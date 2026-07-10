# 주식달력 (StockCal) — 공모주 · 배당 캘린더

이번 주 공모주 청약과 배당락일을 한눈에. GitHub Actions가 매일 공시 데이터를 수집해 정적 JSON으로 굽는 **서버리스 데이터 사이트**.

**운영 URL**: https://maestro24.github.io/stockcal/

## 아키텍처

```
[GitHub Actions cron 06:30 KST]
  → scripts/collect.py   (KRX KIND·DART 수집, 실패 시 기존 데이터 유지)
  → scripts/validate.py  (스키마 검증, 실패 시 커밋 차단)
  → data/*.json 커밋     (변경 시에만)
  → GitHub Pages 자동 재배포
[정적 프론트]
  → index.html + js/app.js 가 data/*.json 렌더 (프레임워크 0)
```

## 실행 & 테스트

```bash
python -m http.server 8000          # 로컬 실행
# http://localhost:8000?demo=1      # 예시 데이터로 UI 확인

node tests/frontend.test.mjs        # 프론트 로직 (날짜·계산기)
python -m unittest discover tests   # 수집기·검증기
python scripts/validate.py          # 데이터 스키마 검증
```

## 데이터 갱신

- 자동: `.github/workflows/update-data.yml` — 매일 06:30 KST + 수동 트리거
- DART 수집 활성화: 저장소 Settings → Secrets → `DART_API_KEY` 추가 (https://opendart.fss.or.kr 무료 발급)
- 키 없으면 KIND만 수집, 그것도 실패하면 기존 데이터 유지 (사이트는 절대 안 깨짐)

## 구조

```
index.html        대시보드 (이번주 요약 + 월간 캘린더 + 리스트)
calc.html         계산기 3종 (증거금·배당수익률·필요투자금)
js/dateutil.js    KST 날짜 유틸 (순수 함수)
js/calc.js        계산 로직 (순수 함수)
js/app.js         대시보드 렌더
data/*.json       소스 오브 트루스 (Actions가 갱신)
scripts/          수집·검증 (Python stdlib only)
docs/PLAN.md      기획서
```

## 원칙

1. 절대 깨지지 않는 사이트 — 수집 실패 시 이전 데이터 유지, 빈 데이터면 "준비 중" 표시
2. 가짜 데이터 금지 — 예시는 `?demo=1` + "(예시)" 라벨에서만
3. 공공 데이터만 — KIND/DART. 면책 고지 + 출처 상시 표기
