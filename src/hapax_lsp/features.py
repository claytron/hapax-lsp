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
_TARGETS = ["CC:", "NRPN:", "CC_PAIR:", "CV:", "PB", "AT"]


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


def completion(text: str, line: int, character: int, fw=LATEST) -> list[t.CompletionItem]:
    lines = text.split("\n")
    before = lines[line][:character] if line < len(lines) else ""
    if "#" in before:
        return []
    stripped = before.lstrip(" \t")
    words = stripped.split()
    trailing = before[-1:] in (" ", "\t")
    # index of the word under the cursor; a trailing space starts the next one
    at = len(words) if trailing or not words else len(words) - 1
    section = _section_at(parse(text), line + 1)

    if stripped.startswith("[/"):
        return [_item(f"{section}]")] if section else []
    if stripped.startswith("["):
        return [_item(f"{s}]") for s in sorted(SECTIONS)]
    if section is None:
        if at == 0:
            return [_item(d) for d in sorted(DIRECTIVES)] + [_item(f"[{s}]") for s in sorted(SECTIONS)]
        if at == 1:
            return _values(words[0].upper(), fw)
    elif section in ("ASSIGN", "AUTOMATION"):
        target = 1 if section == "ASSIGN" else 0
        if at == target:
            return [_item(x) for x in _TARGETS + (["NULL"] if section == "ASSIGN" else [])]
        if at > target:
            return [_item(_DEFAULT)]
    return []


def _section_at(doc, n: int) -> str | None:
    """The section open at 1-based line n."""
    for s in reversed(doc.sections):
        if s.start < n:
            return s.name if s.end is None or n < s.end else None
    return None


def _values(key: str, fw) -> list[t.CompletionItem]:
    virtual = [f"{p}{x}" for p in ("USBD", "USBH") for x in range(1, 17)]
    channels = [_item(str(c)) for c in range(1, 17)] + [_item("NULL")]
    match key:
        case "VERSION":
            return [_item("1")]
        case "TYPE":
            return [_item(x) for x in sorted(TYPES)] + _gated(sorted(TYPES_3_20), (3, 20), fw)
        case "OUTPORT":
            return [_item(x) for x in sorted(OUTPORTS)] + _gated(virtual, (3, 0), fw)
        case "INPORT":
            return [_item(x) for x in sorted(INPORTS)] + _gated(virtual, (3, 0), fw)
        case "OUTCHAN":
            return channels
        case "INCHAN":
            return channels + [_item("ALL")]
        case "MAXRATE":
            return [_item(str(r)) for r in sorted(MAXRATES, reverse=True)] + [_item("NULL")]
    return []


def _gated(labels: list[str], floor: tuple[int, int], fw) -> list[t.CompletionItem]:
    return [_item(x, f"from {floor[0]}.{floor[1]:02}") for x in labels] if fw >= floor else []


def _item(label: str, detail: str | None = None) -> t.CompletionItem:
    return t.CompletionItem(label=label, detail=detail)
