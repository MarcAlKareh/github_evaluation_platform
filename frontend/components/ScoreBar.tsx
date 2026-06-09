interface ScoreBarProps {
  label: string;
  weight: number;
  value: number;
}

function barColor(value: number) {
  if (value >= 70) return "bg-emerald-500";
  if (value >= 40) return "bg-amber-400";
  return "bg-red-400";
}

export default function ScoreBar({ label, weight, value }: ScoreBarProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-500 w-32 shrink-0">
        {label}
        <span className="text-slate-300 ml-1">({weight}%)</span>
      </span>
      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor(value)}`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="text-xs font-semibold text-slate-600 w-8 text-right">{value}</span>
    </div>
  );
}
