"""Local repo intelligence: Apex + metadata dependency graph (plan Phase 2).

Parses Apex with tree-sitter and Salesforce metadata XML with lxml to build a
name-based dependency map, then answers ``analyze_local_blast_radius``: if I
change this file, what else references it?

tree-sitter gives *syntax*, not *symbol resolution*. Cross-file binding is
name-based; dynamic references (dynamic SOQL, ``Type.forName``, ``Database.query``,
managed-package namespaces) are surfaced explicitly in ``unresolved`` /
``limitations`` rather than silently dropped (additional gap #2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from lxml import etree

APEX_SUFFIXES = (".cls", ".trigger")
META_SUFFIX = "-meta.xml"

# Apex built-in / system types and collections that are not project symbols.
BUILTIN_TYPES = {
    "List", "Set", "Map", "Iterator", "Iterable",
    "Integer", "Long", "Decimal", "Double", "Boolean", "String", "Id",
    "Date", "Datetime", "Time", "Blob", "Object", "SObject", "Void",
    "System", "Database", "Schema", "Test", "Math", "JSON", "Limits",
    "Type", "Trigger", "UserInfo", "ApexPages", "Messaging", "EncodingUtil",
    "Http", "HttpRequest", "HttpResponse", "Exception", "DmlException",
}

DYNAMIC_PATTERNS = {
    "Database.query": r"Database\s*\.\s*query\s*\(",
    "Database.getQueryLocator": r"Database\s*\.\s*getQueryLocator\s*\(",
    "Type.forName": r"Type\s*\.\s*forName\s*\(",
    "getGlobalDescribe": r"getGlobalDescribe\s*\(",
    "dynamic SOQL string": r"\bString\b[^;]*\bSELECT\b",
}

LIMITATIONS = [
    "Name-based resolution only; no full symbol binding across namespaces.",
    "Dynamic SOQL, Type.forName, Database.query, and getGlobalDescribe are not "
    "statically resolvable and are listed under 'unresolved'.",
    "Managed-package (namespaced) references may be missed.",
    "Formula-field and cross-object formula references are partially covered.",
]


@dataclass
class FileNode:
    """One parsed file: what it defines and what it references."""

    path: str
    kind: str  # "apex" | "metadata"
    defines: set[str] = field(default_factory=set)
    references: set[str] = field(default_factory=set)
    dynamic: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def _apex_parser():
    from tree_sitter import Parser
    from tree_sitter_language_pack import get_language

    return Parser(get_language("apex"))


def _node_text(source: bytes, node) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def parse_apex(path: str | Path) -> FileNode:
    """Extract defined class names and referenced symbols from an Apex file."""
    path = Path(path)
    source = path.read_bytes()
    tree = _apex_parser().parse(source)
    node = FileNode(path=str(path), kind="apex")

    def visit(n) -> None:
        if n.type in ("class_declaration", "interface_declaration", "trigger_declaration"):
            name = n.child_by_field_name("name")
            if name is not None:
                node.defines.add(_node_text(source, name))
        elif n.type == "type_identifier":
            text = _node_text(source, n)
            if text and text not in BUILTIN_TYPES:
                node.references.add(text)
        elif n.type == "method_invocation":
            obj = n.child_by_field_name("object")
            if obj is not None and obj.type == "identifier":
                receiver = _node_text(source, obj)
                if receiver and receiver[0].isupper() and receiver not in BUILTIN_TYPES:
                    node.references.add(receiver)
        elif n.type == "from_clause":
            for child in n.children:
                if child.type in ("storage_identifier", "identifier"):
                    obj = _node_text(source, child)
                    if obj:
                        node.references.add(obj)
        for child in n.children:
            visit(child)

    visit(tree.root_node)

    text = source.decode("utf-8", errors="replace")
    for label, pattern in DYNAMIC_PATTERNS.items():
        if re.search(pattern, text):
            node.dynamic.append(label)

    node.references -= node.defines
    return node


def _object_name_from_path(path: Path) -> str | None:
    """Derive the sObject API name for a metadata file in a DX layout."""
    name = path.name
    if name.endswith(".object-meta.xml"):
        return name[: -len(".object-meta.xml")]
    # objects/<Object>/fields/<Field>.field-meta.xml etc.
    for parent in path.parents:
        if parent.parent is not None and parent.parent.name == "objects":
            return parent.name
    return None


def parse_metadata(path: str | Path) -> FileNode:
    """Extract defined/referenced sObject and field symbols from metadata XML."""
    path = Path(path)
    node = FileNode(path=str(path), kind="metadata")
    name = path.name
    object_name = _object_name_from_path(path)

    if name.endswith(".object-meta.xml") and object_name:
        node.defines.add(object_name)
    elif name.endswith(".field-meta.xml") and object_name:
        field_name = name[: -len(".field-meta.xml")]
        node.defines.add(f"{object_name}.{field_name}")
        node.references.add(object_name)
    elif object_name:
        node.references.add(object_name)

    try:
        tree = etree.parse(str(path))
    except etree.XMLSyntaxError:
        return node

    for el in tree.iter():
        tag = etree.QName(el).localname if el.tag is not etree.Comment else ""
        if tag in ("object", "objectType", "referenceTo", "entityName") and el.text:
            node.references.add(el.text.strip())

    node.references -= node.defines
    return node


def _iter_source_files(repo_root: Path):
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in APEX_SUFFIXES:
            yield path, "apex"
        elif path.name.endswith(META_SUFFIX):
            yield path, "metadata"


@lru_cache(maxsize=8192)
def _parse_cached(path_str: str, kind: str, mtime_ns: int, size: int) -> FileNode:
    """Parse a file, memoized by (path, mtime, size).

    ``analyze_local_blast_radius`` rebuilds the whole graph on every call; without
    memoization a large DX repo is fully re-parsed each time. Keying on the file's
    mtime and size means an edited file is transparently re-parsed while unchanged
    files are served from cache. Callers treat the returned node as read-only.
    """
    path = Path(path_str)
    return parse_apex(path) if kind == "apex" else parse_metadata(path)


def _parse_file(path: Path, kind: str) -> FileNode:
    """Parse ``path`` through the mtime-keyed cache, falling back on any error."""
    try:
        stat = path.stat()
        return _parse_cached(str(path), kind, stat.st_mtime_ns, stat.st_size)
    except Exception:
        return FileNode(path=str(path), kind=kind)


def build_dependency_graph(repo_root: str | Path) -> dict[str, FileNode]:
    """Parse every Apex/metadata file under ``repo_root`` into a node map."""
    repo_root = Path(repo_root)
    graph: dict[str, FileNode] = {}
    for path, kind in _iter_source_files(repo_root):
        graph[str(path)] = _parse_file(path, kind)
    return graph


def _symbol_to_definers(graph: dict[str, FileNode]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for fpath, node in graph.items():
        for symbol in node.defines:
            index.setdefault(symbol, set()).add(fpath)
    return index


def _dependents_of(symbols: set[str], graph: dict[str, FileNode], exclude: set[str]):
    """Files that reference any of ``symbols`` (a Ref per match)."""
    refs = []
    for fpath, node in graph.items():
        if fpath in exclude:
            continue
        matched = node.references & symbols
        for symbol in sorted(matched):
            refs.append({"file": fpath, "symbol": symbol, "kind": node.kind})
    return refs


def analyze_local_blast_radius(
    filepath: str | Path,
    repo_root: str | Path | None = None,
    depth: int = 2,
) -> dict:
    """Compute what references the target file, directly and transitively.

    Returns ``{target, immediate, transitive, unresolved, limitations}``.
    ``immediate`` are files referencing the target's defined symbols; ``transitive``
    extends outward up to ``depth`` hops. Dynamic/unresolvable references in the
    target are surfaced under ``unresolved`` (additional gap #2).
    """
    filepath = Path(filepath).resolve()
    repo_root = Path(repo_root).resolve() if repo_root else filepath.parent
    graph = build_dependency_graph(repo_root)

    target_key = str(filepath)
    target = graph.get(target_key)
    if target is None:  # parse the target even if outside the scan glob
        if filepath.suffix in APEX_SUFFIXES:
            target = parse_apex(filepath)
        else:
            target = parse_metadata(filepath)
        graph[target_key] = target

    visited: set[str] = {target_key}
    immediate = _dependents_of(target.defines, graph, visited)
    immediate_files = {r["file"] for r in immediate}
    visited |= immediate_files

    transitive: list[dict] = []
    frontier = immediate_files
    for _ in range(max(depth - 1, 0)):
        next_symbols: set[str] = set()
        for fpath in frontier:
            next_symbols |= graph[fpath].defines
        if not next_symbols:
            break
        hop = _dependents_of(next_symbols, graph, visited)
        if not hop:
            break
        transitive.extend(hop)
        frontier = {r["file"] for r in hop}
        visited |= frontier

    unresolved = sorted(target.dynamic)
    return {
        "target": target_key,
        "immediate": immediate,
        "transitive": transitive,
        "unresolved": unresolved,
        "limitations": LIMITATIONS,
    }
