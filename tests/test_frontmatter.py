"""Tests for apex/utils/frontmatter.py."""

from apex.utils.frontmatter import parse_frontmatter, parse_frontmatter_document, split_frontmatter


def test_split_frontmatter_present():
    content = "---\nname: foo\n---\nbody here"
    fm, body = split_frontmatter(content)
    assert fm == "name: foo"
    assert body == "body here"


def test_split_frontmatter_absent():
    content = "no frontmatter"
    fm, body = split_frontmatter(content)
    assert fm is None
    assert body == "no frontmatter"


def test_parse_scalar_types():
    fm = parse_frontmatter(
        "a: 1\nb: 2.5\nc: true\nd: false\ne: null\nf: ~\ng: hello\nh: \"quoted\"\ni: 'single'\nj: [1, 2, 3]\nk: {a: 1, b: two}\nl:"
    )
    assert fm["a"] == 1
    assert fm["b"] == 2.5
    assert fm["c"] is True
    assert fm["d"] is False
    assert fm["e"] is None
    assert fm["f"] is None
    assert fm["g"] == "hello"
    assert fm["h"] == "quoted"
    assert fm["i"] == "single"
    assert fm["j"] == [1, 2, 3]
    assert fm["k"] == {"a": 1, "b": "two"}
    assert fm["l"] is None


def test_parse_frontmatter_skips_comments_and_blanks():
    fm = parse_frontmatter("# comment\n\nkey: value")
    assert fm == {"key": "value"}


def test_parse_frontmatter_document():
    content = "---\nname: foo\n---\nbody"
    meta, body = parse_frontmatter_document(content)
    assert meta == {"name": "foo"}
    assert body == "body"


def test_parse_frontmatter_document_no_fm():
    meta, body = parse_frontmatter_document("just body")
    assert meta is None
    assert body == "just body"


def test_nested_quotes_in_list():
    fm = parse_frontmatter('tags: ["a, b", c]')
    assert fm["tags"] == ["a, b", "c"]


def test_empty_list_and_dict():
    fm = parse_frontmatter("l: []\nd: {}")
    assert fm["l"] == []
    assert fm["d"] == {}
