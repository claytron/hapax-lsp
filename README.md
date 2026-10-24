# hapax-lsp

A language server for [Squarp Hapax](https://squarp.net/hapax/) instrument definitions: diagnostics, highlighting, completion and a fix-all action, in any editor with an LSP client.
Validation comes from [hapax-tui](https://github.com/claytron/hapax-tui), so the editor reports exactly what `hapax validate` reports.

## Install

Requires Python 3.13+.

```sh
uv tool install hapax-lsp
```

This puts `hapax-lsp` on your `PATH`; it speaks LSP over stdio.

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `fw` | `3.21` | Target Hapax OS, `1.12` to `3.21` |
| `warn` | `warn` in `~/.config/hapax/config.toml`, else `true` | Report warnings as well as errors |

Send them as `initializationOptions`, or as `workspace/didChangeConfiguration` settings under a `hapax` key.

## Neovim (0.11+)

This repo is also a Neovim plugin.
Install it with your plugin manager and enable the server, for example with lazy.nvim:

```lua
{ "claytron/hapax-lsp", config = function() vim.lsp.enable("hapax") end }
```

Instrument definitions are `.txt` files, so `ftdetect/hapax.lua` marks a `.txt` buffer as `hapax` when its first non-comment line is a whole directive (`VERSION 1`, `TRACKNAME My Synth`, `TYPE POLY`, ...) or a section header like `[CC]`.
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
