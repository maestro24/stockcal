# -*- coding: utf-8 -*-
"""KRX KIND 공모주(공모진행현황) HTML 파서.

kind.krx.co.kr /listinvstg/pubofrprogcom.do (method=searchPubofrProgComSub)
응답 HTML 테이블을 파싱한다. 표준 라이브러리 html.parser 만 사용.

테이블 컬럼 (2026-07 기준 실제 응답 구조):
  0 회사명(+시장구분 아이콘 alt)  1 신고서제출일  2 수요예측일정
  3 청약일정(범위)               4 납입일       5 확정공모가
  6 공모금액(백만원)             7 상장예정일    8 상장주선인/지정자문인
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
DETAIL_RE = re.compile(r"fnDetailView\('(\d+)'\)")

# KIND 시장구분 아이콘 alt 텍스트 → 스키마 market 값
MARKET_ALT_MAP = (
    ("유가", "KOSPI"),
    ("코스닥", "KOSDAQ"),
    ("코넥스", "KONEX"),
)


class KindIpoTableParser(HTMLParser):
    """공모진행현황 목록 테이블에서 행 단위 원시 데이터를 추출한다."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._in_row = False
        self._in_cell = False
        self._cells = []
        self._cell_parts = []
        self._market_alt = None
        self._acptno = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            match = DETAIL_RE.search(attrs.get("onclick") or "")
            if match:
                self._in_row = True
                self._cells = []
                self._market_alt = None
                self._acptno = match.group(1)
            return
        if not self._in_row:
            return
        if tag == "td":
            self._in_cell = True
            self._cell_parts = []
        elif tag == "img" and "icn_t_" in (attrs.get("src") or ""):
            self._market_alt = attrs.get("alt")
        elif tag == "br" and self._in_cell:
            self._cell_parts.append(" ")

    def handle_data(self, data):
        if self._in_row and self._in_cell:
            self._cell_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self._in_cell:
            text = "".join(self._cell_parts).replace("\xa0", " ")
            self._cells.append(" ".join(text.split()))
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            self._in_row = False
            if self._cells:
                self.rows.append({
                    "cells": self._cells,
                    "market_alt": self._market_alt,
                    "acptno": self._acptno,
                })


def parse_rows(html: str) -> list:
    """응답 HTML → 원시 행 리스트."""
    parser = KindIpoTableParser()
    parser.feed(html)
    return parser.rows


def _parse_date_range(text: str):
    dates = DATE_RE.findall(text or "")
    if len(dates) >= 2:
        return dates[0], dates[1]
    if len(dates) == 1:
        return dates[0], dates[0]
    return None, None


def _parse_single_date(text: str):
    match = DATE_RE.search(text or "")
    return match.group(0) if match else None


def _parse_price(text: str):
    digits = (text or "").replace(",", "").strip()
    return int(digits) if digits.isdigit() else None


def _parse_market(alt):
    if not alt:
        return None
    for keyword, market in MARKET_ALT_MAP:
        if keyword in alt:
            return market
    return None


def _parse_underwriters(text: str) -> list:
    return [part.strip() for part in (text or "").split(",") if part.strip()]


def to_ipo_items(rows: list) -> list:
    """원시 행 → ipo.json 아이템 리스트. 청약일정이 없는 행은 건너뛴다."""
    items = []
    for row in rows:
        cells = row.get("cells") or []
        if len(cells) < 9:
            continue
        name = cells[0].strip()
        sub_start, sub_end = _parse_date_range(cells[3])
        if not name or not sub_start or not sub_end:
            continue
        items.append({
            "name": name,
            "code": None,
            "subStart": sub_start,
            "subEnd": sub_end,
            "listDate": _parse_single_date(cells[7]),
            "priceBandLow": None,
            "priceBandHigh": None,
            "finalPrice": _parse_price(cells[5]),
            "underwriters": _parse_underwriters(cells[8]),
            "market": _parse_market(row.get("market_alt")),
        })
    items.sort(key=lambda it: (it["subStart"], it["name"]))
    return items
