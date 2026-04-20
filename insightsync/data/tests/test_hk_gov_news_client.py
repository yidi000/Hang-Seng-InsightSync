from __future__ import annotations

import unittest

from insightsync.data.connectors.hk_gov_news_client import HKGovNewsClient, extract_hk_gov_news_id


class _DummyResponse:
    def __init__(self, content: str) -> None:
        self.content = content.encode("utf-8")

    def raise_for_status(self) -> None:
        return None


class _DummySession:
    def __init__(self, *, rss_xml: str, archive_xml_by_month: dict[str, str]) -> None:
        self.rss_xml = rss_xml
        self.archive_xml_by_month = archive_xml_by_month
        self.headers: dict[str, str] = {}

    def get(self, url: str, **kwargs) -> _DummyResponse:
        if "articlelist.rss.xml" in url:
            return _DummyResponse(self.rss_xml)
        if "NewsArticle.jsp" in url:
            params = kwargs.get("params") or {}
            month = str(params.get("date") or "")
            return _DummyResponse(self.archive_xml_by_month.get(month, "<rss></rss>"))
        raise AssertionError(f"Unexpected URL in test session: {url}")


class HKGovNewsClientTests(unittest.TestCase):
    def test_extract_news_id_from_link(self) -> None:
        self.assertEqual(
            extract_hk_gov_news_id("https://www.news.gov.hk/eng/2026/04/20260420/20260420_123456_001.html"),
            "20260420_123456_001",
        )

    def test_fetch_articles_latest_rss(self) -> None:
        rss_xml = """
        <rss>
          <channel>
            <item>
              <title>Finance policy update</title>
              <link>https://www.news.gov.hk/eng/2026/04/20/a.html</link>
              <pubDate>Mon, 20 Apr 2026 09:30:00 +0800</pubDate>
              <description>Business support details.</description>
            </item>
          </channel>
        </rss>
        """
        client = HKGovNewsClient(session=_DummySession(rss_xml=rss_xml, archive_xml_by_month={}))
        rows = client.fetch_articles(language="en", since_months=0)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Finance policy update")
        self.assertTrue(rows[0]["published_at"].startswith("2026-04-20"))

    def test_fetch_articles_archive_window_and_dedup(self) -> None:
        archive_202603 = """
        <rss>
          <item>
            <title>March enterprise item</title>
            <generateHtmlPath>/eng/2026/03/15/march-item.html</generateHtmlPath>
            <eventDate>2026-03-15 10:00:00</eventDate>
            <articleSummary>Guangdong enterprise cooperation</articleSummary>
          </item>
        </rss>
        """
        archive_202604 = """
        <rss>
          <item>
            <title>Duplicate from previous month</title>
            <generateHtmlPath>/eng/2026/03/15/march-item.html</generateHtmlPath>
            <eventDate>2026-04-01 08:00:00</eventDate>
            <articleSummary>Duplicate link should be removed</articleSummary>
          </item>
          <item>
            <title>April enterprise item</title>
            <generateHtmlPath>/eng/2026/04/10/april-item.html</generateHtmlPath>
            <eventDate>2026-04-10 12:00:00</eventDate>
            <articleSummary>Shenzhen innovation business news</articleSummary>
          </item>
        </rss>
        """
        client = HKGovNewsClient(
            session=_DummySession(
                rss_xml="<rss></rss>",
                archive_xml_by_month={
                    "202603": archive_202603,
                    "202604": archive_202604,
                },
            )
        )
        rows = client.fetch_articles(language="en", start_date="2026-03-01", end_date="2026-04-30")

        self.assertEqual(len(rows), 2)
        links = [row["link"] for row in rows]
        self.assertIn("https://www.news.gov.hk/eng/2026/03/15/march-item.html", links)
        self.assertIn("https://www.news.gov.hk/eng/2026/04/10/april-item.html", links)

    def test_filter_gba_enterprise_news(self) -> None:
        client = HKGovNewsClient(session=_DummySession(rss_xml="<rss></rss>", archive_xml_by_month={}))
        articles = [
            {
                "title": "Shenzhen and Hong Kong enterprise innovation programme",
                "description": "Greater Bay Area business collaboration",
            },
            {
                "title": "Weather notice",
                "description": "No enterprise content",
            },
        ]
        filtered = client.filter_gba_enterprise_news(articles=articles, language="en", limit=10)
        self.assertEqual(len(filtered), 1)
        self.assertIn("Shenzhen", filtered[0]["title"])


if __name__ == "__main__":
    unittest.main()
