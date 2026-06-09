"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { EvaluationResponse } from "@/lib/types";
import CandidateCard from "@/components/CandidateCard";

const GitHubIcon = () => (
  <svg viewBox="0 0 24 24" fill="white" className="w-4 h-4">
    <path d="M12 2C6.477 2 2 6.477 2 12c0 4.418 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.009-.868-.014-1.703-2.782.603-3.369-1.342-3.369-1.342-.454-1.155-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.115 2.504.337 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.163 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
  </svg>
);

const WEIGHT_DOTS: Record<string, string> = {
  "Stack Match": "bg-indigo-500",
  "Project Quality": "bg-emerald-500",
  Popularity: "bg-amber-400",
  Activity: "bg-slate-400",
};

export default function ResultsPage() {
  const [data, setData] = useState<EvaluationResponse | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem("evaluationResult");
    if (raw) {
      try {
        setData(JSON.parse(raw));
      } catch {}
    }
  }, []);

  if (!data) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center gap-4 px-4">
        <p className="text-slate-500 text-sm">No results found — run an evaluation first.</p>
        <Link href="/" className="text-indigo-600 text-sm hover:underline">
          ← Start evaluation
        </Link>
      </div>
    );
  }

  const weights = [
    { label: "Stack Match", pct: Math.round(data.weights.stack * 100) },
    { label: "Project Quality", pct: Math.round(data.weights.quality * 100) },
    { label: "Popularity", pct: Math.round(data.weights.popularity * 100) },
    { label: "Activity", pct: Math.round(data.weights.activity * 100) },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Nav bar */}
      <header className="bg-slate-900 px-6 py-4 flex items-center gap-3 shrink-0">
        <div className="w-7 h-7 bg-indigo-500 rounded-md flex items-center justify-center">
          <GitHubIcon />
        </div>
        <span className="text-white font-semibold text-sm tracking-wide">StackMatch</span>
        <span className="text-slate-500 text-sm ml-1">/ Results</span>
        <Link
          href="/"
          className="ml-auto text-slate-400 hover:text-white text-sm transition-colors"
        >
          ← New Evaluation
        </Link>
      </header>

      {/* Gradient hero strip */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-700 px-6 py-8 shrink-0">
        <div className="max-w-3xl mx-auto flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-white">{data.role_label}</h1>
            <p className="text-slate-400 text-sm mt-1">Ranked by overall role fit</p>
          </div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/10 text-white text-sm font-medium border border-white/20 self-start sm:self-auto">
            {data.candidate_count} candidate{data.candidate_count !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      <main className="flex-1 px-4 py-8">
        <div className="max-w-3xl mx-auto">
          {/* Scoring weights pill row */}
          <div className="mb-6 px-4 py-3 bg-white border border-slate-200 rounded-xl flex flex-wrap items-center gap-x-5 gap-y-2 text-xs shadow-sm">
            <span className="font-semibold text-slate-600 shrink-0">Score weights</span>
            {weights.map((w) => (
              <span key={w.label} className="flex items-center gap-1.5">
                <span
                  className={`w-2 h-2 rounded-full shrink-0 ${
                    WEIGHT_DOTS[w.label] ?? "bg-slate-300"
                  }`}
                />
                <span className="text-slate-700 font-medium">{w.label}</span>
                <span className="text-slate-400">{w.pct}%</span>
              </span>
            ))}
          </div>

          {/* Candidate cards */}
          <div className="flex flex-col gap-4">
            {data.ranking.map((candidate) => (
              <CandidateCard key={candidate.username} candidate={candidate} />
            ))}
          </div>

          {/* Failed profiles */}
          {data.errors && data.errors.length > 0 && (
            <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-xl">
              <p className="text-sm font-semibold text-amber-800 mb-2">
                Could not evaluate {data.errors.length} profile
                {data.errors.length !== 1 ? "s" : ""}:
              </p>
              <ul className="space-y-1">
                {data.errors.map((err, i) => (
                  <li key={i} className="text-sm text-amber-700">
                    <span className="font-mono font-medium">@{err.username}</span>
                    {" — "}
                    {err.status_code === 403
                      ? "GitHub rate limit exceeded — add a GitHub token to evaluate more profiles"
                      : err.status_code === 404
                      ? "Profile not found"
                      : err.message.replace(/for url: https?:\/\/[^\s]+/g, "").trim()}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
