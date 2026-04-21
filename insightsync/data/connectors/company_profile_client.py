from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote, unquote, urlparse

import requests

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def slugify_company_id(name: str, *, namespace: str = "hkg") -> str:
    base = _normalize_text(name).lower()
    base = re.sub(r"[^a-z0-9]+", "-", base)
    base = base.strip("-") or "unknown-company"
    prefix = _normalize_text(namespace).lower() or "hkg"
    prefix = re.sub(r"[^a-z0-9]+", "-", prefix).strip("-") or "hkg"
    return f"{prefix}-{base}"


def normalize_public_url(raw_url: str | None) -> str | None:
    text = _normalize_text(raw_url)
    if not text:
        return None
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if text.startswith("www."):
        return f"https://{text}"
    # Handle shorthand like wikipedia.org/wiki/Tencent
    if "." in text and not text.startswith("/"):
        return f"https://{text}"
    return None


def wikipedia_title_from_url(url: str | None) -> str | None:
    normalized = normalize_public_url(url)
    if not normalized:
        return None
    parsed = urlparse(normalized)
    host = (parsed.netloc or "").lower()
    if "wikipedia.org" not in host:
        return None
    path = parsed.path.strip("/")
    if not path.startswith("wiki/"):
        return None
    title = path.split("wiki/", 1)[1]
    title = unquote(title).replace("_", " ").strip()
    return title or None


class CompanyProfileClient:
    def __init__(self, *, timeout_seconds: int = 15) -> None:
        self.timeout_seconds = max(3, int(timeout_seconds))
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": DEFAULT_USER_AGENT})

    def fetch_page_title(self, url: str) -> str | None:
        try:
            resp = self.session.get(url, timeout=self.timeout_seconds)
            resp.raise_for_status()
        except Exception:  # noqa: BLE001
            return None

        text = resp.text or ""
        m = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            return None
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        return title or None

    def fetch_wikipedia_summary(self, wikipedia_url: str) -> str | None:
        title = wikipedia_title_from_url(wikipedia_url)
        if not title:
            return None

        encoded = quote(title, safe="")
        api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        try:
            resp = self.session.get(api_url, timeout=self.timeout_seconds)
            resp.raise_for_status()
            payload = resp.json()
        except Exception:  # noqa: BLE001
            return None

        extract = payload.get("extract") if isinstance(payload, dict) else None
        return _normalize_text(extract) or None

    def enrich_public_profile(self, profile_urls: dict[str, Any]) -> dict[str, Any]:
        normalized = {
            "website": normalize_public_url(profile_urls.get("website")),
            "linkedin": normalize_public_url(profile_urls.get("linkedin")),
            "facebook": normalize_public_url(profile_urls.get("facebook")),
            "x": normalize_public_url(profile_urls.get("x")),
            "instagram": normalize_public_url(profile_urls.get("instagram")),
            "wikipedia": normalize_public_url(profile_urls.get("wikipedia")),
        }

        enrichment: dict[str, Any] = {
            "website_title": None,
            "wikipedia_summary": None,
        }

        if normalized["website"]:
            enrichment["website_title"] = self.fetch_page_title(normalized["website"])
        if normalized["wikipedia"]:
            enrichment["wikipedia_summary"] = self.fetch_wikipedia_summary(normalized["wikipedia"])

        return {
            "profile_urls": normalized,
            "enrichment": enrichment,
        }
