import { OTHERS_ID } from '../lib/searchStats';

const SERIES_COLORS = [
  'var(--color-series-1)',
  'var(--color-series-2)',
  'var(--color-series-3)',
  'var(--color-series-4)',
  'var(--color-series-5)',
];

export function seriesColor(id: string, index: number): string {
  if (id === OTHERS_ID) return 'var(--color-series-other)';
  return SERIES_COLORS[index % SERIES_COLORS.length];
}
