// 주식달력 메인 — 데이터 로드, 대시보드, 캘린더/리스트 렌더
import {
  todayKST, weekRangeKST, monthKST, monthGrid, shiftMonth, dday, ipoStatus, isBetween, cmpDate,
} from './dateutil.js';

const DOW = ['월', '화', '수', '목', '금', '토', '일'];
const today = todayKST();
let viewMonth = monthKST();
let ipoData = { updated: null, items: [] };
let divData = { updated: null, items: [] };

// ── 테마 ──
const prefs = JSON.parse(localStorage.getItem('stockcal_prefs') || '{}');
if (!prefs.theme) prefs.theme = window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
applyTheme();
function applyTheme() {
  document.documentElement.dataset.theme = prefs.theme;
  const btn = document.getElementById('btn-theme');
  if (btn) btn.textContent = prefs.theme === 'dark' ? '☀' : '☾';
}
document.getElementById('btn-theme')?.addEventListener('click', () => {
  prefs.theme = prefs.theme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('stockcal_prefs', JSON.stringify(prefs));
  applyTheme();
});

// ── 데이터 로드 (실패해도 앱은 뜬다) ──
async function loadJSON(path, fallback) {
  try {
    const res = await fetch(path, { cache: 'no-cache' });
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    return Array.isArray(data.items) ? data : fallback;
  } catch {
    return fallback;
  }
}

// ── 이번 주 요약 ──
function renderWeekSummary() {
  const [mon, sun] = weekRangeKST();
  const $ipo = document.getElementById('week-ipo');
  const $div = document.getElementById('week-div');

  const ipoWeek = ipoData.items
    .filter((it) => it.subStart <= sun && it.subEnd >= mon)
    .sort((a, b) => cmpDate(a.subStart, b.subStart));
  const listWeek = ipoData.items
    .filter((it) => it.listDate && isBetween(it.listDate, mon, sun));
  const divWeek = divData.items
    .filter((it) => isBetween(it.exDate, mon, sun))
    .sort((a, b) => cmpDate(a.exDate, b.exDate));

  $ipo.innerHTML = '';
  if (ipoWeek.length === 0 && listWeek.length === 0) {
    $ipo.innerHTML = `<div class="empty">${ipoData.updated ? '이번 주 청약 일정이 없어요' : '데이터 준비 중이에요 — 자동 수집이 시작되면 표시됩니다'}</div>`;
  } else {
    for (const it of ipoWeek) $ipo.appendChild(eventRow(it.name, `${fmtMD(it.subStart)}~${fmtMD(it.subEnd)}`, ipoBadge(it)));
    for (const it of listWeek) $ipo.appendChild(eventRow(it.name, fmtMD(it.listDate), { cls: 'badge-list', label: '상장' }));
  }

  $div.innerHTML = '';
  if (divWeek.length === 0) {
    $div.innerHTML = `<div class="empty">${divData.updated ? '이번 주 배당락 일정이 없어요' : '데이터 준비 중이에요 — 자동 수집이 시작되면 표시됩니다'}</div>`;
  } else {
    for (const it of divWeek) $div.appendChild(eventRow(it.name, fmtMD(it.exDate), { cls: 'badge-div', label: '배당락' }));
  }

  setUpdated('ipo-updated', ipoData.updated);
  setUpdated('div-updated', divData.updated);
}

function ipoBadge(it) {
  const st = ipoStatus(it, today);
  if (st === 'open') return { cls: 'badge-open', label: '청약 중' };
  if (st === 'upcoming') {
    const d = dday(it.subStart, today);
    return d === 'D-Day' || d === 'D-1' || d === 'D-2'
      ? { cls: 'badge-dday', label: d }
      : { cls: 'badge-upcoming', label: '예정' };
  }
  if (st === 'waiting') return { cls: 'badge-list', label: '상장 대기' };
  return { cls: 'badge-done', label: '종료' };
}

function eventRow(name, date, badge) {
  const row = document.createElement('div');
  row.className = 'event-row';
  row.innerHTML = `<span class="badge ${badge.cls}">${badge.label}</span><span class="name"></span><span class="date">${date}</span>`;
  row.querySelector('.name').textContent = name;
  return row;
}

function setUpdated(id, ts) {
  const el = document.getElementById(id);
  if (el && ts) el.textContent = `${ts.slice(5, 10).replace('-', '/')} 갱신`;
}

function fmtMD(d) { return d ? `${Number(d.slice(5, 7))}/${Number(d.slice(8, 10))}` : '-'; }

// ── 캘린더 ──
function eventsOn(date) {
  const ev = [];
  for (const it of ipoData.items) {
    if (isBetween(date, it.subStart, it.subEnd)) ev.push({ type: 'open', name: it.name });
    if (it.listDate === date) ev.push({ type: 'list', name: it.name });
  }
  for (const it of divData.items) {
    if (it.exDate === date) ev.push({ type: 'div', name: it.name });
  }
  return ev;
}

