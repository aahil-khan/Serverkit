"""Lightweight syntax highlighting for the ServerKit REPL prompt."""

from __future__ import annotations

import re

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text.base import StyleAndTextTuples
from prompt_toolkit.lexers import Lexer

from serverkit.shell.parser import strip_shell_comment

_TOKEN_RE = re.compile(
    r"""
    (?P<string>'[^']*'|"[^"]*")
    |(?P<number>\b\d+(?:\.\d+)?\b)
    |(?P<method>\.[a-zA-Z_][a-zA-Z0-9_]*\s*\()
    |(?P<call>\b[a-zA-Z_][a-zA-Z0-9_]*\s*\()
    |(?P<keyword>\b(?:ask|connect|disconnect|help|menu|run|import|workflow|exit|quit)\b)
    """,
    re.VERBOSE,
)


def _style_for_kind(kind: str | None) -> str:
    mapping = {
        "string": "class:string",
        "number": "class:number",
        "method": "class:method",
        "call": "class:method",
        "keyword": "class:keyword",
        "comment": "class:comment",
    }
    return mapping.get(kind or "", "")


def _line_fragments(line: str) -> StyleAndTextTuples:
    if not line:
        return [("", "")]
    command = strip_shell_comment(line)
    fragments: StyleAndTextTuples = []
    pos = 0
    for match in _TOKEN_RE.finditer(command):
        if match.start() > pos:
            fragments.append(("", command[pos : match.start()]))
        fragments.append((_style_for_kind(match.lastgroup), match.group()))
        pos = match.end()
    if pos < len(command):
        fragments.append(("", command[pos:]))
    if len(command) < len(line):
        if fragments and fragments[-1][0] == "":
            fragments[-1] = ("class:comment", fragments[-1][1] + line[len(command) :])
        else:
            fragments.append(("class:comment", line[len(command) :]))
    return fragments


class ServerKitLexer(Lexer):
    """Regex-based highlighter for SDK-style shell input."""

    def lex_document(self, document: Document):
        lines = document.lines

        def get_line(lineno: int) -> StyleAndTextTuples:
            try:
                return _line_fragments(lines[lineno])
            except IndexError:
                return []

        return get_line
