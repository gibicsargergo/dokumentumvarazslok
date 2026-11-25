import { useEffect, useState } from 'react';
import SearchStatsCard from '../components/SearchStatsCard';
import ToggleSwitch, { type Option } from '../components/ToggleSwitch';
import { getSearchStats } from '../lib/api';
import type { SearchStatsResponse, StatsPeriod } from '../lib/searchStats';

const PERIODS: Option[] = [
  { value: 'monthly', label: 'Monthly' },
  { value: 'allTime', label: 'All time' },
];

export default function SearchStatsPage() {
  const [period, setPeriod] = useState<StatsPeriod>('monthly');
  const [stats, setStats] = useState<SearchStatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getSearchStats()
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Search statistics</h1>
          <p className="mt-1 text-subtle">The most searched documents and categories.</p>
        </div>
        <ToggleSwitch
          value={period}
          options={PERIODS}
          onChange={(value) => setPeriod(value === 'allTime' ? 'allTime' : 'monthly')}
        />
      </header>
      {error ? (
        <p className="text-subtle">Could not load statistics: {error}</p>
      ) : !stats ? (
        <p className="text-muted">Loading statistics…</p>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <SearchStatsCard title="Most searched documents" stats={stats.documents} period={period} />
          <SearchStatsCard title="Most searched categories" stats={stats.categories} period={period} />
        </div>
      )}
    </div>
  );
}
