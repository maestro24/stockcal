# -*- coding: utf-8 -*-
"""collect.py 실패 안전성 테스트 — 네트워크 없이 실행.

핵심 보장:
- 수집 실패(네트워크/파싱) 시 기존 data/*.json 을 건드리지 않고 exit 0
- 수집 결과가 기존과 동일하면 파일을 다시 쓰지 않음
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import collect  # noqa: E402
import validate  # noqa: E402

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

EXISTING_IPO = {
    "updated": "2099-01-01T06:30:00+09:00",
    "source": "KRX KIND / DART",
    "items": [{
        "name": "테스트기업A", "code": None,
        "subStart": "2099-01-20", "subEnd": "2099-01-21",
        "listDate": None, "priceBandLow": None, "priceBandHigh": None,
        "finalPrice": None, "underwriters": [], "market": None,
    }],
}
EXISTING_DIVIDEND = {
    "updated": "2099-01-01T06:30:00+09:00",
    "source": "DART",
    "items": [{
        "name": "테스트기업A", "code": "000001",
        "exDate": "2099-02-28", "payDate": None, "amount": 1500, "market": None,
    }],
}


class CollectSafetyBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        data_dir = Path(self.tmp.name)
        self.ipo_path = data_dir / "ipo.json"
        self.dividend_path = data_dir / "dividend.json"
        self.ipo_path.write_text(
            json.dumps(EXISTING_IPO, ensure_ascii=False), encoding="utf-8")
        self.dividend_path.write_text(
            json.dumps(EXISTING_DIVIDEND, ensure_ascii=False), encoding="utf-8")
        for name, value in (("IPO_PATH", self.ipo_path),
                            ("DIVIDEND_PATH", self.dividend_path)):
            patcher = mock.patch.object(collect, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def read(self, path):
        return json.loads(path.read_text(encoding="utf-8"))


class TestNetworkFailureKeepsFiles(CollectSafetyBase):
    def test_kind_network_error_preserves_ipo_json_and_exits_zero(self):
        with mock.patch.object(collect, "fetch_url",
                               side_effect=OSError("network unreachable")), \
             mock.patch.dict(os.environ, {"DART_API_KEY": ""}):
            exit_code = collect.run()
        self.assertEqual(exit_code, 0)
        self.assertEqual(self.read(self.ipo_path), EXISTING_IPO)
        self.assertEqual(self.read(self.dividend_path), EXISTING_DIVIDEND)

    def test_dart_network_error_preserves_dividend_json(self):
        with mock.patch.object(collect, "fetch_url",
                               side_effect=OSError("network unreachable")), \
             mock.patch.dict(os.environ, {"DART_API_KEY": "dummy-key"}):
            exit_code = collect.run()
        self.assertEqual(exit_code, 0)
        self.assertEqual(self.read(self.dividend_path), EXISTING_DIVIDEND)

    def test_garbage_html_preserves_ipo_json(self):
        with mock.patch.object(collect, "fetch_kind_ipo_html",
                               return_value="<html><body>점검중</body></html>"), \
             mock.patch.dict(os.environ, {"DART_API_KEY": ""}):
            exit_code = collect.run()
        self.assertEqual(exit_code, 0)
        self.assertEqual(self.read(self.ipo_path), EXISTING_IPO)

    def test_missing_dart_key_skips_dividend(self):
        with mock.patch.object(collect, "fetch_kind_ipo_html",
                               side_effect=OSError("down")), \
             mock.patch.dict(os.environ, {"DART_API_KEY": ""}):
            exit_code = collect.run()
        self.assertEqual(exit_code, 0)
        self.assertEqual(self.read(self.dividend_path), EXISTING_DIVIDEND)


class TestSuccessfulCollection(CollectSafetyBase):
    def fixture_html(self):
        path = os.path.join(FIXTURE_DIR, "kind_pubofr_sub.html")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_valid_html_updates_ipo_json(self):
        with mock.patch.object(collect, "fetch_kind_ipo_html",
                               return_value=self.fixture_html()), \
             mock.patch.dict(os.environ, {"DART_API_KEY": ""}):
            exit_code = collect.run()
        self.assertEqual(exit_code, 0)
        payload = self.read(self.ipo_path)
        self.assertEqual(len(payload["items"]), 2)
        self.assertIsNotNone(payload["updated"])
        self.assertEqual(validate.validate_ipo_payload(payload), [])

    def test_unchanged_items_do_not_rewrite_file(self):
        html = self.fixture_html()
        with mock.patch.object(collect, "fetch_kind_ipo_html", return_value=html), \
             mock.patch.dict(os.environ, {"DART_API_KEY": ""}):
            collect.run()
            first = self.ipo_path.read_text(encoding="utf-8")
            first_mtime = self.ipo_path.stat().st_mtime_ns
            collect.run()
        self.assertEqual(self.ipo_path.read_text(encoding="utf-8"), first)
        self.assertEqual(self.ipo_path.stat().st_mtime_ns, first_mtime)

    def test_invalid_items_never_written(self):
        broken = [{"name": "테스트기업A"}]  # 필수 필드 누락
        with self.assertRaises(collect.CollectError):
            collect.update_json_file(
                self.ipo_path, "KRX KIND / DART", broken,
                validate.validate_ipo_payload)
        self.assertEqual(self.read(self.ipo_path), EXISTING_IPO)


if __name__ == "__main__":
    unittest.main()
