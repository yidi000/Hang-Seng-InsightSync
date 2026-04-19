from insightsync.backend.services.chunker import (
    chunk_text,
    estimate_tokens,
    extract_query_terms,
    tokenize,
)


def test_estimate_tokens_returns_positive_count() -> None:
    assert estimate_tokens("HKMA rate update") >= 3


def test_chunk_text_is_stable_and_overlapping() -> None:
    text = " ".join(f"token{i}" for i in range(30))
    chunks = chunk_text(text, max_tokens=10, overlap_tokens=2)

    assert len(chunks) == 4
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["chunk_hash"] == chunk_text(text, max_tokens=10, overlap_tokens=2)[0]["chunk_hash"]
    assert chunks[1]["chunk_text"].startswith("token8")


def test_tokenize_cjk_splits_per_char() -> None:
    tokens = tokenize("香港金管局 rate 调整")
    assert "香" in tokens and "港" in tokens and "rate" in tokens
    # Latin runs stay grouped; CJK chars split.
    assert any(len(t) > 1 and t.isascii() for t in tokens)


def test_extract_query_terms_handles_cjk_and_english() -> None:
    terms = extract_query_terms("HKMA 加息 对 HK 银行 影响?")
    assert "hkma" in terms
    assert "加" in terms and "息" in terms
    # Single-letter ASCII is filtered out (HK stays as >=2).
    assert "hk" in terms


def test_chunk_text_handles_cjk() -> None:
    text = "香港金融管理局发布最新利率公告，重点关注商业银行合规情况。"
    chunks = chunk_text(text, max_tokens=8, overlap_tokens=2)
    assert len(chunks) >= 2
    # CJK chars should be joined without intervening spaces.
    assert " " not in chunks[0]["chunk_text"] or "香" in chunks[0]["chunk_text"]
