# hapax-lsp design

## Goal

Syntax highlighting, validation and completion for Squarp Hapax instrument definitions in any editor with an LSP client.
Neovim is the first client, but nothing in the server is Neovim-specific.
This is a prototype: prove the editor experience before deciding whether the validator moves out of hapax-tui into its own package.

## Non-goals

- A second parser or rule set.
  hapax-tui's `parse()` and `validate()` are the single source of truth.
- Tree-sitter, TextMate or Vim syntax grammars.
  Highlighting comes from semantic tokens.
- Hover, go-to-definition, formatting, rename.
- Detecting the filetype inside the server.

## Packaging

- Python package `hapax-lsp` in this repo, managed with `uv`, Python 3.13 (hapax-tui's floor).
- Dependencies: `pygls` and `hapax-tui @ git+https://github.com/claytron/hapax-tui`.
  The git dependency becomes a PyPI version once hapax-tui is published.
- Console script `hapax-lsp`, speaking LSP over stdio.

## What the server reuses

| hapax-tui | Used for |
|---|---|
| `parse.parse(text) -> Document` | Never raises; every entry carries its line and a `spans` map of field name to columns |
| `rules.validate(doc, fw) -> list[Finding]` | Findings have severity, stable `code`, message, 1-based line and optional `Span` |
| `fix.fix(text, fw) -> (text, applied)` | The "Fix all" code action |
| `rules.parse_fw`, `rules.LATEST` | Firmware setting |
| `rules.DIRECTIVES`, `TYPES`, `TYPES_3_20`, `OUTPORTS`, `INPORTS`, `MAXRATES`, `parse.SECTIONS` | Completion candidates |
| `config.load()` | The `warn` default, as the CLI uses it |

## Settings

Read from `initializationOptions`, and refreshed from `workspace/didChangeConfiguration` under the `hapax` key:

```json
{ "fw": "3.21", "warn": true }
```

- `fw` defaults to `rules.LATEST`; an invalid value is logged via `window/logMessage` and ignored.
- `warn` defaults to `config.load().get("warn", True)`; when false, warnings are not published.
- A settings change re-validates every open document.

## Features

### Diagnostics

On `didOpen` and `didChange` (full sync), parse and validate the document and publish one diagnostic per finding.

- Severity: `error` maps to Error, `warning` maps to Warning.
- `code` is the finding's code, for example `cc.range`.
- `source` is `hapax`.
- Range: line `finding.line - 1`, columns from `finding.span`; with no span, the whole line.
  A finding on line 0 (whole file) goes on the first line.
- `check_file_name` runs against the document's URI basename, so the 27-character limit shows up too.

### Semantic tokens

Full-document semantic tokens only, no deltas or ranges.
The legend uses standard token types so every colour scheme already styles them:

| Source | Token type |
|---|---|
| Directive key (`TYPE`, `OUTPORT`, ...) | `keyword` |
| Directive value | `enumMember`, or `number` when numeric |
| `[CC]`, `[/CC]` section headers | `namespace` |
| Numeric fields (`cc`, `msb`, `lsb`, `depth`, `row`, ...) | `number` |
| `NULL`, target types (`CC:`, `NRPN:`, `PB`, ...), `DEFAULT=` | `keyword` |
| `name` field and `[COMMENT]` lines | `string` |
| `#` to end of line | `comment` |

Tokens come from each entry's `spans`.
Headers and comments are found by scanning the raw lines, since they are not entries.
Lines that fail to parse get no tokens beyond their comment; the diagnostic already marks them.

### Completion

Decided from the cursor's line and the section it is in (from `Document.sections`):

| Context | Candidates |
|---|---|
| Outside any section, first word | `DIRECTIVES`, and `[` section openers |
| After `TYPE` | `TYPES`, plus `TYPES_3_20` when `fw >= 3.20` |
| After `OUTPORT` | `OUTPORTS`, plus `USBD1-16`/`USBH1-16` when `fw >= 3.00` |
| After `INPORT` | `INPORTS`, plus virtual ports when `fw >= 3.00` |
| After `OUTCHAN`/`INCHAN` | `1`-`16`, `NULL`, and `ALL` for `INCHAN` |
| After `MAXRATE` | `MAXRATES`, `NULL` |
| After `VERSION` | `1` |
| `[` at line start | `SECTIONS` |
| `[/` at line start | The open section's name, closing it |
| `[ASSIGN]` after the pot, `[AUTOMATION]` first word | `CC:`, `NRPN:`, `CC_PAIR:`, `CV:`, `PB`, `AT`, and `NULL` in `[ASSIGN]` only |
| After a complete target value | `DEFAULT=` |

Trigger characters: `[`, `/`, ` `, `:`.
Each item's `detail` names its firmware floor when it has one, for example `from 3.20`.

### Code action

One action, "Hapax: fix all", offered whenever the document has findings.
It runs `fix(text, fw)` and returns a single whole-document text edit, titled with the number of repairs; it is not offered when `fix` changes nothing.

## Editor setup (shipped in the README)

Instrument definitions are `.txt` files, so each client has to decide which `.txt` files are Hapax ones.

Neovim:

- `vim.filetype.add` with a `.txt` pattern function that returns `hapax` when the first non-blank, non-comment line starts with `VERSION`, `TRACKNAME`, `TYPE`, `OUTPORT`, `OUTCHAN`, `INPORT`, `INCHAN`, `MAXRATE` or `[`.
- `lsp/hapax.lua` with `cmd = { "hapax-lsp" }`, `filetypes = { "hapax" }` and `init_options = { fw = "3.21" }`, enabled with `vim.lsp.enable("hapax")`.

Other editors get a one-line note: map the instruments directory's `*.txt` to a `hapax` language and run `hapax-lsp`.

## Layout

```text
pyproject.toml
src/hapax_lsp/
  server.py      # pygls wiring, settings, document cache
  features.py    # pure functions: diagnostics, tokens, completion, fix action
tests/
  test_features.py
  test_server.py
editors/nvim/
  lsp/hapax.lua
  ftdetect.lua
README.md
```

`features.py` takes text, firmware and a position, and returns `lsprotocol` types.
It holds no state, so it is testable without a server.

## Error handling

- `parse()` never raises; a document that fails to parse still gets diagnostics.
- Any exception inside a handler is logged to the client and that request returns empty, so one bad document cannot kill the server.

## Testing

- `test_features.py`: table tests from text to diagnostics (range, severity, code), semantic tokens (decoded back to `(line, col, len, type)`), completion labels per context, and the fix edit.
- `test_server.py`: one end-to-end test through pygls's test client, covering open, publish diagnostics and request completion.
- Fixtures reuse hapax-tui's style of small inline definitions; no files copied from the SD card.
