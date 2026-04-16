from __future__ import annotations

import unittest

from insightsync.data.connectors.investhk_client import InvestHKNewsClient, extract_news_items, parse_multiple_json


class InvestHKClientParsingTests(unittest.TestCase):
    def test_parse_multiple_json_handles_concatenated_documents(self) -> None:
        payload = """
        [{\"title\": \"A\", \"url\": \"/a\"}]
        {\"results\": [{\"title\": \"B\", \"url\": \"/b\"}]}
        {\"title\": \"C\", \"url\": \"/c\"}
        """
        objects = parse_multiple_json(payload)
        self.assertEqual(len(objects), 3)

    def test_extract_news_items_flattens_shapes_and_deduplicates(self) -> None:
        payload = """
        [
          {\"title\": \"A\", \"url\": \"/a\", \"publishDate\": \"2026-01-02\"},
          {\"title\": \"A\", \"url\": \"/a\", \"publishDate\": \"2026-01-02\"}
        ]
        {\"data\": {\"results\": [{\"title\": \"B\", \"url\": \"/b\"}]}}
        {\"title\": \"C\", \"url\": \"/c\"}
        """
        items = extract_news_items(payload)
        titles = [item.get("title") for item in items]
        self.assertEqual(titles, ["A", "B", "C"])

    def test_build_full_url_supports_relative_and_absolute_paths(self) -> None:
        client = InvestHKNewsClient(base_url="https://www.investhk.gov.hk")
        self.assertEqual(
            client.build_full_url("/zh-cn/news/sample"),
            "https://www.investhk.gov.hk/zh-cn/news/sample",
        )
        self.assertEqual(
            client.build_full_url("https://example.com/news"),
            "https://example.com/news",
        )


if __name__ == "__main__":
    unittest.main()
