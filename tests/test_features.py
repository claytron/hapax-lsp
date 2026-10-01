from lsprotocol import types as t

from hapax_lsp.features import diagnostics


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
