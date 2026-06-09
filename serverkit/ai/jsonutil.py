"""Extract and sanitize JSON from small-model LLM output."""

from __future__ import annotations

import json
import re


def extract_first_json_object(text: str) -> str | None:
    """Return the first `{` … `}` span with string-aware brace matching, or None."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    quote = ""
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == quote:
                in_str = False
            continue
        if c in "\"'":
            in_str = True
            quote = c
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def strip_json_comments(text: str) -> str:
    """Remove // line comments (naive; helps model output with // in JSON)."""
    out_lines = []
    for line in text.splitlines():
        cut = None
        in_s = False
        esc = False
        q = ""
        for j, ch in enumerate(line):
            if in_s:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == q:
                    in_s = False
                continue
            if ch in "\"'":
                in_s = True
                q = ch
                continue
            if ch == "/" and j + 1 < len(line) and line[j + 1] == "/":
                cut = j
                break
        out_lines.append(line if cut is None else line[:cut].rstrip())
    return "\n".join(out_lines)


def strip_block_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def parse_model_json(raw: str) -> dict | None:
    """Best-effort parse of a single JSON object from model text."""
    t = raw.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()

    candidates: list[str] = []
    ex = extract_first_json_object(t)
    if ex:
        candidates.append(ex)
    start, end = t.find("{"), t.rfind("}")
    if start >= 0 and end > start:
        candidates.append(t[start : end + 1])

    seen: set[str] = set()
    for cand in candidates:
        if not cand or cand in seen:
            continue
        seen.add(cand)
        for variant in (
            cand,
            strip_json_comments(cand),
            strip_block_comments(strip_json_comments(cand)),
        ):
            try:
                out = json.loads(variant)
                if isinstance(out, dict):
                    return out
            except json.JSONDecodeError:
                continue
    return None
