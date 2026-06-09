interface ConfidenceBadgeProps {
  level: "High" | "Medium" | "Low";
  score: number;
}

export default function ConfidenceBadge({ level, score }: ConfidenceBadgeProps) {
  const { dot, text } =
    level === "High"
      ? { dot: "bg-emerald-500", text: "text-emerald-700" }
      : level === "Medium"
      ? { dot: "bg-amber-400", text: "text-amber-700" }
      : { dot: "bg-red-400", text: "text-red-700" };

  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${text}`}>
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dot}`} />
      {level} confidence ({score})
    </span>
  );
}
