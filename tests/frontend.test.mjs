// 프론트 순수 로직 테스트 — node tests/frontend.test.mjs
import { strict as assert } from 'node:assert';
import {
  todayKST, isBetween, weekRangeKST, monthGrid, shiftMonth, dday, ipoStatus, cmpDate,
} from '../js/dateutil.js';
import {
  subscriptionMargin, minEqualMargin, dividendYield, requiredInvestment, fmtKRW,
} from '../js/calc.js';

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log(`  ok - ${name}`); }
  catch (e) { failed++; console.error(`  FAIL - ${name}\n    ${e.message}`); }
}

console.log('# dateutil');
test('todayKST: UTC 15:00 = KST 자정 경계', () => {
  // 2026-07-10 15:00 UTC = 2026-07-11 00:00 KST
  assert.equal(todayKST(Date.UTC(2026, 6, 10, 15, 0, 0)), '2026-07-11');
  assert.equal(todayKST(Date.UTC(2026, 6, 10, 14, 59, 59)), '2026-07-10');
});
test('isBetween 경계 포함', () => {
  assert.equal(isBetween('2026-07-10', '2026-07-10', '2026-07-11'), true);
  assert.equal(isBetween('2026-07-12', '2026-07-10', '2026-07-11'), false);
});
test('weekRangeKST: 금요일 → 월~일', () => {
  // 2026-07-10은 금요일
  const [mon, sun] = weekRangeKST(Date.UTC(2026, 6, 10, 3, 0, 0));
  assert.equal(mon, '2026-07-06');
  assert.equal(sun, '2026-07-12');
});
test('monthGrid: 2026-07은 수요일 시작(lead 2), 31일', () => {
  const g = monthGrid('2026-07');
  assert.equal(g[0], null); // 월
  assert.equal(g[1], null); // 화
  assert.equal(g[2], '2026-07-01'); // 수
  assert.equal(g.filter(Boolean).length, 31);
  assert.equal(g.length % 7, 0);
});
test('shiftMonth 연도 넘김', () => {
  assert.equal(shiftMonth('2026-12', 1), '2027-01');
  assert.equal(shiftMonth('2026-01', -1), '2025-12');
});
test('dday', () => {
  assert.equal(dday('2026-07-10', '2026-07-10'), 'D-Day');
  assert.equal(dday('2026-07-13', '2026-07-10'), 'D-3');
  assert.equal(dday('2026-07-09', '2026-07-10'), null);
});
test('ipoStatus 분류', () => {
  const item = { subStart: '2026-07-08', subEnd: '2026-07-09', listDate: '2026-07-17' };
  assert.equal(ipoStatus(item, '2026-07-08'), 'open');
  assert.equal(ipoStatus(item, '2026-07-07'), 'upcoming');
  assert.equal(ipoStatus(item, '2026-07-12'), 'waiting');
  assert.equal(ipoStatus(item, '2026-07-18'), 'done');
  assert.equal(ipoStatus({ subStart: '2026-07-01', subEnd: '2026-07-02', listDate: null }, '2026-07-05'), 'done');
});
test('cmpDate', () => {
  assert.equal(cmpDate('2026-07-01', '2026-07-02'), -1);
  assert.equal(cmpDate('2026-07-02', '2026-07-02'), 0);
});

console.log('# calc');
test('증거금: 공모가 30,000 × 10주 × 50% = 150,000', () => {
  assert.deepEqual(subscriptionMargin({ price: 30000, qty: 10 }), { deposit: 150000 });
});
test('증거금률 100%', () => {
  assert.deepEqual(subscriptionMargin({ price: 20000, qty: 5, marginRate: 100 }), { deposit: 100000 });
});
test('균등 최소 증거금 기본값', () => {
  assert.deepEqual(minEqualMargin({ price: 25000 }), { deposit: 125000 });
});
test('잘못된 입력 → null', () => {
  assert.equal(subscriptionMargin({ price: -1, qty: 10 }), null);
  assert.equal(subscriptionMargin({ price: 1000, qty: 0 }), null);
});
test('배당수익률: 70,000원 주가, 연 3,500원 → 5%', () => {
  assert.equal(dividendYield({ price: 70000, annualDividend: 3500 }), 5);
});
test('필요 투자금: 월 100만, 수익률 5%, 세율 15.4%', () => {
  const v = requiredInvestment({ monthlyGoal: 1000000, yieldPct: 5 });
  // 연 1200만 세후 → 세전 1200/(1-0.154)=1418.44만 → /5% = 2.837억
  assert.ok(v > 283000000 && v < 284000000, String(v));
});
test('fmtKRW', () => {
  assert.equal(fmtKRW(150000), '150,000원');
  assert.equal(fmtKRW(300000000), '3억 원');
  assert.equal(fmtKRW(null), '-');
});

console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
