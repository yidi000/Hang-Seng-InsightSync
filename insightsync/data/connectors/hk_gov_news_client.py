from __future__ import annotations

import calendar
import email.utils
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import requests

HK_GOV_FINANCE_RSS_EN = "https://www.news.gov.hk/en/categories/finance/html/articlelist.rss.xml"
HK_GOV_FINANCE_RSS_TC = "https://www.news.gov.hk/tc/categories/finance/html/articlelist.rss.xml"
HK_GOV_NEWS_ARCHIVE_JSP = "https://www.news.gov.hk/jsp/NewsArticle.jsp"

DEFAULT_USER_AGENT = "insightsync-hkgov-rss/1.0"
DEFAULT_ARCHIVE_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

Lang = Literal["en", "tc"]

DEFAULT_GBA_ENTERPRISE_KEYWORDS_EN: tuple[str, ...] = (
    "greater bay area",
    "guangdong",
    "shenzhen",
    "guangzhou",
    "enterprise",
    "company",
    "industry",
    "manufacturing",
    "innovation",
    "technology",
    "cross-boundary",
)

DEFAULT_GBA_ENTERPRISE_KEYWORDS_TC: tuple[str, ...] = (
    "粤港澳大湾区",
    "大湾区",
    "广东",
    "深圳",
    "广州",
    "企业",
    "公司",
    "产业",
    "制造",
    "创新",
    "科技",
    "跨境",
)

DEFAULT_GBA_GEO_KEYWORDS_EN: tuple[str, ...] = (
    "greater bay area",
    "guangdong",
    "shenzhen",
    "guangzhou",
    "hong kong",
    "macao",
)

DEFAULT_GBA_GEO_KEYWORDS_TC: tuple[str, ...] = (
    "粤港澳大湾区",
    "大湾区",
    "广东",
    "深圳",
    "广州",
    "香港",
    "澳门",
)

DEFAULT_ENTERPRISE_BIZ_KEYWORDS_EN: tuple[str, ...] = (
    "enterprise",
    "company",
    "industry",
    "manufacturing",
    "innovation",
    "technology",
    "trade",
    "investment",
    "finance",
    "business",
)

DEFAULT_ENTERPRISE_BIZ_KEYWORDS_TC: tuple[str, ...] = (
    "企业",
    "公司",
    "产业",
    "制造",
    "创新",
    "科技",
    "贸易",
    "投资",
    "金融",
    "商业",
)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _parse_pub_date(value: str) -> datetime | None:
    s = _normalize_text(value)
    if not s:
        return None
    try:
        return email.utils.parsedate_to_datetime(s)
    except Exception:
        return None


def _month_keys_between(start: datetime, end: datetime) -> list[str]:
    if start > end:
        return []
    keys: list[str] = []
    cursor = datetime(year=start.year, month=start.month, day=1)
    end_month = datetime(year=end.year, month=end.month, day=1)
    while cursor <= end_month:
        keys.append(f"{cursor.year:04d}{cursor.month:02d}")
        if cursor.month == 12:
            cursor = datetime(year=cursor.year + 1, month=1, day=1)
        else:
            cursor = datetime(year=cursor.year, month=cursor.month + 1, day=1)
    return keys


def _parse_archive_event_date(value: str) -> datetime | None:
    s = _normalize_text(value)
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _parse_date_yyyy_mm_dd(value: str) -> datetime | None:
    s = _normalize_text(value)
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except Exception:
        return None


def _subtract_months(value: datetime, months: int) -> datetime:
    if months < 0:
        raise ValueError("months must be >= 0")
    if months == 0:
        return value
    total = value.year * 12 + (value.month - 1) - months
    year = total // 12
    month = total % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def extract_hk_gov_news_id(link: Any) -> str:
    s = _normalize_text(link)
    if not s:
        return ""
    path = urlparse(s).path
    if not path:
        return ""
    name = Path(path).name
    if not name.endswith(".html"):
        return name
    return name[:-5]


