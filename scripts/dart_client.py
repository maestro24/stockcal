# -*- coding: utf-8 -*-
"""DART OpenAPI 배당 공시 수집 헬퍼.

- list.json 으로 최근 '현금ㆍ현물배당결정' 공시 목록 조회
- document.xml (zip) 에서 배당기준일/1주당 배당금/지급예정일 추출

표준 라이브러리만 사용. 네트워크 호출부는 인자로 주입 가능하게 하여
테스트에서 mock 할 수 있게 한다.
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import datetime, timedelta

LIST_URL = "https://opendart.fss.or.kr/api/list.json"
DOC_URL = "https://opendart.fss.or.kr/api/document.xml"

# 공시명에 쓰이는 가운뎃점 이형 문자들
_DIVIDEND_NAME_RE = re.compile(r"현금\s*[ㆍ·\.]?\s*현물\s*배당\s*결정")
_KOREAN_DATE_RE = re.compile(
    r"(\d{4})\s*[년.\-/]\s*(\d{1,2})\s*[월.\-/]\s*(\d{1,2})")
_TAG_RE = re.compile(r"<[^>]+>")
_MAX_DOCUMENTS = 20


def is_dividend_report(report_nm: str) -> bool:
    return bool(_DIVIDEND_NAME_RE.search(report_nm or ""))


def parse_list_response(text: str) -> list:
    """list.json 응답에서 배당결정 공시만 추린다."""
    data = json.loads(text)
    if data.get("status") != "000":
        if data.get("status") == "013":  # 조회 결과 없음
            return []
        raise ValueError(f"DART list.json 오류: {data.get('status')} {data.get('message')}")
    results = []
    for entry in data.get("list") or []:
        if not is_dividend_report(entry.get("report_nm", "")):
            continue
        results.append({
            "corp_name": entry.get("corp_name"),
            "stock_code": (entry.get("stock_code") or "").strip() or None,
            "corp_cls": entry.get("corp_cls"),
            "rcept_no": entry.get("rcept_no"),
        })
    return results


def build_list_url(api_key: str, days: int = 30, page_count: int = 100) -> str:
    end = datetime.now()
    begin = end - timedelta(days=days)
    return (
        f"{LIST_URL}?crtfc_key={api_key}"
        f"&bgn_de={begin:%Y%m%d}&end_de={end:%Y%m%d}"
        f"&page_no=1&page_count={page_count}"
    )


def build_document_url(api_key: str, rcept_no: str) -> str:
    return f"{DOC_URL}?crtfc_key={api_key}&rcept_no={rcept_no}"


def extract_document_text(zip_bytes: bytes) -> str:
    """document.xml 응답(zip)에서 첫 XML 문서 텍스트를 꺼낸다."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".xml")]
        if not names:
            raise ValueError("zip 안에 XML 문서가 없음")
        raw = archive.read(names[0])
    for encoding in ("utf-8", "cp949"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _normalize_date(text: str):
    match = _KOREAN_DATE_RE.search(text or "")
    if not match:
        return None
    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _find_after(plain: str, label_re: str, window: int = 120):
    match = re.search(label_re, plain)
    if not match:
        return None
    return plain[match.end():match.end() + window]


def parse_dividend_document(xml_text: str) -> dict:
    """공시 본문에서 배당기준일(exDate), 1주당 배당금(amount), 지급예정일(payDate) 추출.

    반환: {"exDate": str|None, "amount": int|None, "payDate": str|None}
    """
    plain = _TAG_RE.sub(" ", xml_text)
    plain = " ".join(plain.split())

    result = {"exDate": None, "amount": None, "payDate": None}

    chunk = _find_after(plain, r"배당\s*기준일")
    if chunk:
        result["exDate"] = _normalize_date(chunk)

    chunk = _find_after(plain, r"1\s*주당\s*배당금")
    if chunk:
        num = re.search(r"([\d,]{1,20})", chunk)
        if num:
            digits = num.group(1).replace(",", "")
            if digits.isdigit():
                result["amount"] = int(digits)

    chunk = _find_after(plain, r"배당금\s*지급\s*예정\s*일")
    if chunk:
        result["payDate"] = _normalize_date(chunk)

    return result


def _market_from_corp_cls(corp_cls):
    return {"Y": "KOSPI", "K": "KOSDAQ", "N": "KONEX"}.get(corp_cls)


def collect_dividend_items(api_key: str, fetch) -> list:
    """배당결정 공시 목록 → dividend.json 아이템 리스트.

    fetch: callable(url) -> bytes (네트워크 함수 주입)
    본문 파싱에 실패한 공시는 건너뛴다 (가짜/불완전 데이터 금지).
    """
    listing = parse_list_response(fetch(build_list_url(api_key)).decode("utf-8"))
    items = []
    for entry in listing[:_MAX_DOCUMENTS]:
        rcept_no = entry.get("rcept_no")
        if not rcept_no:
            continue
        try:
            text = extract_document_text(fetch(build_document_url(api_key, rcept_no)))
            fields = parse_dividend_document(text)
        except Exception:
            continue
        if not fields["exDate"]:
            continue
        items.append({
            "name": entry.get("corp_name") or "",
            "code": entry.get("stock_code"),
            "exDate": fields["exDate"],
            "payDate": fields["payDate"],
            "amount": fields["amount"],
            "market": _market_from_corp_cls(entry.get("corp_cls")),
        })
    items.sort(key=lambda it: (it["exDate"], it["name"]))
    return items
