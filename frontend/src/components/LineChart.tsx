import { useEffect, useRef, useState } from 'react';

export type LineSeries = {
  id: string;
  label: string;
  color: string;
  values: number[];
};



const PAD = { top: 8, right: 12, bottom: 22, left: 36 };

function niceMax(value: number): number {
  if (value <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 2.5, 5, 10].find((s) => s * magnitude >= value / 4) ?? 10;
  return Math.ceil(value / (step * magnitude)) * step * magnitude;
}

function formatMonth(label: string): string {
  const [year, month] = label.split('-').map(Number);
  return new Date(year, month - 1, 1).toLocaleDateString(undefined, { month: 'short', year: '2-digit' });
}

interface LineSeriesProps {
  labels: string[];
  series: LineSeries[];
  height?: number;
};

export default function LineChart({ labels, series, height = 180 }: Readonly<LineSeriesProps>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const [hover, setHover] = useState<number | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const max = niceMax(Math.max(0, ...series.flatMap((s) => s.values)));
  const plotW = Math.max(0, width - PAD.left - PAD.right);
  const plotH = height - PAD.top - PAD.bottom;
  const x = (i: number) => PAD.left + (labels.length > 1 ? (i / (labels.length - 1)) * plotW : plotW / 2);
  const y = (v: number) => PAD.top + plotH - (v / max) * plotH;
  const ticks = [0, max / 2, max];
  const labelEvery = Math.max(1, Math.ceil(labels.length / Math.max(1, Math.floor(plotW / 56))));

  function onMove(e: React.MouseEvent<SVGRectElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    setHover(Math.min(labels.length - 1, Math.max(0, Math.round(ratio * (labels.length - 1)))));
  }

  const tooltipLeft = hover !== null ? x(hover) : 0;
  const flip = tooltipLeft > width / 2;

  return (
    <div ref={containerRef} className="relative w-full" style={{ height }}>
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label="Searches per month">
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={width - PAD.right} y1={y(t)} y2={y(t)} stroke="var(--color-grid)" />
              <text x={PAD.left - 6} y={y(t)} dy="0.32em" textAnchor="end" className="fill-muted text-[10px]">
                {t.toLocaleString()}
              </text>
            </g>
          ))}

          {labels.map((label, i) =>
            i % labelEvery === 0 ? (
              <text key={label} x={x(i)} y={height - 6} textAnchor="middle" className="fill-muted text-[10px]">
                {formatMonth(label)}
              </text>
            ) : null,
          )}

          {hover !== null && (
            <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={PAD.top + plotH} stroke="var(--color-line)" />
          )}

          {series.map((s) => (
            <polyline
              key={s.id}
              points={s.values.map((v, i) => `${x(i)},${y(v)}`).join(' ')}
              fill="none"
              stroke={s.color}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          ))}

          {hover !== null &&
            series.map((s) => (
              <circle
                key={s.id}
                cx={x(hover)}
                cy={y(s.values[hover])}
                r={4}
                fill={s.color}
                stroke="var(--color-surface)"
                strokeWidth={2}
              />
            ))}

          <rect
            x={PAD.left}
            y={0}
            width={plotW}
            height={height}
            fill="transparent"
            onMouseMove={onMove}
            onMouseLeave={() => setHover(null)}
          />
        </svg>
      )}

      {hover !== null && (
        <div
          className="pointer-events-none absolute top-0 z-10 min-w-40 rounded-md border border-line bg-surface px-3 py-2 text-xs shadow"
          style={flip ? { right: width - tooltipLeft + 8 } : { left: tooltipLeft + 8 }}
        >
          <p className="mb-1 font-medium text-ink">{formatMonth(labels[hover])}</p>
          {[...series]
            .sort((a, b) => b.values[hover] - a.values[hover])
            .map((s) => (
              <p key={s.id} className="flex items-center gap-2 text-subtle">
                <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: s.color }} />
                <span className="flex-1 truncate">{s.label}</span>
                <span className="tabular-nums text-ink">{s.values[hover].toLocaleString()}</span>
              </p>
            ))}
        </div>
      )}
    </div>
  );
}