class HKGovNewsClient:
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._session = session or requests.Session()
        self._session.headers.setdefault("User-Agent", user_agent)

    def _rss_url(self, language: Lang) -> str:
        if language == "en":
            return HK_GOV_FINANCE_RSS_EN
        if language == "tc":
            return HK_GOV_FINANCE_RSS_TC
        raise ValueError(f"Unsupported language: {language!r}")

    def _archive_language_code(self, language: Lang) -> str:
        if language == "en":
            return "eng"
        if language == "tc":
            return "chi"
        raise ValueError(f"Unsupported language: {language!r}")

    def _archive_referer(self, language: Lang) -> str:
        if language == "en":
            return "https://www.news.gov.hk/en/archive.html"
        if language == "tc":
            return "https://www.news.gov.hk/chi/archive.html"
        raise ValueError(f"Unsupported language: {language!r}")

    def _fetch_articles_latest_rss(
        self,
        *,
        language: Lang = "en",
        timeout: int = 60,
    ) -> list[dict[str, Any]]:
        url = self._rss_url(language)
        response = self._session.get(url, timeout=timeout)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        rows: list[dict[str, Any]] = []
        for item in root.findall(".//item"):
            title = _normalize_text(item.findtext("title"))
            link = _normalize_text(item.findtext("link"))
            pub_date = _normalize_text(item.findtext("pubDate"))
            description = _normalize_text(item.findtext("description"))
            dt = _parse_pub_date(pub_date)
            rows.append(
                {
                    "title": title,
                    "link": link,
                    "pubDate": pub_date,
                    "published_at": dt.isoformat() if dt is not None else "",
                    "description": description,
                }
            )
        return rows

    def _fetch_articles_recent_archive(
        self,
        *,
        language: Lang = "en",
        start_dt: datetime,
        end_dt: datetime,
        timeout: int = 60,
    ) -> list[dict[str, Any]]:
        if start_dt > end_dt:
            return []
        month_keys = _month_keys_between(start_dt, end_dt)
        lang_code = self._archive_language_code(language)
        referer = self._archive_referer(language)

        rows: list[dict[str, Any]] = []
        seen_links: set[str] = set()

        for month_key in month_keys:
            params = {
                "language": lang_code,
                "category": "finance",
                "date": month_key,
                "time": str(int(datetime.now().timestamp() * 1000)),
            }
            headers = {
                "Referer": referer,
                "User-Agent": DEFAULT_ARCHIVE_BROWSER_USER_AGENT,
            }
            response = self._session.get(HK_GOV_NEWS_ARCHIVE_JSP, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            root = ET.fromstring(response.content)

            for item in root.findall(".//item"):
                title = _normalize_text(item.findtext("title"))
                link = _normalize_text(item.findtext("generateHtmlPath"))
                if link.startswith("/"):
                    link = f"https://www.news.gov.hk{link}"
                event_date = _normalize_text(item.findtext("eventDate"))
                dt = _parse_archive_event_date(event_date)
                if dt is None:
                    continue
                if not (start_dt <= dt <= end_dt):
                    continue
                if not link or link in seen_links:
                    continue
                seen_links.add(link)

                description = _normalize_text(item.findtext("articleSummary"))
                rows.append(
                    {
                        "title": title,
                        "link": link,
                        "pubDate": event_date,
                        "published_at": dt.isoformat(),
                        "description": description,
                    }
                )

        rows.sort(key=lambda x: str(x.get("published_at") or ""), reverse=True)
        return rows

    def fetch_articles(
        self,
        *,
        language: Lang = "en",
        since_months: int | None = None,
        since_days: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        timeout: int = 60,
        max_items: int = 1000,
    ) -> list[dict[str, Any]]:
        has_explicit_range = bool(_normalize_text(start_date) or _normalize_text(end_date))
        if has_explicit_range:
            if not (_normalize_text(start_date) and _normalize_text(end_date)):
                raise ValueError("start_date and end_date must be provided together")
            if since_months is not None or since_days is not None:
                raise ValueError("Explicit date range cannot be combined with since_months/since_days")
            start_dt = _parse_date_yyyy_mm_dd(_normalize_text(start_date))
            end_day = _parse_date_yyyy_mm_dd(_normalize_text(end_date))
            if start_dt is None or end_day is None:
                raise ValueError("start_date/end_date must use YYYY-MM-DD format")
            end_dt = end_day + timedelta(days=1) - timedelta(seconds=1)
            rows = self._fetch_articles_recent_archive(
                language=language,
                start_dt=start_dt,
                end_dt=end_dt,
                timeout=timeout,
            )
        elif since_months is not None:
            if since_months < 0:
                raise ValueError("since_months must be >= 0")
            if since_months == 0:
                rows = self._fetch_articles_latest_rss(language=language, timeout=timeout)
            else:
                end_dt = datetime.now()
                start_dt = _subtract_months(end_dt, since_months)
                rows = self._fetch_articles_recent_archive(
                    language=language,
                    start_dt=start_dt,
                    end_dt=end_dt,
                    timeout=timeout,
                )
        elif since_days is not None:
            if since_days <= 0:
                raise ValueError("since_days must be a positive integer")
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=since_days)
            rows = self._fetch_articles_recent_archive(
                language=language,
                start_dt=start_dt,
                end_dt=end_dt,
                timeout=timeout,
            )
        else:
            rows = self._fetch_articles_latest_rss(language=language, timeout=timeout)

        if max_items == 0:
            return []
        if max_items > 0:
            return rows[:max_items]
        return rows

    def filter_gba_enterprise_news(
        self,
        *,
        articles: list[dict[str, Any]],
        language: Lang = "en",
        keywords: list[str] | tuple[str, ...] | None = None,
        require_geo_and_business: bool = True,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if keywords is None:
            keywords = (
                DEFAULT_GBA_ENTERPRISE_KEYWORDS_EN
                if language == "en"
                else DEFAULT_GBA_ENTERPRISE_KEYWORDS_TC
            )
        normalized = [k.strip().lower() for k in keywords if _normalize_text(k)]
        if not normalized:
            return []

        geo_keywords = DEFAULT_GBA_GEO_KEYWORDS_EN if language == "en" else DEFAULT_GBA_GEO_KEYWORDS_TC
        biz_keywords = (
            DEFAULT_ENTERPRISE_BIZ_KEYWORDS_EN
            if language == "en"
            else DEFAULT_ENTERPRISE_BIZ_KEYWORDS_TC
        )

        out: list[dict[str, Any]] = []
        for row in articles:
            title = _normalize_text(row.get("title"))
            desc = _normalize_text(row.get("description"))
            hay = f"{title}\n{desc}".lower()
            if not any(k in hay for k in normalized):
                continue

            if require_geo_and_business:
                has_geo = any(k in hay for k in geo_keywords)
                has_biz = any(k in hay for k in biz_keywords)
                if not (has_geo and has_biz):
                    continue

            out.append(row)
            if limit > 0 and len(out) >= limit:
                break
        return out
