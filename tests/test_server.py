import asyncio
import sys

from lsprotocol import types as t
from pygls.lsp.client import LanguageClient

from hapax_lsp.server import configure


class FakeServer:
    def __init__(self):
        self.fw, self.warn, self.logged = (3, 21), True, []

    def window_log_message(self, params):
        self.logged.append(params.message)


def test_configure_reads_nested_settings():
    ls = FakeServer()
    configure(ls, {"hapax": {"fw": "3.10", "warn": False}})
    assert (ls.fw, ls.warn) == ((3, 10), False)


def test_configure_keeps_firmware_and_logs_on_a_bad_value():
    ls = FakeServer()
    configure(ls, {"fw": "9.99"})
    assert ls.fw == (3, 21)
    assert "unsupported firmware" in ls.logged[0]


def test_configure_accepts_no_options():
    ls = FakeServer()
    configure(ls, None)
    assert ls.fw == (3, 21)


async def session():
    client = LanguageClient("test", "0")
    published = asyncio.get_running_loop().create_future()

    @client.feature(t.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS)
    def on_diagnostics(params):
        if not published.done():
            published.set_result(params)

    await client.start_io(sys.executable, "-m", "hapax_lsp")
    try:
        await client.initialize_async(t.InitializeParams(
            capabilities=t.ClientCapabilities(), initialization_options={"fw": "3.10"}))
        client.initialized(t.InitializedParams())
        uri = "file:///tmp/synth.txt"
        client.text_document_did_open(t.DidOpenTextDocumentParams(
            t.TextDocumentItem(uri=uri, language_id="hapax", version=1, text="TYPE POLYAT\nTYPE ")))
        diagnostics = await asyncio.wait_for(published, 10)
        completions = await client.text_document_completion_async(t.CompletionParams(
            text_document=t.TextDocumentIdentifier(uri), position=t.Position(1, 5)))
        await client.shutdown_async(None)
        client.exit(None)
        return diagnostics, completions
    finally:
        await client.stop()


def test_server_end_to_end():
    diagnostics, completions = asyncio.run(session())
    assert "type.value" in [d.code for d in diagnostics.diagnostics]  # POLYAT is 3.20+, fw is 3.10
    labels = [i.label for i in (completions.items if hasattr(completions, "items") else completions)]
    assert "POLY" in labels and "POLYAT" not in labels
