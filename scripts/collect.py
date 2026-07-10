# -*- coding: utf-8 -*-
"""주식달력 데이터 수집기 (GitHub Actions 크론에서 실행).

원칙:
- 어떤 소스든 실패(네트워크/파싱/스키마) 시 기존 data/*.json 유지, stderr 로그, exit 0
- 수집 결과가 기존 items 와 동일하면 파일을 쓰지 않는다 (불필요 커밋 방지)
- DART 는 환경변수 DART_API_KEY 가 있을 때만 시도
- 표준 라이브러리만 사용
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dart_client  # noqa: E402
import kind_parser  # noqa: E402
import validate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
IPO_PATH = DATA_DIR / "ipo.json"
DIVIDEND_PATH = DATA_DIR / "dividend.json"

KIND_URL = "https://kind.krx.co.kr/listinvstg/pubofrprogcom.do"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TIMEOUT = 30
KST = timezone(timedelta(hours=9))


class CollectError(Exception):
    """수집/파싱 단계에서의 예상 가능한 실패."""


def log(message: str) -> None:
    print(f"[collect] {message}", file=sys.stderr)


def fetch_url(url: str, data: dict | None = None) -> bytes:
    """urllib 기반 HTTP 요청. data 가 있으면 POST 폼 요청."""
    headers = {"User-Agent": USER_AGENT}
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["X-Requested-With"] = "XMLHttpRequest"
        headers["Referer"] = f"{KIND_URL}?method=searchPubofrProgComMain"
    request = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def fetch_kind_ipo_html() -> str:
    """KIND 공모진행현황 목록(AJAX sub) HTML 조회."""
    payload = {
        "method": "searchPubofrProgComSub",
        "currentPageSize": "100",
        "pageIndex": "1",
        "orderMode": "1",
        "orderStat": "D",
        "searchCodeType": "",
        "searchCorpName": "",
        "repIsuSrtCd": "",
    }
    return fetch_url(KIND_URL, data=payload).decode("utf-8", errors="replace")


def collect_ipo_items(fetch_html=None) -> list:
    """KIND 에서 공모주 아이템 수집. 스키마 검증 통과분만 반환."""
    html = (fetch_html or fetch_kind_ipo_html)()
    rows = kind_parser.parse_rows(html)
    if not rows:
        raise CollectError("KIND 응답에서 테이블 행을 찾지 못함 (구조 변경 또는 차단 가능성)")
    items = kind_parser.to_ipo_items(rows)
    valid = [item for item in items if not validate.validate_ipo_item(item)]
    if not valid:
        raise CollectError(f"행 {len(rows)}건 파싱했지만 유효 아이템 0건 (구조 변경 가능성)")
    dropped = len(items) - len(valid)
    if dropped:
        log(f"스키마 검증 실패로 {dropped}건 제외")
    return valid


def collect_dividend_items(api_key: str, fetch=None) -> list:
    """DART 에서 배당 아이템 수집. 스키마 검증 통과분만 반환."""
    items = dart_client.collect_dividend_items(api_key, fetch or fetch_url)
    return [item for item in items if not validate.validate_dividend_item(item)]


def load_payload(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def kst_now_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def update_json_file(path: Path, source: str, items: list, payload_validator) -> bool:
    """검증 통과 시에만 원자적으로 파일 갱신. 변경 없으면 False."""
    existing = load_payload(path)
    if existing is not None and existing.get("items") == items:
        return False
    payload = {"updated": kst_now_iso(), "source": source, "items": items}
    errors = payload_validator(payload)
    if errors:
        raise CollectError(f"쓰기 전 스키마 검증 실패: {errors[:3]}")
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)
    return True


def run() -> int:
    """모든 소스를 수집. 개별 실패는 격리하고 항상 0을 반환한다."""
    # --- 공모주 (KIND) ---
    try:
        items = collect_ipo_items()
        changed = update_json_file(
            IPO_PATH, "KRX KIND / DART", items, validate.validate_ipo_payload)
        log(f"ipo.json: {len(items)}건 수집, {'갱신됨' if changed else '변경 없음'}")
    except Exception as exc:  # noqa: BLE001 - 어떤 실패든 기존 파일 유지
        log(f"ipo 수집 실패, 기존 파일 유지: {type(exc).__name__}: {exc}")

    # --- 배당 (DART) ---
    api_key = os.environ.get("DART_API_KEY", "").strip()
    if not api_key:
        log("DART_API_KEY 없음 → 배당 수집 스킵 (기존 dividend.json 유지)")
        return 0
    try:
        items = collect_dividend_items(api_key)
        if not items:
            log("DART 수집 결과 0건 → 기존 dividend.json 유지")
            return 0
        changed = update_json_file(
            DIVIDEND_PATH, "DART", items, validate.validate_dividend_payload)
        log(f"dividend.json: {len(items)}건 수집, {'갱신됨' if changed else '변경 없음'}")
    except Exception as exc:  # noqa: BLE001
        log(f"dividend 수집 실패, 기존 파일 유지: {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
