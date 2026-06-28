"""Persona writer: opt-in gating and file content."""

import pytest

from sf_architect.memory.persona import ConsentRequiredError, write_persona


def test_refuses_without_consent(tmp_path) -> None:
    with pytest.raises(ConsentRequiredError):
        write_persona(tmp_path, consent=False)
    # Nothing should be written.
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / ".cursor").exists()


def test_writes_with_consent(tmp_path) -> None:
    paths = write_persona(tmp_path, consent=True)
    mdc = tmp_path / ".cursor" / "rules" / "architect.mdc"
    agents = tmp_path / "AGENTS.md"
    assert mdc.exists() and agents.exists()
    assert paths["architect_mdc"] == str(mdc)

    content = mdc.read_text(encoding="utf-8")
    assert "alwaysApply: true" in content
    assert "senior Salesforce architect" in content
    assert "governor limits" in content
