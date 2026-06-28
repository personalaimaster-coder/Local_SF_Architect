"""Architecture linter (plan Phase 6 task 2).

Scans Apex for common architectural infractions using the tree-sitter AST:
SOQL/DML inside loops (Scalability) and classes missing an explicit sharing
declaration (Security). Designed to be pre-commit friendly: the CLI exits
non-zero when infractions are found.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sf_architect.engines.depgraph import _apex_parser

APEX_SUFFIXES = (".cls", ".trigger")
LOOP_NODES = {
    "for_statement",
    "enhanced_for_statement",
    "while_statement",
    "do_statement",
}


@dataclass
class Infraction:
    """One linter finding."""

    file: str
    line: int
    rule: str
    message: str
    pillar: str


def _find_soql_dml_in_loops(source: bytes, root, file: str) -> list[Infraction]:
    findings: list[Infraction] = []

    def visit(node, in_loop: bool) -> None:
        inside = in_loop or node.type in LOOP_NODES
        if inside and node.type in ("query_expression", "dml_expression"):
            kind = "SOQL" if node.type == "query_expression" else "DML"
            findings.append(
                Infraction(
                    file=file,
                    line=node.start_point[0] + 1,
                    rule="soql_dml_in_loop",
                    message=f"{kind} statement inside a loop; bulkify by moving it out.",
                    pillar="Scalability",
                )
            )
        for child in node.children:
            visit(child, inside)

    visit(root, False)
    return findings


def _find_missing_sharing(source: bytes, root, file: str) -> list[Infraction]:
    findings: list[Infraction] = []

    def visit(node) -> None:
        if node.type == "class_declaration":
            modifiers = next(
                (c for c in node.children if c.type == "modifiers"), None
            )
            text = (
                source[modifiers.start_byte : modifiers.end_byte].decode("utf-8", "replace")
                if modifiers is not None
                else ""
            )
            if "sharing" not in text:
                name = node.child_by_field_name("name")
                cls = (
                    source[name.start_byte : name.end_byte].decode("utf-8", "replace")
                    if name is not None
                    else "<class>"
                )
                findings.append(
                    Infraction(
                        file=file,
                        line=node.start_point[0] + 1,
                        rule="missing_sharing",
                        message=f"class '{cls}' has no explicit sharing declaration "
                        "(use 'with sharing' / 'without sharing' / 'inherited sharing').",
                        pillar="Security",
                    )
                )
        for child in node.children:
            visit(child)

    visit(root)
    return findings


def scan_file(path: str | Path) -> list[Infraction]:
    """Lint a single Apex file."""
    path = Path(path)
    if path.suffix not in APEX_SUFFIXES:
        return []
    source = path.read_bytes()
    root = _apex_parser().parse(source).root_node
    file = str(path)
    return _find_soql_dml_in_loops(source, root, file) + _find_missing_sharing(
        source, root, file
    )


def scan_path(path: str | Path) -> list[Infraction]:
    """Lint a file or recursively lint all Apex under a directory."""
    path = Path(path)
    if path.is_file():
        return scan_file(path)
    findings: list[Infraction] = []
    for suffix in APEX_SUFFIXES:
        for apex_file in path.rglob(f"*{suffix}"):
            findings.extend(scan_file(apex_file))
    return findings
