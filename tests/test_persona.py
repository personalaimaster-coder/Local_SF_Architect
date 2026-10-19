"""Persona writer: opt-in gating and file content."""

import pytest

from sf_architect.memory.persona import (
    ConsentRequiredError,
    install_skill,
    write_persona,
)


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


def test_install_skill_copies_skill_and_writes_persona(tmp_path) -> None:
    written = install_skill(tmp_path)

    # Skill copied into each agent's skills directory.
    for agent in ("cursor", "claude", "vibes"):
        assert agent in written
    cursor_skill = tmp_path / ".cursor" / "skills" / "local-sf-architect" / "SKILL.md"
    assert cursor_skill.exists()
    assert (
        tmp_path / ".claude" / "skills" / "local-sf-architect" / "references" / "tools.md"
    ).exists()

    # Always-on persona is written and references the skill + MCP tools.
    assert (tmp_path / ".cursor" / "rules" / "architect.mdc").exists()
    agents_md = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "local-sf-architect" in agents_md
    assert "query_architect_db" in agents_md


def test_install_skill_selected_agents_and_no_persona(tmp_path) -> None:
    written = install_skill(tmp_path, agents=("cursor",), with_persona=False)

    # The architect skill plus the bundled sf-compress companion skill are both
    # installed for the selected agent (integrated installer); no persona files.
    assert set(written) == {"cursor", "cursor:sf-compress"}
    assert (tmp_path / ".cursor" / "skills" / "local-sf-architect" / "SKILL.md").exists()
    assert (tmp_path / ".cursor" / "skills" / "sf-compress" / "SKILL.md").exists()
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / "AGENTS.md").exists()


def test_install_skill_refuses_without_consent(tmp_path) -> None:
    with pytest.raises(ConsentRequiredError):
        install_skill(tmp_path, consent=False)


def test_install_skill_is_idempotent(tmp_path) -> None:
    install_skill(tmp_path, agents=("cursor",), with_persona=False)
    # Running again must not raise (target already exists) and stays consistent.
    install_skill(tmp_path, agents=("cursor",), with_persona=False)
    assert (tmp_path / ".cursor" / "skills" / "local-sf-architect" / "SKILL.md").exists()
