from __future__ import annotations

import unittest

from insightsync.data.connectors.company_profile_client import slugify_company_id


class CompanyProfileClientUtilityTests(unittest.TestCase):
    def test_slugify_company_id_includes_default_namespace(self) -> None:
        self.assertEqual(slugify_company_id("Tencent Holdings"), "hkg-tencent-holdings")
        self.assertEqual(slugify_company_id("HSBC", namespace="bank"), "bank-hsbc")


if __name__ == "__main__":
    unittest.main()
