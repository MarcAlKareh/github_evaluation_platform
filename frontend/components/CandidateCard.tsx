"use client";

import type { Candidate } from "@/lib/types";
import ScoreBar from "./ScoreBar";
import ScoreBadge from "./ScoreBadge";
import ConfidenceBadge from "./ConfidenceBadge";

interface CandidateCardProps {
  candidate: Candidate;
}

const RANK_COLORS: Record<number, string> = {
  1: "bg-amber-400 text-white",
  2: "bg-slate-400 text-white",
  3: "bg-orange-400 text-white",
};

const LANG_COLORS: Record<string, string> = {
  Python: "#3572A5",
  JavaScript: "#F1E05A",
  TypeScript: "#2b7489",
  Go: "#00ADD8",
  Ruby: "#701516",
  Rust: "#DEA584",
  C: "#555555",
  "C++": "#F34B7D",
  Java: "#B07219",
  Kotlin: "#A97BFF",
  Swift: "#F05138",
  PHP: "#4F5D95",
  Shell: "#89E051",
  HTML: "#E34C26",
  CSS: "#563D7C",
};

function accentBorder(score: number) {
  if (score >= 70) return "border-l-4 border-l-emerald-500";
  if (score >= 40) return "border-l-4 border-l-amber-400";
  return "border-l-4 border-l-red-400";
}

function avatarRing(score: number) {
  if (score >= 70) return "ring-2 ring-offset-1 ring-emerald-400";
  if (score >= 40) return "ring-2 ring-offset-1 ring-amber-400";
  return "ring-2 ring-offset-1 ring-red-400";
}

export default function CandidateCard({ candidate }: CandidateCardProps) {
  const { rank, username, score, summary, confidence, scores, profile, top_projects } =
    candidate;

  const isTop = rank === 1;

  return (
    <div
      className={`bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden ${accentBorder(score)} ${
        isTop ? "ring-2 ring-amber-300/50" : ""
      }`}
    >
      {/* Card header */}
      <div className="flex items-center gap-4 px-5 py-4 border-b border-slate-100">
        {/* Rank bubble */}
        <span
          className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${
            RANK_COLORS[rank] ?? "bg-slate-100 text-slate-600"
          }`}
        >
          {rank}
        </span>

        {/* Avatar */}
        <img
          src={`https://github.com/${username}.png?size=96`}
          alt={username}
          className={`w-12 h-12 rounded-full border border-slate-200 shrink-0 ${avatarRing(score)}`}
        />

        {/* Name + meta */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <a
              href={`https://github.com/${username}`}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-slate-900 hover:text-indigo-600 transition-colors"
            >
              {username}
            </a>
            {isTop && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-xs font-medium">
                🏆 Top Candidate
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            {profile.top_language} · {profile.public_repos} repos · ⭐{" "}
            {profile.total_stars.toLocaleString()} stars
          </p>
        </div>

        {/* Score + confidence */}
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <ScoreBadge score={score} />
          <ConfidenceBadge level={confidence.level} score={confidence.score} />
        </div>
      </div>

      {/* Card body */}
      <div className="px-5 py-4 flex flex-col sm:flex-row gap-6">
        {/* Score bars */}
        <div className="flex-1 flex flex-col gap-3">
          <ScoreBar label="Stack Match" weight={35} value={scores.stack_match} />
          <ScoreBar label="Project Quality" weight={30} value={scores.project_quality} />
          <ScoreBar label="Popularity" weight={20} value={scores.popularity} />
          <ScoreBar label="Public Activity" weight={15} value={scores.public_activity} />
        </div>

        {/* Right: summary + projects */}
        <div className="sm:w-56 flex flex-col gap-3 shrink-0">
          <p className="text-xs text-slate-500 leading-relaxed">{summary}</p>

          <p className="text-xs text-slate-400">
            Last active:{" "}
            <span className="text-slate-600 font-medium">
              {profile.most_recent_public_activity}
            </span>
          </p>

          {top_projects.length > 0 && (
            <div className="flex flex-col gap-1.5">
              {top_projects.slice(0, 3).map((proj) => {
                const langColor = LANG_COLORS[proj.language];
                return (
                  <a
                    key={proj.name}
                    href={proj.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 transition-colors group"
                  >
                    <span className="flex items-center gap-1.5 min-w-0">
                      {langColor && (
                        <span
                          className="w-2 h-2 rounded-full shrink-0"
                          style={{ backgroundColor: langColor }}
                        />
                      )}
                      <span className="text-xs font-medium text-slate-700 group-hover:text-indigo-600 truncate">
                        {proj.name}
                      </span>
                    </span>
                    <span className="text-xs text-slate-400 shrink-0">
                      ⭐ {proj.stars.toLocaleString()}
                    </span>
                  </a>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Evidence footer */}
      <div className="px-5 py-2.5 bg-slate-50 border-t border-slate-100 flex items-center gap-1.5 text-xs text-slate-400">
        <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        {confidence.repo_count} public repos · {confidence.inspected_count} inspected ·{" "}
        {confidence.signal_count} file signals detected
      </div>
    </div>
  );
}
