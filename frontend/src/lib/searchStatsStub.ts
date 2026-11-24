export type SearchStat = {
  id: string;
  label: string;
  monthly: number[];
};

export type SearchStats = {
  months: string[];
  items: SearchStat[];
};

export type StatsPeriod = 'monthly' | 'allTime';

export const OTHERS_ID = 'others';

const MONTH_COUNT = 24;
const RECENT_MONTHS = 12;

const MONTHS = Array.from({ length: MONTH_COUNT }, (_, i) => {
  const d = new Date(2024, 11 + i, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
});

function series(base: number, growth: number, phase: number): number[] {
  return MONTHS.map((_, i) =>
    Math.max(0, Math.round(base * (1 + growth * i) * (1 + 0.2 * Math.sin(i / 1.9 + phase)))),
  );
}

export const documentSearchStats: SearchStats = {
  months: MONTHS,
  items: [
    { id: 'doc-1', label: 'Employee Handbook 2026', monthly: series(320, 0.02, 0) },
    { id: 'doc-2', label: 'Remote Work Policy', monthly: series(290, -0.01, 1) },
    { id: 'doc-3', label: 'Expense Reimbursement Guide', monthly: series(210, 0.01, 2) },
    { id: 'doc-4', label: 'IT Security Guidelines', monthly: series(60, 0.2, 3) },
    { id: 'doc-5', label: 'Onboarding Checklist', monthly: series(150, 0.005, 4) },
    { id: 'doc-6', label: 'Q3 Financial Report', monthly: series(130, 0.01, 5) },
    { id: 'doc-7', label: 'Office Floor Plan', monthly: series(60, 0, 0.5) },
    { id: 'doc-8', label: 'Travel Policy', monthly: series(80, -0.02, 1.5) },
    { id: 'doc-9', label: 'Brand Style Guide', monthly: series(45, 0.01, 2.5) },
    { id: 'doc-10', label: 'GDPR Compliance Notes', monthly: series(55, 0.03, 3.5) },
  ],
};

export const categorySearchStats: SearchStats = {
  months: MONTHS,
  items: [
    { id: 'cat-1', label: 'HR', monthly: series(760, 0.02, 0) },
    { id: 'cat-2', label: 'Finance', monthly: series(420, 0.01, 1) },
    { id: 'cat-3', label: 'IT', monthly: series(180, 0.12, 2) },
    { id: 'cat-4', label: 'Legal', monthly: series(230, -0.01, 3) },
    { id: 'cat-5', label: 'Operations', monthly: series(160, 0, 4) },
    { id: 'cat-6', label: 'Marketing', monthly: series(110, 0.04, 5) },
    { id: 'cat-7', label: 'Facilities', monthly: series(80, 0, 0.5) },
    { id: 'cat-8', label: 'Sales', monthly: series(70, 0.02, 1.5) },
  ],
};

export function statsForPeriod(stats: SearchStats, period: StatsPeriod, top = 5): SearchStats {
  const start = period === 'monthly' ? stats.months.length - RECENT_MONTHS : 0;
  const months = stats.months.slice(start);
  const score = (item: SearchStat) =>
    period === 'monthly'
      ? item.monthly[item.monthly.length - 1]
      : item.monthly.reduce((a, b) => a + b, 0);

  const sorted = [...stats.items].sort((a, b) => score(b) - score(a));
  const window = (item: SearchStat) => ({ ...item, monthly: item.monthly.slice(start) });
  const items = sorted.slice(0, top).map(window);
  const rest = sorted.slice(top).map(window);

  if (rest.length > 0) {
    const monthly = months.map((_, i) => rest.reduce((sum, item) => sum + item.monthly[i], 0));
    items.push({ id: OTHERS_ID, label: 'Others', monthly });
  }

  return { months, items };
}
