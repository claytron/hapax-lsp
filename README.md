# hapax-lsp

A language server for Squarp Hapax instrument definitions: diagnostics, highlighting, completion and a fix-all action, in any editor with an LSP client.
Validation comes from [hapax-tui](https://github.com/claytron/hapax-tui), so the editor reports exactly what `hapax validate` reports.

## Install

```sh
uv tool install git+https://github.com/claytron/hapax-lsp
```

This puts `hapax-lsp` on your `PATH`; it speaks LSP over stdio.

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `fw` | `3.21` | Target Hapax OS, `1.12` to `3.21` |
| `warn` | `warn` in `~/.config/hapax/config.toml`, else `true` | Report warnings as well as errors |

Send them as `initializationOptions`, or as `workspace/didChangeConfiguration` settings under a `hapax` key.

## Neovim (0.11+)

Add the bundled runtime directory and enable the server:

```lua
vim.opt.runtimepath:append("/path/to/hapax-lsp/editors/nvim")
vim.lsp.enable("hapax")
```

Instrument definitions are `.txt` files, so `ftdetect/hapax.lua` marks a `.txt` buffer as `hapax` when its first non-comment line is a directive (`VERSION`, `TRACKNAME`, `TYPE`, ...) or a section header.
Other `.txt` files stay `text`.
Highlighting comes from semantic tokens, linked to your colour scheme's `@lsp.type.*` groups.
Run the fix-all action with `vim.lsp.buf.code_action()`.

## Other editors

Map Hapax `.txt` files to a `hapax` language however your editor allows, for example by the directory you keep instruments in, and run `hapax-lsp` for it.

## Development

```sh
uv sync
uv run pytest
```
