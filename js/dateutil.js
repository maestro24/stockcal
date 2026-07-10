// KST 날짜 유틸 — 순수 함수 (테스트 대상)

/** 현재 KST 기준 YYYY-MM-DD */
export function todayKST(now = Date.now()) {
  return new Date(now + 9 * 3600000).toISOString().slice(0, 10);
}

/** YYYY-MM-DD 문자열 비교용 파싱 없이 사전순 비교 가능 (ISO 형식 보장 전제) */
export function cmpDate(a, b) {
  return a < b ? -1 : a > b ? 1 : 0;
}

/** date가 [start, end] 안인지 (경계 포함) */
export function isBetween(date, start, end) {
  return start <= date && date <= end;
}

/** 이번 주 [월요일, 일요일] (KST) */
export function weekRangeKST(now = Date.now()) {
  const d = new Date(now + 9 * 3600000);
  const dow = (d.getUTCDay() + 6) % 7; // 월=0
  const mon = new Date(d);
  mon.setUTCDate(d.getUTCDate() - dow);
  const sun = new Date(mon);
  sun.setUTCDate(mon.getUTCDate() + 6);
  return [mon.toISOString().slice(0, 10), sun.toISOString().slice(0, 10)];
}

/** YYYY-MM (KST) */
export function monthKST(now = Date.now()) {
  return todayKST(now).slice(0, 7);
}

/** 해당 월의 달력 그리드용 날짜 배열: 앞뒤 패딩 포함, 월요일 시작 */
export function monthGrid(yyyymm) {
  const [y, m] = yyyymm.split('-').map(Number);
  const first = new Date(Date.UTC(y, m - 1, 1));
  const daysInMonth = new Date(Date.UTC(y, m, 0)).getUTCDate();
  const lead = (first.getUTCDay() + 6) % 7; // 월=0
  const cells = [];
  for (let i = 0; i < lead; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push(`${yyyymm}-${String(d).padStart(2, '0')}`);
  }
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

/** 월 이동: yyyymm + delta개월 */
export function shiftMonth(yyyymm, delta) {
  const [y, m] = yyyymm.split('-').map(Number);
  const d = new Date(Date.UTC(y, m - 1 + delta, 1));
  return d.toISOString().slice(0, 7);
}

/** D-day 라벨: 오늘=D-Day, 미래=D-n, 과거=null */
export function dday(date, today) {
  const diff = Math.round((Date.parse(date) - Date.parse(today)) / 86400000);
  if (diff < 0) return null;
  return diff === 0 ? 'D-Day' : `D-${diff}`;
}

/** 공모주 상태 분류 */
export function ipoStatus(item, today) {
  if (isBetween(today, item.subStart, item.subEnd)) return 'open';      // 청약 중
  if (today < item.subStart) return 'upcoming';                          // 예정
  if (item.listDate && today <= item.listDate) return 'waiting';         // 상장 대기
  return 'done';                                                         // 종료
}
