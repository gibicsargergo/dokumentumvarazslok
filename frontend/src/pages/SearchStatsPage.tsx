import { useState } from 'react';
import SearchStatsCard from '../components/SearchStatsCard';
import ToggleSwitch, { type Option } from '../components/ToggleSwitch';
import { categorySearchStats, documentSearchStats, type StatsPeriod } from '../lib/searchStatsStub';

const PERIODS: Option[] = [
  { value: 'monthly', label: 'Monthly' },
  { value: 'allTime', label: 'All time' },
];

export default function SearchStatsPage() {
  const [period, setPeriod] = useState<StatsPeriod>('monthly');

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
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SearchStatsCard title="Most searched documents" stats={documentSearchStats} period={period} />
        <SearchStatsCard title="Most searched categories" stats={categorySearchStats} period={period} />
      </div>
    </div>
  );
}
