# -*- coding: utf-8 -*-
"""validate.py 스키마 검증 테스트."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import validate  # noqa: E402


def valid_ipo_item():
    return {
        "name": "테스트기업A",
        "code": "000001",
        "subStart": "2099-01-20",
        "subEnd": "2099-01-21",
        "listDate": "2099-01-30",
        "priceBandLow": 10000,
        "priceBandHigh": 12000,
        "finalPrice": 12000,
        "underwriters": ["더미증권(주)"],
        "market": "KOSDAQ",
    }


def valid_dividend_item():
    return {
        "name": "테스트기업A",
        "code": "000001",
        "exDate": "2099-02-28",
        "payDate": "2099-03-20",
        "amount": 1500,
        "market": "KOSPI",
    }


class TestIpoItem(unittest.TestCase):
    def test_valid_item_passes(self):
        self.assertEqual(validate.validate_ipo_item(valid_ipo_item()), [])

    def test_nullable_fields_pass(self):
        item = valid_ipo_item()
        for key in ("code", "listDate", "priceBandLow", "priceBandHigh",
                    "finalPrice", "market"):
            item[key] = None
        self.assertEqual(validate.validate_ipo_item(item), [])

    def test_missing_field_fails(self):
        item = valid_ipo_item()
        del item["subStart"]
        errors = validate.validate_ipo_item(item)
        self.assertTrue(any("subStart" in e for e in errors))

    def test_bad_date_format_fails(self):
        item = valid_ipo_item()
        item["subStart"] = "2099/01/20"
        self.assertTrue(validate.validate_ipo_item(item))

    def test_reversed_subscription_dates_fail(self):
        item = valid_ipo_item()
        item["subStart"], item["subEnd"] = "2099-01-22", "2099-01-21"
        errors = validate.validate_ipo_item(item)
        self.assertTrue(any("subStart" in e for e in errors))

    def test_wrong_type_fails(self):
        item = valid_ipo_item()
        item["finalPrice"] = "12,000"
        self.assertTrue(validate.validate_ipo_item(item))

    def test_invalid_market_fails(self):
        item = valid_ipo_item()
        item["market"] = "NASDAQ"
        self.assertTrue(validate.validate_ipo_item(item))

    def test_reversed_price_band_fails(self):
        item = valid_ipo_item()
        item["priceBandLow"], item["priceBandHigh"] = 12000, 10000
        self.assertTrue(validate.validate_ipo_item(item))

    def test_empty_name_fails(self):
        item = valid_ipo_item()
        item["name"] = "  "
        self.assertTrue(validate.validate_ipo_item(item))


class TestDividendItem(unittest.TestCase):
    def test_valid_item_passes(self):
        self.assertEqual(validate.validate_dividend_item(valid_dividend_item()), [])

    def test_missing_ex_date_fails(self):
        item = valid_dividend_item()
        del item["exDate"]
        self.assertTrue(validate.validate_dividend_item(item))

    def test_bad_ex_date_format_fails(self):
        item = valid_dividend_item()
        item["exDate"] = "20990228"
        self.assertTrue(validate.validate_dividend_item(item))

    def test_negative_amount_fails(self):
        item = valid_dividend_item()
        item["amount"] = -1
        self.assertTrue(validate.validate_dividend_item(item))

    def test_nullable_fields_pass(self):
        item = valid_dividend_item()
        for key in ("code", "payDate", "amount", "market"):
            item[key] = None
        self.assertEqual(validate.validate_dividend_item(item), [])


class TestPayload(unittest.TestCase):
    def test_seed_payload_passes(self):
        payload = {"updated": None, "source": "KRX KIND / DART", "items": []}
        self.assertEqual(validate.validate_ipo_payload(payload), [])

    def test_payload_with_bad_item_fails(self):
        payload = {"updated": "2099-01-01T06:30:00+09:00", "source": "DART",
                   "items": [{"name": "테스트기업A"}]}
        self.assertTrue(validate.validate_dividend_payload(payload))

    def test_payload_missing_keys_fails(self):
        self.assertTrue(validate.validate_ipo_payload({"items": []}))

    def test_payload_items_not_list_fails(self):
        payload = {"updated": None, "source": "DART", "items": {}}
        self.assertTrue(validate.validate_dividend_payload(payload))


if __name__ == "__main__":
    unittest.main()
