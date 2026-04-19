from __future__ import annotations

import re

from insightsync.backend.utils import stable_hash

# CJK Unified Ideographs, Hiragana, Katakana, Hangul.
_CJK_RANGES = (
    ("\u3040", "\u30ff"),  # Hiragana + Katakana
    ("\u3400", "\u4dbf"),  # CJK Ext A
    ("\u4e00", "\u9fff"),  # CJK Unified
    ("\uac00", "\ud7af"),  # Hangul
    ("\uf900", "\ufaff"),  # CJK Compatibility
)


def _is_cjk(ch: str) -> bool:
    for lo, hi in _CJK_RANGES:
        if lo <= ch <= hi:
            return True
    return False


def tokenize(text: str) -> list[str]:
    """Token stream that treats each CJK character as its own token and groups
    Latin/numeric runs together.
    """

    tokens: list[str] = []
    buf: list[str] = []
    for ch in text:
        if _is_cjk(ch):
            if buf:
                tokens.append("".join(buf))
                buf = []
            tokens.append(ch)
        elif ch.isalnum() or ch == "_":
            buf.append(ch)
        elif ch.isspace():
            if buf:
                tokens.append("".join(buf))
                buf = []
        else:
            if buf:
                tokens.append("".join(buf))
                buf = []
            tokens.append(ch)
    if buf:
        tokens.append("".join(buf))
    return tokens


def estimate_tokens(text: str) -> int:
    """Estimate token count without a tokenizer dependency."""

    return max(1, len(tokenize(text)))


def _join_tokens(tokens: list[str]) -> str:
    """Re-join tokens: no space between adjacent CJK tokens, space otherwise."""

    if not tokens:
        return ""
    out = [tokens[0]]
    for prev, cur in zip(tokens, tokens[1:]):
        if _is_cjk(prev[-1]) and _is_cjk(cur[0]):
            out.append(cur)
        else:
            out.append(" ")
            out.append(cur)
    return "".join(out).strip()


def chunk_text(text: str, *, max_tokens: int = 800, overlap_tokens: int = 100) -> list[dict[str, object]]:
    """Split text into stable token-window chunks."""

    tokens = tokenize(text)
    if not tokens:
        return []
    chunks: list[dict[str, object]] = []
    start = 0
    while start < len(tokens):
        end = min(len(tokens), start + max_tokens)
        chunk = _join_tokens(tokens[start:end])
        chunks.append(
            {
                "chunk_index": len(chunks),
                "chunk_text": chunk,
                "chunk_hash": stable_hash(chunk),
                "token_count": estimate_tokens(chunk),
            }
        )
        if end >= len(tokens):
            break
        start = max(0, end - overlap_tokens)
    return chunks


# Regex that matches meaningful query terms: CJK single chars OR Latin/numeric runs >= 2.
_QUERY_TERM_RE = re.compile(
    r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uf900-\ufaff]|"
    r"[A-Za-z0-9]{2,}"
)


def extract_query_terms(question: str) -> list[str]:
    """Return lowercased search terms suitable for lexical fallback.

    CJK characters are returned as single-char terms; Latin/numeric runs of
    length >=2 are kept as-is and lowercased.
    """

    seen: set[str] = set()
    terms: list[str] = []
    for match in _QUERY_TERM_RE.finditer(question):
        term = match.group(0).lower()
        if term and term not in seen:
            seen.add(term)
            terms.append(term)
    return terms
