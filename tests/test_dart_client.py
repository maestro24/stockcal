# -*- coding: utf-8 -*-
"""DART 배당 공시 파서 테스트 (네트워크 불필요, 픽스처 기반)."""
import io
import os
import sys
import unittest
import zipfile
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import dart_client  # noqa: E402

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def read_fixture(name, mode="r"):
    path = os.path.join(FIXTURE_DIR, name)
    if mode == "rb":
        with open(path, "rb") as f:
            return f.read()
    with open(path, encoding="utf-8") as f:
        return f.read()


def make_zip(xml_text):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("20990101000101.xml", xml_text)
    return buf.getvalue()


class TestListParsing(unittest.TestCase):
    def test_only_dividend_reports_kept(self):
        entries = dart_client.parse_list_response(read_fixture("dart_list.json"))
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["corp_name"], "테스트기업A")
        self.assertEqual(entries[1]["rcept_no"], "20990101000102")

    def test_no_result_status_returns_empty(self):
        text = '{"status": "013", "message": "조회된 데이타가 없습니다."}'
        self.assertEqual(dart_client.parse_list_response(text), [])

    def test_error_status_raises(self):
        text = '{"status": "020", "message": "요청 제한 초과"}'
        with self.assertRaises(ValueError):
            dart_client.parse_list_response(text)

    def test_report_name_variants(self):
        self.assertTrue(dart_client.is_dividend_report("현금ㆍ현물배당결정"))
        self.assertTrue(dart_client.is_dividend_report("현금·현물배당 결정"))
        self.assertFalse(dart_client.is_dividend_report("분기보고서 (2099.03)"))


class TestDocumentParsing(unittest.TestCase):
    def test_extract_fields_from_document(self):
        fields = dart_client.parse_dividend_document(read_fixture("dart_document.xml"))
        self.assertEqual(fields["exDate"], "2099-02-28")
        self.assertEqual(fields["amount"], 1500)
        self.assertEqual(fields["payDate"], "2099-03-20")

    def test_missing_fields_return_none(self):
        fields = dart_client.parse_dividend_document("<DOCUMENT>내용 없음</DOCUMENT>")
        self.assertIsNone(fields["exDate"])
        self.assertIsNone(fields["amount"])
        self.assertIsNone(fields["payDate"])

    def test_extract_document_text_from_zip(self):
        xml = read_fixture("dart_document.xml")
        self.assertIn("배당기준일", dart_client.extract_document_text(make_zip(xml)))


class TestCollectDividendItems(unittest.TestCase):
    def test_end_to_end_with_mocked_fetch(self):
        list_bytes = read_fixture("dart_list.json").encode("utf-8")
        doc_zip = make_zip(read_fixture("dart_document.xml"))

        def fake_fetch(url):
            return list_bytes if "list.json" in url else doc_zip

        items = dart_client.collect_dividend_items("dummy-key", fake_fetch)
        self.assertEqual(len(items), 2)
        item = items[0]
        self.assertEqual(item["name"], "테스트기업A")
        self.assertEqual(item["code"], "000001")
        self.assertEqual(item["exDate"], "2099-02-28")
        self.assertEqual(item["payDate"], "2099-03-20")
        self.assertEqual(item["amount"], 1500)
        self.assertEqual(item["market"], "KOSPI")
        self.assertEqual(items[1]["market"], "KOSDAQ")

    def test_document_failure_skips_item(self):
        list_bytes = read_fixture("dart_list.json").encode("utf-8")

        def fake_fetch(url):
            if "list.json" in url:
                return list_bytes
            raise OSError("network down")

        items = dart_client.collect_dividend_items("dummy-key", fake_fetch)
        self.assertEqual(items, [])


if __name__ == "__main__":
    unittest.main()
