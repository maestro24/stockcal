// 계산기 순수 함수 (테스트 대상)

/**
 * 청약 증거금 계산
 * @returns { deposit: 필요 증거금, fee: 청약 수수료 제외 }
 */
export function subscriptionMargin({ price, qty, marginRate = 50 }) {
  if (!(price > 0) || !(qty > 0) || !(marginRate > 0)) return null;
  const deposit = Math.ceil(price * qty * (marginRate / 100));
  return { deposit };
}

/** 균등배정 최소 증거금 (최소 청약 단위 기준, 통상 10주·50%) */
export function minEqualMargin({ price, minQty = 10, marginRate = 50 }) {
  return subscriptionMargin({ price, qty: minQty, marginRate });
}

/**
 * 배당 수익률: 연 배당금 / 현재가
 */
export function dividendYield({ price, annualDividend }) {
  if (!(price > 0) || !(annualDividend >= 0)) return null;
  return (annualDividend / price) * 100;
}

/**
 * 목표 월 배당금 달성에 필요한 투자금
 * @param monthlyGoal 목표 월 배당(원), yieldPct 연 수익률(%)
 */
export function requiredInvestment({ monthlyGoal, yieldPct, taxRate = 15.4 }) {
  if (!(monthlyGoal > 0) || !(yieldPct > 0)) return null;
  const annualNet = monthlyGoal * 12;
  const annualGross = annualNet / (1 - taxRate / 100);
  return Math.ceil(annualGross / (yieldPct / 100));
}

/** 원화 표기 */
export function fmtKRW(n) {
  if (n == null || Number.isNaN(n)) return '-';
  if (n >= 100000000) {
    const eok = n / 100000000;
    return `${eok % 1 === 0 ? eok : eok.toFixed(2)}억 원`;
  }
  return `${n.toLocaleString('ko-KR')}원`;
}
