export type RankedItem = {
  id: string;
  label: string;
  color: string;
  value: number;
};

interface RankedListProps  {
  items: RankedItem[];
};

export default function RankedList({ items }: Readonly<RankedListProps>) {
  const total = items.reduce((sum, item) => sum + item.value, 0);

  return (
    <ol className="flex flex-col gap-2">
      {items.map((item) => {
        const share = total > 0 ? item.value / total : 0;
        return (
          <li key={item.id} className="flex flex-col gap-1">
            <div className="flex items-center gap-2 text-sm">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: item.color }} />
              <span className="flex-1 truncate text-body">{item.label}</span>
              <span className="tabular-nums text-ink">{item.value.toLocaleString()}</span>
              <span className="w-10 text-right tabular-nums text-subtle">{Math.round(share * 100)}%</span>
            </div>
            <div className="h-1 overflow-hidden rounded-full bg-track">
              <div className="h-full rounded-full" style={{ width: `${share * 100}%`, background: item.color }} />
            </div>
          </li>
        );
      })}
    </ol>
  );
}
