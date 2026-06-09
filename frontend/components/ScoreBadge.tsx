interface ScoreBadgeProps {
  score: number;
}

export default function ScoreBadge({ score }: ScoreBadgeProps) {
  const color =
    score >= 70
      ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200"
      : score >= 40
      ? "bg-amber-50 text-amber-700 ring-1 ring-amber-200"
      : "bg-red-50 text-red-700 ring-1 ring-red-200";

  return (
    <span
      className={`inline-flex flex-col items-center justify-center w-12 h-12 rounded-full font-bold ${color}`}
    >
      <span className="text-base leading-none">{score}</span>
      <span className="text-[9px] font-normal opacity-50 leading-none mt-0.5">/100</span>
    </span>
  );
}
