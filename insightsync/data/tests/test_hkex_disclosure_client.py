from __future__ import annotations

import unittest

from insightsync.data.connectors.hkex_disclosure_client import extract_pdf_url_from_html, parse_hkex_predefined_rows


class HKEXDisclosureClientParsingTests(unittest.TestCase):
    def test_parse_predefined_rows_deduplicates_and_builds_absolute_links(self) -> None:
        payload = """
        <table>
          <tbody>
            <tr>
              <td>2026/04/18</td><td>0005</td><td>HSBC Holdings</td>
              <td><a href="/listedco/listconews/sehk/2026/0418/2026041800012.pdf">Annual Report</a></td>
            </tr>
            <tr>
              <td>2026/04/18</td><td>0005</td><td>HSBC Holdings</td>
              <td><a href="/listedco/listconews/sehk/2026/0418/2026041800012.pdf">Annual Report</a></td>
            </tr>
            <tr>
              <td>2026/04/19</td><td>0011</td><td>Hang Seng Bank</td>
              <td><a href="https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0419/2026041900001.pdf">Annual Report</a></td>
            </tr>
          </tbody>
        </table>
        """

        items = parse_hkex_predefined_rows(payload)
        self.assertEqual(len(items), 2)
        self.assertEqual(
            items[0]["detail_url"],
            "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0418/2026041800012.pdf",
        )
        self.assertEqual(items[1]["stock_code"], "0011")

    def test_extract_pdf_url_from_html_supports_iframe_and_relative_path(self) -> None:
        payload = """
        <html>
          <body>
            <iframe src="/listedco/listconews/sehk/2026/0419/2026041900001.pdf"></iframe>
          </body>
        </html>
        """

        out = extract_pdf_url_from_html(payload)
        self.assertEqual(
            out,
            "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0419/2026041900001.pdf",
        )


if __name__ == "__main__":
    unittest.main()
