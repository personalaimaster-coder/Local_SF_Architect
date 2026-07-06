"""Architecture linter (plan Phase 6 task 2).

Scans Apex for common architectural infractions. Structural rules use the
tree-sitter AST (SOQL/DML inside loops, missing sharing declaration, deep
nesting); pattern rules use targeted regexes over the source text (empty catch
blocks, hardcoded record Ids, hardcoded endpoints, dynamic-SOQL injection risk,
leftover debug statements). Designed to be pre-commit friendly: the CLI exits
non-zero when infractions are found.
"""

from __future__ import annotations

import re
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
# Control-flow blocks that contribute to nesting depth.
NESTING_NODES = LOOP_NODES | {
    "if_statement",
    "try_statement",
    "switch_expression",
    "switch_statement",
}
MAX_NESTING_DEPTH = 4

# Regex rules operate on decoded source. Kept deliberately conservative so the
# clean-code fixture stays clean and false positives are rare.
_EMPTY_CATCH_RE = re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}")
# Salesforce record Id string literal: exactly 15 or 18 base-62 characters.
_HARDCODED_ID_RE = re.compile(r"'(?:[a-zA-Z0-9]{18}|[a-zA-Z0-9]{15})'")
_HARDCODED_URL_RE = re.compile(r"'https?://[^']+'")
_DEBUG_RE = re.compile(r"\bSystem\s*\.\s*debug\s*\(")
# Dynamic SOQL/SOSL built by string concatenation inside a Database query call.
_SOQL_INJECTION_RE = re.compile(
    r"Database\s*\.\s*(?:query|getQueryLocator|countQuery|queryWithBinds)\s*\([^)]*\+"
)


@dataclass
class Infraction:
    """One linter finding."""

    file: str
    line: int
    rule: str
    message: str
    pillar: str


def _line_of(text: str, pos: int) -> int:
    """1-based line number for a character offset in ``text``."""
    return text.count("\n", 0, pos) + 1


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


def _find_deep_nesting(source: bytes, root, file: str) -> list[Infraction]:
    """Flag control-flow nested at or beyond ``MAX_NESTING_DEPTH`` levels."""
    findings: list[Infraction] = []
    reported: set[int] = set()

    def visit(node, depth: int) -> None:
        next_depth = depth
        if node.type in NESTING_NODES:
            next_depth = depth + 1
            line = node.start_point[0] + 1
            if next_depth >= MAX_NESTING_DEPTH and line not in reported:
                reported.add(line)
                findings.append(
                    Infraction(
                        file=file,
                        line=line,
                        rule="deep_nesting",
                        message=f"control flow nested {next_depth} levels deep; "
                        "extract methods to reduce complexity.",
                        pillar="Reliability",
                    )
                )
        for child in node.children:
            visit(child, next_depth)

    visit(root, 0)
    return findings


def _find_regex_rules(text: str, file: str) -> list[Infraction]:
    """Source-text rules for literals and idioms the AST does not surface well."""
    findings: list[Infraction] = []

    def add(pattern: re.Pattern, rule: str, message: str, pillar: str) -> None:
        for match in pattern.finditer(text):
            findings.append(
                Infraction(
                    file=file,
                    line=_line_of(text, match.start()),
                    rule=rule,
                    message=message,
                    pillar=pillar,
                )
            )

    add(
        _EMPTY_CATCH_RE,
        "empty_catch_block",
        "empty catch block swallows the exception; log, rethrow, or handle it.",
        "Reliability",
    )
    add(
        _HARDCODED_ID_RE,
        "hardcoded_id",
        "hardcoded Salesforce record Id; Ids differ per org — query or configure it.",
        "Reliability",
    )
    add(
        _HARDCODED_URL_RE,
        "hardcoded_endpoint",
        "hardcoded endpoint URL; use a Named Credential instead of a literal URL.",
        "Security",
    )
    add(
        _SOQL_INJECTION_RE,
        "soql_injection_risk",
        "dynamic query built with string concatenation; use bind variables or "
        "String.escapeSingleQuotes to prevent SOQL injection.",
        "Security",
    )
    add(
        _DEBUG_RE,
        "debug_statement",
        "System.debug left in code; remove or gate it to avoid log noise and overhead.",
        "Reliability",
    )
    return findings


def scan_file(path: str | Path) -> list[Infraction]:
    """Lint a single Apex file."""
    path = Path(path)
    if path.suffix not in APEX_SUFFIXES:
        return []
    source = path.read_bytes()
    root = _apex_parser().parse(source).root_node
    text = source.decode("utf-8", errors="replace")
    file = str(path)
    return (
        _find_soql_dml_in_loops(source, root, file)
        + _find_missing_sharing(source, root, file)
        + _find_deep_nesting(source, root, file)
        + _find_regex_rules(text, file)
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
