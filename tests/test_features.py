from lsprotocol import types as t

from hapax_lsp.features import TOKEN_TYPES, diagnostics, semantic_tokens


def decode(data):
    """Semantic token data back to absolute (line, col, length, type) tuples."""
    out, line, col = [], 0, 0
    for i in range(0, len(data), 5):
        dl, dc, length, kind, _ = data[i : i + 5]
        line, col = line + dl, (col + dc if dl == 0 else dc)
        out.append((line, col, length, TOKEN_TYPES[kind]))
    return out


# Diagnostics


def test_clean_file_has_no_diagnostics():
    assert diagnostics("VERSION 1\nTYPE POLY\n[CC]\n74 Cutoff\n[/CC]\n") == []


def test_error_maps_range_severity_code_and_source():
    [d] = diagnostics("[CC]\n200 Bad\n[/CC]\n")
    assert d.range == t.Range(t.Position(1, 0), t.Position(1, 3))
    assert d.severity == t.DiagnosticSeverity.Error
    assert d.code == "cc.range"
    assert d.source == "hapax"


def test_finding_without_span_covers_the_whole_line():
    [d] = diagnostics("[FOO]\nx\n[/FOO]\n")
    assert d.code == "section.unknown"
    assert d.range == t.Range(t.Position(1, 0), t.Position(1, 1))


def test_firmware_changes_findings():
    assert diagnostics("TYPE POLYAT\n", fw=(3, 21)) == []
    assert [d.code for d in diagnostics("TYPE POLYAT\n", fw=(3, 10))] == ["type.value"]


def test_long_file_name_warns_on_first_line():
    [d] = diagnostics("VERSION 1\n", file_name="a" * 28 + ".txt")
    assert (d.code, d.range.start.line, d.severity) == ("file.name_long", 0, t.DiagnosticSeverity.Warning)


def test_warn_false_drops_warnings_but_keeps_errors():
    text = "[CC]\n74 Cutoff\n"  # never closed: a warning
    assert [d.code for d in diagnostics(text)] == ["section.unclosed_eof"]
    assert diagnostics(text, warn=False) == []


def test_unparseable_line_still_reports():
    [d] = diagnostics("[CC]\nnot a cc\n[/CC]\n")
    assert d.code == "syntax"


# Semantic tokens


def test_tokens_for_directives_sections_entries_and_comments():
    text = "TYPE POLY # synth\nOUTCHAN 3\n[CC]\n74:DEFAULT=64 Cutoff\n[/CC]\n"
    assert decode(semantic_tokens(text)) == [
        (0, 0, 4, "keyword"),
        (0, 5, 4, "enumMember"),
        (0, 10, 7, "comment"),
        (1, 0, 7, "keyword"),
        (1, 8, 1, "number"),
        (2, 0, 4, "namespace"),
        (3, 0, 2, "number"),
        (3, 3, 8, "keyword"),
        (3, 11, 2, "number"),
        (3, 14, 6, "string"),
        (4, 0, 5, "namespace"),
    ]


def test_tokens_for_trackname_null_and_targets():
    text = "TRACKNAME Peak\nOUTPORT NULL\n[ASSIGN]\n1 CC:74 DEFAULT=100\n[/ASSIGN]\n"
    assert decode(semantic_tokens(text)) == [
        (0, 0, 9, "keyword"),
        (0, 10, 4, "string"),
        (1, 0, 7, "keyword"),
        (1, 8, 4, "keyword"),
        (2, 0, 8, "namespace"),
        (3, 0, 1, "number"),
        (3, 2, 3, "keyword"),
        (3, 5, 2, "number"),
        (3, 8, 8, "keyword"),
        (3, 16, 3, "number"),
        (4, 0, 9, "namespace"),
    ]


def test_comment_section_lines_are_strings():
    assert decode(semantic_tokens("[COMMENT]\nHello there\n[/COMMENT]\n"))[1] == (1, 0, 11, "string")


def test_bad_line_gets_only_its_comment():
    assert decode(semantic_tokens("[CC]\nnot a cc # oops\n[/CC]\n"))[1] == (1, 9, 6, "comment")


def test_crlf_line_endings_tokenize_like_lf():
    assert semantic_tokens("TYPE POLY # x\r\n[CC]\r\n74 Cutoff\r\n[/CC]\r\n") == semantic_tokens(
        "TYPE POLY # x\n[CC]\n74 Cutoff\n[/CC]\n")
