"""Linter: detects SOQL/DML-in-loop and missing sharing; CLI exit codes."""

from pathlib import Path

from click.testing import CliRunner

from sf_architect.cli import main
from sf_architect.lint import scan_file

FIXTURES = Path(__file__).parent / "fixtures" / "lint"


def test_bad_class_has_infractions() -> None:
    findings = scan_file(FIXTURES / "Bad.cls")
    rules = {f.rule for f in findings}
    assert "soql_dml_in_loop" in rules
    assert "missing_sharing" in rules


def test_clean_class_passes() -> None:
    findings = scan_file(FIXTURES / "Clean.cls")
    assert findings == []


def test_cli_lint_nonzero_on_infraction() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["lint", str(FIXTURES / "Bad.cls")])
    assert result.exit_code == 1
    assert "infraction" in result.output.lower()


def test_cli_lint_zero_on_clean() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["lint", str(FIXTURES / "Clean.cls")])
    assert result.exit_code == 0
    assert "No architectural infractions" in result.output
