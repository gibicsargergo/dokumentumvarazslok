export type Option = { value: string; label: string };

type Props = {
  value: string;
  options: Option[];
  onChange: (value: string) => void;
};

export default function ToggleSwitch({ value, options, onChange }: Props) {
  return (
    <div className="inline-flex rounded-lg bg-track p-1">
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            aria-pressed={active}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
              active ? 'bg-surface text-ink shadow' : 'text-subtle hover:text-emphasis'
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  )
}
