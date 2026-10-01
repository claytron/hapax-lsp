"""LSP features as pure functions of document text; server.py only wires them up."""

import re

from hapax.fix import fix
from hapax.parse import SECTIONS, Directive, Severity, parse
from hapax.rules import (
    DIRECTIVES, INPORTS, LATEST, MAXRATES, OUTPORTS, TYPES, TYPES_3_20, check_file_name, validate,
)
from lsprotocol import types as t


def diagnostics(text: str, fw=LATEST, file_name: str | None = None, warn: bool = True) -> list[t.Diagnostic]:
    findings = validate(parse(text), fw) + (check_file_name(file_name) if file_name else [])
    lines = text.split("\n")
    return [_diagnostic(f, lines) for f in findings if warn or f.severity is Severity.ERROR]


def _diagnostic(f, lines: list[str]) -> t.Diagnostic:
    line = max(f.line - 1, 0)  # line 0 is the whole file
    start, end = (f.span.start, f.span.end) if f.span else (0, len(lines[line]) if line < len(lines) else 0)
    return t.Diagnostic(
        range=t.Range(t.Position(line, start), t.Position(line, end)),
        message=f.message,
        severity=t.DiagnosticSeverity.Error if f.severity is Severity.ERROR else t.DiagnosticSeverity.Warning,
        code=f.code,
        source="hapax",
    )
