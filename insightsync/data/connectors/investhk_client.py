from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

INVESTHK_BASE_URL = "https://www.investhk.gov.hk"
INVESTHK_NEWS_JSON_URL_TEMPLATE = "https://www.investhk.gov.hk/data/news/{lang}.json"
DEFAULT_USER_AGENT = "insightsync-investhk/1.0"


def parse_multiple_json(text: str) -> list[Any]:
    """Parse payloads that may contain multiple concatenated JSON objects."""
    decoder = json.JSONDecoder()
    out: list[Any] = []
    idx = 0
    payload = text.strip()

    while idx < len(payload):
        while idx < len(payload) and payload[idx] in " \t\n\r":
            idx += 1
        if idx >= len(payload):
            break
        try:
            obj, end_idx = decoder.raw_decode(payload, idx)
        except json.JSONDecodeError:
            break
        out.append(obj)
        idx = end_idx
    return out


def extract_news_items(text: str) -> list[dict[str, Any]]:
    """Extract InvestHK news item dictionaries from JSON payload text."""
    objects = parse_multiple_json(text)
    extracted: list[dict[str, Any]] = []

    for obj in objects:
        if isinstance(obj, list):
            extracted.extend(item for item in obj if isinstance(item, dict))
            continue
        if not isinstance(obj, dict):
            continue

        matched = False
        for key in ("results", "data", "items", "news"):
            value = obj.get(key)
            if isinstance(value, list):
                extracted.extend(item for item in value if isinstance(item, dict))
                matched = True
                break
            if isinstance(value, dict):
                nested = value.get("results")
                if isinstance(nested, list):
                    extracted.extend(item for item in nested if isinstance(item, dict))
                    matched = True
                    break

        if not matched and ("title" in obj or "url" in obj):
            extracted.append(obj)

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in extracted:
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        publish_date = str(item.get("publishDate") or item.get("date") or "").strip()
        key = (title, url, publish_date)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


class InvestHKNewsClient:
    def __init__(
        self,
        *,
        base_url: str = INVESTHK_BASE_URL,
        session: requests.Session | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout_seconds: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

        if session is not None:
            self.session = session
        else:
            self.session = requests.Session()
            retry = Retry(
                total=3,
                backoff_factor=1.5,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=frozenset(["GET"]),
            )
            adapter = HTTPAdapter(max_retries=retry)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)

        self.session.headers.setdefault("User-Agent", user_agent)
        self.session.headers.setdefault("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.7")

    def build_news_json_url(self, *, language: str = "zh-cn") -> str:
        lang = (language or "zh-cn").strip().lower()
        return INVESTHK_NEWS_JSON_URL_TEMPLATE.format(lang=lang)

    def build_full_url(self, url: str) -> str:
        raw = (url or "").strip()
        if not raw:
            return ""
        if raw.startswith("http://") or raw.startswith("https://"):
            return raw
        return urljoin(self.base_url + "/", raw)

    def fetch_news_items(self, *, language: str = "zh-cn", json_url: str | None = None) -> list[dict[str, Any]]:
        url = (json_url or "").strip() or self.build_news_json_url(language=language)
        resp = self.session.get(url, timeout=self.timeout_seconds)
        resp.raise_for_status()
        return extract_news_items(resp.text)

    def fetch_article_text(self, url: str) -> str:
        full_url = self.build_full_url(url)
        if not full_url:
            return ""

        resp = self.session.get(full_url, timeout=self.timeout_seconds)
        resp.raise_for_status()
        resp.encoding = "utf-8"

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "lxml")
        content_tag = (
            soup.select_one(".innerPage__content")
            or soup.select_one(".textBlock")
            or soup.select_one(".articleDetail")
            or soup.select_one("article")
            or soup.select_one("main")
        )
        if content_tag is None:
            return ""

        for tag in content_tag.select(
            "nav, script, style, footer, .sidebar, .breadcrumbRow, .heroSlider, .contactForm, .contactCta"
        ):
            tag.decompose()

        text = content_tag.get_text(separator="\n", strip=True)
        return re.sub(r"\n{3,}", "\n\n", text).strip()
