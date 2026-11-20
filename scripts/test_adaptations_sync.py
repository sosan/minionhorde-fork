"""Tests for agent adaptation frontmatter synchronization."""

from __future__ import annotations

from adaptations_sync import (
    parse_frontmatter,
    render_frontmatter,
    update_one,
)


def test_parse_frontmatter_preserves_body_after_delimiter():
    text = "---\nname: demo\n---\n\n# Body\n\nExact.\n"
    fields, body = parse_frontmatter(text)
    assert fields["name"] == "demo"
    assert body == "\n# Body\n\nExact.\n"


def test_parse_frontmatter_preserves_polluted_separator_exactly():
    # The parser must never normalize body bytes. The old --update bug polluted
    # the delimiter separator with extra blank lines; the fix stops growing them
    # but must leave existing bytes byte-for-byte intact.
    text = "---\nname: demo\n---\n\n\n\n# Body\n"
    _fields, body = parse_frontmatter(text)
    assert body == "\n\n\n# Body\n"


def test_parse_frontmatter_body_without_leading_blank():
    text = "---\nname: demo\n---\n# Body\n"
    _fields, body = parse_frontmatter(text)
    assert body == "# Body\n"


def test_update_one_is_idempotent_and_preserves_body(tmp_path, monkeypatch):
    import adaptations_sync

    agent_dir = tmp_path / ".claude" / "agents"
    agent_dir.mkdir(parents=True)
    path = agent_dir / "demo.md"
    body = "\n# Body\n\nExact.\n"
    meta = {
        "description": "Demo agent",
        "tools": ["Read"],
        "model": "sonnet",
    }
    path.write_text(render_frontmatter({"name": "demo", **meta}) + body, encoding="utf-8")
    monkeypatch.setattr(adaptations_sync, "REPO_ROOT", tmp_path)

    first_changed, _ = update_one("demo", meta)
    first_text = path.read_text(encoding="utf-8")
    second_changed, _ = update_one("demo", meta)

    assert not first_changed
    assert not second_changed
    assert path.read_text(encoding="utf-8") == first_text
    assert parse_frontmatter(first_text)[1] == body


def test_update_one_is_idempotent_on_already_polluted_file(tmp_path, monkeypatch):
    import adaptations_sync

    agent_dir = tmp_path / ".claude" / "agents"
    agent_dir.mkdir(parents=True)
    path = agent_dir / "demo.md"
    meta = {
        "description": "Demo agent",
        "tools": ["Read"],
        "model": "sonnet",
    }
    polluted = render_frontmatter({"name": "demo", **meta}) + "\n\n\n# Body\n"
    path.write_text(polluted, encoding="utf-8")
    monkeypatch.setattr(adaptations_sync, "REPO_ROOT", tmp_path)

    changed, _ = update_one("demo", meta)
    assert not changed  # frontmatter already canonical: no rewrite at all
    assert path.read_text(encoding="utf-8") == polluted  # body untouched