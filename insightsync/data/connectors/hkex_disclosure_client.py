from __future__ import annotations

import base64
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HKEX_BASE_URL = "https://www1.hkexnews.hk"
HKEX_PREDEFINED_DOCS_URL = (
    "https://www1.hkexnews.hk/search/predefineddoc.xhtml?lang=zh&predefineddocuments=3"
)
DEFAULT_USER_AGENT = "insightsync-hkex/1.0"


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _safe_name(name: str) -> str:
    out = _normalize_text(name)
    out = re.sub(r'[<>:"/\\|?*\n\r\t]+', "_", out)
    out = re.sub(r"\s+", " ", out)
    return out[:200] or "untitled"


def _absolute_url(url: str, *, base_url: str = HKEX_BASE_URL) -> str:
    raw = _normalize_text(url)
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return urljoin(base_url.rstrip("/") + "/", raw)


def parse_hkex_predefined_rows(html_text: str, *, base_url: str = HKEX_BASE_URL) -> list[dict[str, str]]:
    """Parse disclosure rows from the HKEX predefined-documents list page."""
    soup = BeautifulSoup(html_text, "lxml")
    extracted: list[dict[str, str]] = []

    rows = soup.select("tbody tr") or soup.select("table tr")
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        publish_date = _normalize_text(cols[0].get_text())
        stock_code = _normalize_text(cols[1].get_text())
        company_name = _normalize_text(cols[2].get_text())
        link = cols[3].find("a", href=True)
        if link is None:
            continue

        href = _absolute_url(_normalize_text(link.get("href")), base_url=base_url)
        title = _normalize_text(link.get_text())
        extracted.append(
            {
                "publish_date": publish_date,
                "stock_code": stock_code,
                "company_name": company_name,
                "title": title,
                "detail_url": href,
            }
        )

    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in extracted:
        key = (
            item.get("publish_date", ""),
            item.get("stock_code", ""),
            item.get("detail_url", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def extract_pdf_url_from_html(html_text: str, *, base_url: str = HKEX_BASE_URL) -> str | None:
    """Extract a likely PDF URL from an HKEX detail page HTML payload."""
    soup = BeautifulSoup(html_text, "lxml")
    selectors = (
        "a[href$='.pdf']",
        "a[href*='.pdf']",
        "iframe[src*='.pdf']",
        "embed[src*='.pdf']",
        "object[data*='.pdf']",
    )
    for selector in selectors:
        node = soup.select_one(selector)
        if node is None:
            continue
        ref = node.get("href") or node.get("src") or node.get("data")
        out = _absolute_url(_normalize_text(ref), base_url=base_url)
        if out:
            return out

    m = re.search(r"(https?://[^\s'\"]+\.pdf(?:\?[^\s'\"]*)?)", html_text, flags=re.IGNORECASE)
    if m:
        return m.group(1)

    m = re.search(r"(['\"])(/[^'\"]+\.pdf(?:\?[^'\"]*)?)\1", html_text, flags=re.IGNORECASE)
    if m:
        return _absolute_url(m.group(2), base_url=base_url)
    return None


class HKEXDisclosureClient:
    def __init__(
        self,
        *,
        base_url: str = HKEX_BASE_URL,
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

    def fetch_predefined_items(self, *, list_url: str = HKEX_PREDEFINED_DOCS_URL) -> list[dict[str, str]]:
        resp = self.session.get(list_url, timeout=self.timeout_seconds)
        resp.raise_for_status()
        if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding or "utf-8"
        return parse_hkex_predefined_rows(resp.text, base_url=self.base_url)

    def resolve_pdf_url(self, detail_url: str) -> str | None:
        if not detail_url:
            return None
        if detail_url.lower().endswith(".pdf"):
            return detail_url

        resp = self.session.get(detail_url, timeout=self.timeout_seconds)
        resp.raise_for_status()
        if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding or "utf-8"
        return extract_pdf_url_from_html(resp.text, base_url=self.base_url)

    def download_pdf(self, pdf_url: str, destination: str | Path) -> Path:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.session.get(pdf_url, timeout=self.timeout_seconds, stream=True) as resp:
            resp.raise_for_status()
            with path.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
        return path

    def download_with_selenium(
        self,
        detail_url: str,
        *,
        download_dir: str | Path,
        headless: bool = True,
        wait_seconds: int = 30,
        page_wait_seconds: float = 1.0,
    ) -> Path | None:
        """Open an HKEX detail URL and capture browser-triggered PDF downloads."""

        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        out_dir = Path(download_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        before = {p.name for p in out_dir.iterdir() if p.is_file()}

        opts = Options()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--window-size=1920,1080")
        prefs = {
            "download.default_directory": str(out_dir.resolve()),
            "download.prompt_for_download": False,
            "profile.default_content_settings.popups": 0,
            "plugins.always_open_pdf_externally": True,
        }
        opts.add_experimental_option("prefs", prefs)

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
        try:
            try:
                driver.execute_cdp_cmd(
                    "Page.setDownloadBehavior",
                    {"behavior": "allow", "downloadPath": str(out_dir.resolve())},
                )
            except Exception:
                try:
                    driver.execute_cdp_cmd(
                        "Browser.setDownloadBehavior",
                        {"behavior": "allow", "downloadPath": str(out_dir.resolve())},
                    )
                except Exception:
                    pass

            driver.get(detail_url)
            time.sleep(max(0.1, page_wait_seconds))

            current_url = (driver.current_url or "").strip()
            if current_url.lower().endswith(".pdf"):
                pass
            else:
                candidate = driver.execute_script(
                    """
                    var nodes = document.querySelectorAll("a[href*='.pdf'],iframe[src*='.pdf'],embed[src*='.pdf'],object[data*='.pdf']");
                    for (var i = 0; i < nodes.length; i++) {
                      var v = nodes[i].href || nodes[i].src || nodes[i].getAttribute('data');
                      if (v) { return v; }
                    }
                    return null;
                    """
                )
                if candidate:
                    full = _absolute_url(str(candidate), base_url=self.base_url)
                    driver.execute_script("window.open(arguments[0], '_blank');", full)

            blob_url = driver.execute_script(
                """
                var nodes = document.querySelectorAll('iframe,embed,object,a');
                for (var i = 0; i < nodes.length; i++) {
                  var v = nodes[i].src || nodes[i].href || nodes[i].getAttribute('data');
                  if (v && v.indexOf('blob:') === 0) { return v; }
                }
                return null;
                """
            )
            if blob_url:
                b64 = driver.execute_async_script(
                    """
                    var blobUrl = arguments[0];
                    var callback = arguments[arguments.length - 1];
                    fetch(blobUrl).then(function(r){return r.arrayBuffer();}).then(function(buf){
                      var bytes = new Uint8Array(buf);
                      var CH = 0x8000;
                      var binary = '';
                      for (var i = 0; i < bytes.length; i += CH) {
                        binary += String.fromCharCode.apply(null, bytes.subarray(i, i + CH));
                      }
                      callback(btoa(binary));
                    }).catch(function(){ callback(null); });
                    """,
                    blob_url,
                )
                if b64:
                    blob_path = out_dir / f"blob_{int(time.time())}.pdf"
                    blob_path.write_bytes(base64.b64decode(b64))

            deadline = time.time() + max(1, int(wait_seconds))
            while time.time() < deadline:
                files = [p for p in out_dir.iterdir() if p.is_file()]
                names = {p.name for p in files}
                new_names = [name for name in names - before if not name.endswith(".crdownload")]
                if new_names and not any(name.endswith(".crdownload") for name in names):
                    newest = max((out_dir / name for name in new_names), key=lambda p: p.stat().st_mtime)
                    if newest.suffix.lower() == ".pdf":
                        return newest
                    safe = out_dir / f"{_safe_name(newest.stem)}.pdf"
                    newest.replace(safe)
                    return safe
                time.sleep(0.5)
            return None
        finally:
            try:
                driver.quit()
            except Exception:
                pass
