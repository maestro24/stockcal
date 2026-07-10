# -*- coding: utf-8 -*-
"""KIND 공모주 HTML 파서 테스트 (네트워크 불필요, 픽스처 기반)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import kind_parser  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "kind_pubofr_sub.html")


def load_fixture():
    with open(FIXTURE, encoding="utf-8") as f:
        return f.read()


class TestParseRows(unittest.TestCase):
    def setUp(self):
        self.rows = kind_parser.parse_rows(load_fixture())

    def test_row_count(self):
        self.assertEqual(len(self.rows), 3)

    def test_cells_per_row(self):
        for row in self.rows:
            self.assertEqual(len(row["cells"]), 9)

    def test_market_alt_extracted(self):
        self.assertEqual(self.rows[0]["market_alt"], "코스닥")
        self.assertEqual(self.rows[1]["market_alt"], "유가증권")
        self.assertIsNone(self.rows[2]["market_alt"])

    def test_acptno_extracted(self):
        self.assertEqual(self.rows[0]["acptno"], "20990101000001")


class TestToIpoItems(unittest.TestCase):
    def setUp(self):
        self.items = kind_parser.to_ipo_items(kind_parser.parse_rows(load_fixture()))

    def test_row_without_subscription_dates_skipped(self):
        names = [item["name"] for item in self.items]
        self.assertNotIn("테스트기업C", names)
        self.assertEqual(len(self.items), 2)

    def test_sorted_by_sub_start(self):
        self.assertEqual(self.items[0]["name"], "테스트기업B")
        self.assertEqual(self.items[1]["name"], "테스트기업A")

    def test_full_item_fields(self):
        item = next(i for i in self.items if i["name"] == "테스트기업A")
        self.assertEqual(item["subStart"], "2099-01-20")
        self.assertEqual(item["subEnd"], "2099-01-21")
        self.assertEqual(item["listDate"], "2099-01-30")
        self.assertEqual(item["finalPrice"], 12000)
        self.assertEqual(item["underwriters"], ["더미증권(주)"])
        self.assertEqual(item["market"], "KOSDAQ")
        self.assertIsNone(item["code"])
        self.assertIsNone(item["priceBandLow"])
        self.assertIsNone(item["priceBandHigh"])

    def test_empty_optional_fields_are_null(self):
        item = next(i for i in self.items if i["name"] == "테스트기업B")
        self.assertIsNone(item["listDate"])
        self.assertIsNone(item["finalPrice"])
        self.assertEqual(item["market"], "KOSPI")
        self.assertEqual(item["underwriters"], ["가나다증권(주)", "라마바증권(주)"])

    def test_empty_html_returns_no_rows(self):
        self.assertEqual(kind_parser.parse_rows("<html><body></body></html>"), [])


if __name__ == "__main__":
    unittest.main()
