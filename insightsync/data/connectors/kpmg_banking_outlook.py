from __future__ import annotations

import os
from pathlib import Path

import requests

KPMG_HONG_KONG_BANKING_OUTLOOK_PDF_URL = (
    "https://assets.kpmg.com/content/dam/kpmg/cn/pdf/en/2026/01/hong-kong-banking-report-2026.pdf"
)

DEFAULT_UA = "insightsync-kpmg-fetch/1.0"


def download_kpmg_hong_kong_banking_outlook_pdf(
    dest: str | os.PathLike[str],
    *,
    url: str | None = None,
    session: requests.Session | None = None,
    timeout: int = 120,
) -> Path:
    target = Path(dest)
    pdf_url = url if url is not None else KPMG_HONG_KONG_BANKING_OUTLOOK_PDF_URL

    if target.suffix.lower() != ".pdf":
        target = target / "hong-kong-banking-outlook.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)

    sess = session or requests.Session()
    sess.headers.setdefault("User-Agent", DEFAULT_UA)

    with sess.get(pdf_url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with target.open("wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
    return target.resolve()

