// 계산기 페이지 바인딩
import { subscriptionMargin, dividendYield, requiredInvestment, fmtKRW } from './calc.js';

// 테마 (app.js와 동일 로직 최소화)
const prefs = JSON.parse(localStorage.getItem('stockcal_prefs') || '{}');
if (!prefs.theme) prefs.theme = window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
document.documentElement.dataset.theme = prefs.theme;
const $theme = document.getElementById('btn-theme');
$theme.textContent = prefs.theme === 'dark' ? '☀' : '☾';
$theme.addEventListener('click', () => {
  prefs.theme = prefs.theme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('stockcal_prefs', JSON.stringify(prefs));
  document.documentElement.dataset.theme = prefs.theme;
  $theme.textContent = prefs.theme === 'dark' ? '☀' : '☾';
});

const $ = (id) => document.getElementById(id);
const num = (id) => parseFloat($(id).value) || 0;

function bind(ids, fn) {
  ids.forEach((id) => $(id).addEventListener('input', fn));
  fn();
}

// 증거금
bind(['m-price', 'm-qty', 'm-rate'], () => {
  const r = subscriptionMargin({ price: num('m-price'), qty: num('m-qty'), marginRate: num('m-rate') });
  $('m-result').querySelector('.result-value').textContent = r ? fmtKRW(r.deposit) : '-';
  $('m-note').textContent = r && num('m-qty') === 10
    ? '균등배정 최소 단위(10주) 기준 증거금이에요.'
    : '';
});

// 배당 수익률
bind(['y-price', 'y-div'], () => {
  const y = dividendYield({ price: num('y-price'), annualDividend: num('y-div') });
  const $v = $('y-result').querySelector('.result-value');
  if (y == null) { $v.textContent = '-'; $('y-note').textContent = ''; return; }
  $v.textContent = `${y.toFixed(2)}%`;
  $('y-note').textContent = `세후(15.4%) 기준 약 ${(y * 0.846).toFixed(2)}%`;
});

// 필요 투자금
bind(['g-goal', 'g-yield'], () => {
  const v = requiredInvestment({ monthlyGoal: num('g-goal'), yieldPct: num('g-yield') });
  $('g-result').querySelector('.result-value').textContent = v ? fmtKRW(v) : '-';
});