function renderCalendar() {
  const $cal = document.getElementById('view-cal');
  const [y, m] = viewMonth.split('-');
  document.getElementById('cal-title').textContent = `${y}년 ${Number(m)}월`;
  $cal.innerHTML = '';
  for (const d of DOW) {
    const el = document.createElement('div');
    el.className = 'cal-dow';
    el.textContent = d;
    $cal.appendChild(el);
  }
  for (const date of monthGrid(viewMonth)) {
    const cell = document.createElement('div');
    if (!date) {
      cell.className = 'cal-cell blank';
    } else {
      const dow = new Date(date + 'T00:00:00Z').getUTCDay();
      cell.className = 'cal-cell'
        + (date === today ? ' today' : '')
        + (dow === 0 || dow === 6 ? ' weekend' : '');
      const dnum = document.createElement('span');
      dnum.className = 'd';
      dnum.textContent = Number(date.slice(8, 10));
      cell.appendChild(dnum);
      const evs = eventsOn(date);
      const shown = evs.slice(0, 2);
      for (const ev of shown) {
        const chip = document.createElement('span');
        chip.className = `chip chip-${ev.type}`;
        chip.textContent = ev.name;
        chip.title = ev.name;
        cell.appendChild(chip);
      }
      if (evs.length > 2) {
        const more = document.createElement('span');
        more.className = 'chip chip-more';
        more.textContent = `+${evs.length - 2}`;
        cell.appendChild(more);
      }
    }
    $cal.appendChild(cell);
  }
}

// ── 리스트 뷰 ──
function renderList() {
  const $list = document.getElementById('view-list');
  $list.innerHTML = '';
  const monthItems = ipoData.items
    .filter((it) => it.subStart.startsWith(viewMonth) || it.subEnd.startsWith(viewMonth) || (it.listDate || '').startsWith(viewMonth))
    .sort((a, b) => cmpDate(a.subStart, b.subStart));
  if (monthItems.length === 0) {
    $list.innerHTML = `<div class="empty">${ipoData.updated ? '이 달에는 공모주 일정이 없어요' : '데이터 준비 중이에요'}</div>`;
    return;
  }
  for (const it of monthItems) {
    const b = ipoBadge(it);
    const el = document.createElement('div');
    el.className = 'ipo-item';
    const band = it.priceBandLow && it.priceBandHigh
      ? `${it.priceBandLow.toLocaleString()}~${it.priceBandHigh.toLocaleString()}원` : null;
    el.innerHTML = `
      <div class="top">
        <span class="badge ${b.cls}">${b.label}</span>
        <span class="name"></span>
        ${it.market ? `<span class="badge badge-upcoming">${it.market}</span>` : ''}
      </div>
      <div class="meta">
        <span>청약 <b>${fmtMD(it.subStart)}~${fmtMD(it.subEnd)}</b></span>
        ${it.listDate ? `<span>상장 <b>${fmtMD(it.listDate)}</b></span>` : ''}
        ${it.finalPrice ? `<span>공모가 <b>${it.finalPrice.toLocaleString()}원</b></span>` : band ? `<span>밴드 <b>${band}</b></span>` : ''}
        ${it.underwriters?.length ? `<span>주관 <b>${it.underwriters.join('·')}</b></span>` : ''}
      </div>`;
    el.querySelector('.name').textContent = it.name;
    $list.appendChild(el);
  }
}

// ── 뷰 전환 & 월 네비 ──
document.getElementById('btn-view-cal').addEventListener('click', () => switchView('cal'));
document.getElementById('btn-view-list').addEventListener('click', () => switchView('list'));
function switchView(v) {
  document.getElementById('view-cal').classList.toggle('hidden', v !== 'cal');
  document.getElementById('view-list').classList.toggle('hidden', v !== 'list');
  document.getElementById('btn-view-cal').classList.toggle('active', v === 'cal');
  document.getElementById('btn-view-list').classList.toggle('active', v === 'list');
}
document.getElementById('btn-prev').addEventListener('click', () => { viewMonth = shiftMonth(viewMonth, -1); renderCalendar(); renderList(); });
document.getElementById('btn-next').addEventListener('click', () => { viewMonth = shiftMonth(viewMonth, 1); renderCalendar(); renderList(); });

// ── 데모 모드 (?demo=1) — 개발·미리보기 전용, 모든 항목에 '예시' 명시 ──
function demoData() {
  const d = (offset) => {
    const t = new Date(Date.parse(today) + offset * 86400000);
    return t.toISOString().slice(0, 10);
  };
  return {
    ipo: {
      updated: new Date().toISOString(), source: '예시 데이터',
      items: [
        { name: '테스트기업A (예시)', code: null, subStart: d(-1), subEnd: d(0), listDate: d(7), priceBandLow: 18000, priceBandHigh: 21000, finalPrice: 21000, underwriters: ['한국증권'], market: 'KOSDAQ' },
        { name: '테스트기업B (예시)', code: null, subStart: d(2), subEnd: d(3), listDate: d(10), priceBandLow: 30000, priceBandHigh: 35000, finalPrice: null, underwriters: ['서울증권', '대한증권'], market: 'KOSPI' },
        { name: '테스트기업C (예시)', code: null, subStart: d(9), subEnd: d(10), listDate: null, priceBandLow: null, priceBandHigh: null, finalPrice: null, underwriters: [], market: 'KOSDAQ' },
      ],
    },
    div: {
      updated: new Date().toISOString(), source: '예시 데이터',
      items: [
        { name: '테스트지주 (예시)', code: null, exDate: d(1), payDate: d(30), amount: 500, market: 'KOSPI' },
        { name: '테스트은행 (예시)', code: null, exDate: d(4), payDate: null, amount: 350, market: 'KOSPI' },
      ],
    },
  };
}

// ── 초기화 ──
(async () => {
  if (new URLSearchParams(location.search).get('demo') === '1') {
    const demo = demoData();
    ipoData = demo.ipo;
    divData = demo.div;
  } else {
    [ipoData, divData] = await Promise.all([
      loadJSON('data/ipo.json', ipoData),
      loadJSON('data/dividend.json', divData),
    ]);
  }
  renderWeekSummary();
  renderCalendar();
  renderList();
})();
