"""pygls wiring: settings, document events and requests, delegating to features."""

from pathlib import PurePath

from hapax import config
from hapax.rules import LATEST, parse_fw
from lsprotocol import types as t
from pygls.lsp.server import LanguageServer

from . import features


class HapaxServer(LanguageServer):
    fw = LATEST
    warn = bool(config.load().get("warn", True))


server = HapaxServer("hapax-lsp", "0.1.0", text_document_sync_kind=t.TextDocumentSyncKind.Full)


def configure(ls: HapaxServer, options) -> None:
    options = options if isinstance(options, dict) else {}
    options = options.get("hapax", options)  # didChangeConfiguration nests settings under "hapax"
    options = options if isinstance(options, dict) else {}
    if "warn" in options:
        ls.warn = bool(options["warn"])
    if "fw" in options:
        try:
            ls.fw = parse_fw(str(options["fw"]))
        except ValueError as e:
            ls.window_log_message(t.LogMessageParams(t.MessageType.Warning, f"hapax-lsp: {e}"))


def publish(ls: HapaxServer, uri: str) -> None:
    doc = ls.workspace.get_text_document(uri)
    name = PurePath(doc.path).name if doc.path else None
    ls.text_document_publish_diagnostics(t.PublishDiagnosticsParams(
        uri=uri, diagnostics=features.diagnostics(doc.source, ls.fw, name, ls.warn)))


@server.feature(t.INITIALIZE)
def initialize(ls: HapaxServer, params: t.InitializeParams):
    configure(ls, params.initialization_options)


@server.feature(t.WORKSPACE_DID_CHANGE_CONFIGURATION)
def did_change_configuration(ls: HapaxServer, params: t.DidChangeConfigurationParams):
    configure(ls, params.settings)
    for uri in ls.workspace.text_documents:
        publish(ls, uri)


@server.feature(t.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: HapaxServer, params: t.DidOpenTextDocumentParams):
    publish(ls, params.text_document.uri)


@server.feature(t.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: HapaxServer, params: t.DidChangeTextDocumentParams):
    publish(ls, params.text_document.uri)


@server.feature(
    t.TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
    t.SemanticTokensLegend(token_types=features.TOKEN_TYPES, token_modifiers=[]),
)
def semantic_tokens(ls: HapaxServer, params: t.SemanticTokensParams):
    return t.SemanticTokens(data=features.semantic_tokens(ls.workspace.get_text_document(params.text_document.uri).source))


@server.feature(t.TEXT_DOCUMENT_COMPLETION, t.CompletionOptions(trigger_characters=["[", "/", " "]))
def completion(ls: HapaxServer, params: t.CompletionParams):
    text = ls.workspace.get_text_document(params.text_document.uri).source
    return features.completion(text, params.position.line, params.position.character, ls.fw)


@server.feature(t.TEXT_DOCUMENT_CODE_ACTION)
def code_action(ls: HapaxServer, params: t.CodeActionParams):
    uri = params.text_document.uri
    action = features.fix_all(ls.workspace.get_text_document(uri).source, uri, ls.fw)
    return [action] if action else []


def main() -> None:
    server.start_io()
