"""Tests for REPL syntax highlighting lexer."""

from __future__ import annotations

from prompt_toolkit.document import Document

from serverkit.shell.lexer import ServerKitLexer


def test_lexer_returns_style_text_fragments():
    document = Document('processes().memory_above(500)')
    get_line = ServerKitLexer().lex_document(document)
    fragments = get_line(0)
    assert isinstance(fragments, list)
    assert all(isinstance(item, tuple) and len(item) == 2 for item in fragments)
    joined = "".join(text for _, text in fragments)
    assert joined == document.text
    styles = {style for style, _ in fragments if style}
    assert "class:method" in styles


def test_lexer_empty_line():
    document = Document("")
    get_line = ServerKitLexer().lex_document(document)
    assert get_line(0) == [("", "")]


def test_lexer_prompt_session_render():
    from prompt_toolkit import PromptSession
    from prompt_toolkit.styles import Style

    from serverkit.shell.autocomplete import SDKCompleter

    style = Style.from_dict(
        {
            "string": "ansigreen",
            "number": "ansiyellow",
            "keyword": "ansibrightmagenta bold",
            "method": "ansicyan",
        }
    )
    session = PromptSession(
        lexer=ServerKitLexer(),
        style=style,
        completer=SDKCompleter(),
    )
    get_line = session.lexer.lex_document(Document("processes()"))
    fragments = get_line(0)
    assert isinstance(fragments, list)
