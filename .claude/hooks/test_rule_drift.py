from pathlib import Path

from rule_drift import check, canonicalize, parse_blocks


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def pair(tmp_path: Path, content: str) -> tuple[Path, Path]:
    source = tmp_path / "source.md"
    derived = tmp_path / "derived.md"
    block = (
        "<!-- @rule:sample @source:source.md @fragment:one -->\n"
        f"{content}\n"
        "<!-- /@rule:sample -->\n"
    )
    write(source, block.replace("@source:source.md", "@source:source.md"))
    write(derived, block)
    return source, derived


def test_matching_source_and_derived_pass(tmp_path, monkeypatch):
    source, derived = pair(tmp_path, "Shared rule text.")
    # The checker resolves paths relative to the current repository. Make the
    # explicit source path relative to the temporary test directory.
    source_block = source.read_text().replace("@source:source.md", f"@source:{source}")
    derived_block = derived.read_text().replace("@source:source.md", f"@source:{source}")
    write(source, source_block)
    write(derived, derived_block)
    messages, code = check([source, derived])
    assert code == 0
    assert messages == []


def test_whitespace_only_change_passes(tmp_path):
    source, derived = pair(tmp_path, "Shared   rule\ntext.")
    source_text = source.read_text().replace("@source:source.md", f"@source:{source}")
    derived_text = derived.read_text().replace(
        "@source:source.md", f"@source:{source}"
    ).replace("Shared   rule\ntext.", "  Shared rule\n\ntext.  ")
    write(source, source_text)
    write(derived, derived_text)
    messages, code = check([source, derived])
    assert code == 0
    assert messages == []


def test_content_drift_fails(tmp_path):
    source, derived = pair(tmp_path, "Canonical text.")
    source_text = source.read_text().replace("@source:source.md", f"@source:{source}")
    derived_text = derived.read_text().replace(
        "@source:source.md", f"@source:{source}"
    ).replace("Canonical text.", "Changed text.")
    write(source, source_text)
    write(derived, derived_text)
    messages, code = check([source, derived])
    assert code == 1
    assert any(message.startswith("DRIFT_FAIL") for message in messages)


def test_missing_source_fails(tmp_path):
    path = tmp_path / "orphan.md"
    write(
        path,
        "<!-- @rule:missing @source:no-such.md @fragment:x -->\n"
        "Text\n<!-- /@rule:missing -->\n",
    )
    messages, code = check([path])
    assert code == 1
    assert any(message.startswith("SOURCE_MISSING") for message in messages)


def test_missing_source_attribute_is_orphan(tmp_path):
    path = tmp_path / "orphan.md"
    write(
        path,
        "<!-- @rule:orphan @fragment:x -->\n"
        "Text\n<!-- /@rule:orphan -->\n",
    )
    messages, code = check([path])
    assert code == 1
    assert any(message.startswith("ORPHAN_FAIL") for message in messages)


def test_unterminated_block_is_reported(tmp_path):
    path = tmp_path / "broken.md"
    write(path, "<!-- @rule:broken @source:broken.md @fragment:x -->\nText\n")
    blocks, errors = parse_blocks(path)
    assert blocks == []
    assert errors


def test_canonicalize_collapses_whitespace():
    assert canonicalize([" a   b ", "", "c\td"]) == "a b c d"
