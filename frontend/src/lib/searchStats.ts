export type SearchStat = {
  id: string;
  label: string;
  monthly: number[];
};

export type SearchStats = {
  months: string[];
  items: SearchStat[];
};

// GET /admin/stats
export type SearchStatsResponse = {
  documents: SearchStats;
  categories: SearchStats;
};

export type StatsPeriod = 'monthly' | 'allTime';

export const OTHERS_ID = 'others';

const RECENT_MONTHS = 12;

export function statsForPeriod(stats: SearchStats, period: StatsPeriod, top = 5): SearchStats {
  const start = period === 'monthly' ? Math.max(0, stats.months.length - RECENT_MONTHS) : 0;
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
