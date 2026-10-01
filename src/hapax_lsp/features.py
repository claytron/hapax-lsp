"""LSP features as pure functions of document text; server.py only wires them up."""

import re

from hapax.fix import fix
from hapax.parse import SECTIONS, Directive, Severity, parse
from hapax.rules import (
    DIRECTIVES, INPORTS, LATEST, MAXRATES, OUTPORTS, TYPES, TYPES_3_20, check_file_name, validate,
)
from lsprotocol import types as t

TOKEN_TYPES = ["keyword", "enumMember", "number", "string", "namespace", "comment"]
_HEADER = re.compile(r"[ \t]*(\[/?[^\]]*\])")
_NUMBER = re.compile(r"-?[0-9]+(\.[0-9]+)?V?", re.I)
_DEFAULT = "DEFAULT="


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


def semantic_tokens(text: str) -> list[int]:
    doc = parse(text)
    tokens = []  # (line, start, end, type), 0-based
    for e in [*doc.directives, *(e for s in doc.sections for e in s.entries)]:
        for field, span in e.spans.items():
            if kind := _kind(e, field, e.raw[span.start : span.end]):
                tokens.append((e.line - 1, span.start, span.end, kind))
            if field == "default" and e.raw[: span.start].upper().endswith(_DEFAULT):
                tokens.append((e.line - 1, span.start - len(_DEFAULT), span.start, "keyword"))
    for n, raw in enumerate(doc.lines):
        body, hash_, _ = raw.partition("#")
        if m := _HEADER.fullmatch(body.rstrip(" \t\r")):
            tokens.append((n, m.start(1), m.end(1), "namespace"))
        if hash_:
            tokens.append((n, len(body), len(raw.rstrip("\r")), "comment"))
    return _encode(sorted(tokens))


def _kind(entry, field: str, raw: str) -> str | None:
    if field in ("name", "text") or (isinstance(entry, Directive) and entry.key == "TRACKNAME" and field == "value"):
        return "string"
    if field in ("key", "type") or raw.upper() == "NULL":
        return "keyword"
    if field == "junk":
        return None
    return "number" if _NUMBER.fullmatch(raw) else "enumMember"


def _encode(tokens) -> list[int]:
    data, prev_line, prev_start = [], 0, 0
    for line, start, end, kind in tokens:
        delta = start - prev_start if line == prev_line else start
        data += [line - prev_line, delta, end - start, TOKEN_TYPES.index(kind), 0]
        prev_line, prev_start = line, start
    return data
