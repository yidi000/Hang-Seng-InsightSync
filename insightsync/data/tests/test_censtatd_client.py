from __future__ import annotations

import unittest

from insightsync.data.connectors.censtatd_client import extract_censtatd_rows


class CENSTATDClientParsingTests(unittest.TestCase):
    def test_extract_rows_returns_list_items(self) -> None:
        payload = {
            "header": {"status": {"code": 0}},
            "dataSet": [
                {"freq": "M", "period": "202601", "sv": "VAL_RS", "figure": 100},
                {"freq": "M", "period": "202602", "sv": "VAL_RS", "figure": 110},
            ],
        }
        rows = extract_censtatd_rows(payload)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["period"], "202601")


if __name__ == "__main__":
    unittest.main()
