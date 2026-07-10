# -*- coding: utf-8 -*-
"""주식달력 데이터 스키마 검증.

단독 실행: python scripts/validate.py  →  실패 시 exit 1
다른 모듈에서 import 하여 개별 아이템 검증에도 사용한다.
표준 라이브러리만 사용.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MARKETS = {"KOSPI", "KOSDAQ", "KONEX"}

IPO_FIELDS = (
    "name", "code", "subStart", "subEnd", "listDate",
    "priceBandLow", "priceBandHigh", "finalPrice", "underwriters", "market",
)
DIVIDEND_FIELDS = ("name", "code", "exDate", "payDate", "amount", "market")


def _is_date(value) -> bool:
    return isinstance(value, str) and bool(DATE_RE.match(value))


def _check_opt_str(item: dict, key: str, errors: list) -> None:
    value = item.get(key)
    if value is not None and not isinstance(value, str):
        errors.append(f"{key}: str 또는 null 이어야 함 (got {type(value).__name__})")


def _check_opt_int(item: dict, key: str, errors: list) -> None:
    value = item.get(key)
    if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
        errors.append(f"{key}: int 또는 null 이어야 함 (got {type(value).__name__})")


def _check_opt_date(item: dict, key: str, errors: list) -> None:
    value = item.get(key)
    if value is not None and not _is_date(value):
        errors.append(f"{key}: YYYY-MM-DD 또는 null 이어야 함 (got {value!r})")


def validate_ipo_item(item) -> list:
    """공모주 아이템 검증. 에러 메시지 리스트 반환(빈 리스트 = 통과)."""
    errors = []
    if not isinstance(item, dict):
        return ["아이템이 객체가 아님"]
    for key in IPO_FIELDS:
        if key not in item:
            errors.append(f"필수 필드 누락: {key}")
    if errors:
        return errors

    if not isinstance(item["name"], str) or not item["name"].strip():
        errors.append("name: 비어있지 않은 str 이어야 함")
    _check_opt_str(item, "code", errors)
    for key in ("subStart", "subEnd"):
        if not _is_date(item[key]):
            errors.append(f"{key}: YYYY-MM-DD 형식이어야 함 (got {item[key]!r})")
    if _is_date(item["subStart"]) and _is_date(item["subEnd"]) \
            and item["subStart"] > item["subEnd"]:
        errors.append("subStart 가 subEnd 보다 이후일 수 없음")
    _check_opt_date(item, "listDate", errors)
    _check_opt_int(item, "priceBandLow", errors)
    _check_opt_int(item, "priceBandHigh", errors)
    _check_opt_int(item, "finalPrice", errors)
    low, high = item.get("priceBandLow"), item.get("priceBandHigh")
    if isinstance(low, int) and isinstance(high, int) and low > high:
        errors.append("priceBandLow 가 priceBandHigh 보다 클 수 없음")
    uw = item.get("underwriters")
    if not isinstance(uw, list) or not all(isinstance(u, str) for u in uw):
        errors.append("underwriters: str 리스트여야 함")
    if item.get("market") is not None and item["market"] not in MARKETS:
        errors.append(f"market: {sorted(MARKETS)} 또는 null 이어야 함 (got {item['market']!r})")
    return errors


def validate_dividend_item(item) -> list:
    """배당 아이템 검증. 에러 메시지 리스트 반환(빈 리스트 = 통과)."""
    errors = []
    if not isinstance(item, dict):
        return ["아이템이 객체가 아님"]
    for key in DIVIDEND_FIELDS:
        if key not in item:
            errors.append(f"필수 필드 누락: {key}")
    if errors:
        return errors

    if not isinstance(item["name"], str) or not item["name"].strip():
        errors.append("name: 비어있지 않은 str 이어야 함")
    _check_opt_str(item, "code", errors)
    if not _is_date(item["exDate"]):
        errors.append(f"exDate: YYYY-MM-DD 형식이어야 함 (got {item['exDate']!r})")
    _check_opt_date(item, "payDate", errors)
    _check_opt_int(item, "amount", errors)
    if isinstance(item.get("amount"), int) and item["amount"] < 0:
        errors.append("amount: 음수일 수 없음")
    _check_opt_str(item, "market", errors)
    return errors


def _validate_payload(payload, item_validator) -> list:
    errors = []
    if not isinstance(payload, dict):
        return ["최상위가 객체가 아님"]
    if "updated" not in payload or "source" not in payload or "items" not in payload:
        errors.append("updated/source/items 필드 필요")
        return errors
    if payload["updated"] is not None and not isinstance(payload["updated"], str):
        errors.append("updated: str 또는 null 이어야 함")
    if not isinstance(payload["source"], str):
        errors.append("source: str 이어야 함")
    if not isinstance(payload["items"], list):
        errors.append("items: 리스트여야 함")
        return errors
    for i, item in enumerate(payload["items"]):
        for msg in item_validator(item):
            errors.append(f"items[{i}]: {msg}")
    return errors


def validate_ipo_payload(payload) -> list:
    return _validate_payload(payload, validate_ipo_item)


def validate_dividend_payload(payload) -> list:
    return _validate_payload(payload, validate_dividend_item)


def _validate_file(path: Path, validator) -> list:
    if not path.exists():
        return [f"파일 없음: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"JSON 로드 실패: {exc}"]
    return validator(payload)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    targets = [
        (root / "data" / "ipo.json", validate_ipo_payload),
        (root / "data" / "dividend.json", validate_dividend_payload),
    ]
    failed = False
    for path, validator in targets:
        errors = _validate_file(path, validator)
        if errors:
            failed = True
            for msg in errors:
                print(f"[FAIL] {path.name}: {msg}", file=sys.stderr)
        else:
            print(f"[OK] {path.name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
