import LineChart from './LineChart';
import RankedList from './RankedList';
import { seriesColor } from './seriesColors';
import { statsForPeriod, type SearchStats, type StatsPeriod } from '../lib/searchStats';

interface SearchStatsCardProps  {
  title: string;
  stats: SearchStats;
  period: StatsPeriod;
};

export default function SearchStatsCard({ title, stats, period }: Readonly<SearchStatsCardProps>) {
  const { months, items } = statsForPeriod(stats, period);

  const series = items.map((item, i) => ({
    id: item.id,
    label: item.label,
    color: seriesColor(item.id, i),
    values: item.monthly,
  }));

  const ranked = series.map((s) => ({
    id: s.id,
    label: s.label,
    color: s.color,
    value: period === 'monthly' ? s.values[s.values.length - 1] : s.values.reduce((a, b) => a + b, 0),
  }));

  return (
    <section className="flex flex-col gap-4 rounded-xl border border-line bg-surface p-5">
      <header>
        <h2 className="text-lg font-semibold text-ink">{title}</h2>
        <p className="text-sm text-subtle">
          {period === 'monthly' ? 'Searches this month' : 'Searches since tracking began'}
        </p>
      </header>
      <RankedList items={ranked} />
      <LineChart labels={months} series={series} />
    </section>
  );
}
