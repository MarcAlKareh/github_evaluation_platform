"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchRoles, evaluateCandidates } from "@/lib/api";
import type { RolesResponse } from "@/lib/types";

function extractUsername(input: string): string {
  const trimmed = input.trim().replace(/\/$/, "");
  const match = trimmed.match(/github\.com\/([^/\s]+)/);
  if (match) return match[1];
  return trimmed.replace(/^@/, "");
}

const getMessages = (role: string) => [
  { text: "Pulling GitHub profile...", time: 0 },
  { text: "Fetching repositories...", time: 1.3 },
  { text: "Reading contribution history...", time: 2.6 },
  { text: "Scanning public activity...", time: 3.9 },
  { text: "Analysing commit patterns...", time: 4 },
  { text: "Evaluating code quality signals...", time: 5.2 },
  { text: "Checking language spread...", time: 6.4 },
  { text: "Reviewing project depth...", time: 7.6 },
  { text: "Mapping tech stack...", time: 8.8 },
  { text: `Scoring against ${role} criteria...`, time: 10 },
  { text: "Weighing strengths and gaps...", time: 11.5 },
  { text: "Comparing to role benchmarks...", time: 13 },
  { text: "Calibrating final score...", time: 14.5 },
  { text: "Putting it all together...", time: 15 },
];

const GitHubIcon = () => (
  <svg viewBox="0 0 24 24" fill="white" className="w-4 h-4">
    <path d="M12 2C6.477 2 2 6.477 2 12c0 4.418 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.009-.868-.014-1.703-2.782.603-3.369-1.342-3.369-1.342-.454-1.155-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.115 2.504.337 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.163 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
  </svg>
);

export default function HomePage() {
  const router = useRouter();
  const [roles, setRoles] = useState<RolesResponse>({});
  const [selectedRole, setSelectedRole] = useState("");
  const [profilesText, setProfilesText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [rolesError, setRolesError] = useState("");
  const [loadingRoles, setLoadingRoles] = useState(true);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("");

  useEffect(() => {
    fetchRoles()
      .then((data) => {
        setRoles(data);
        const first = Object.keys(data)[0];
        if (first) setSelectedRole(first);
      })
      .catch(() =>
        setRolesError(
          "Cannot reach the backend. Start the API server with: uvicorn api:app --reload"
        )
      )
      .finally(() => setLoadingRoles(false));
  }, []);

  useEffect(() => {
    if (!loading) {
      setLoadingMessage("");
      return;
    }

    const messages = getMessages(roles[selectedRole] || "this role");
    const startTime = Date.now();
    setLoadingMessage(messages[0].text);

    const interval = setInterval(() => {
      const elapsed = (Date.now() - startTime) / 1000;
      let current = messages[0];
      for (const message of messages) {
        if (message.time > elapsed) break;
        current = message;
      }
      setLoadingMessage(current.text);
    }, 100);

    return () => clearInterval(interval);
  }, [loading, roles, selectedRole]);

  const candidateCount = profilesText
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean).length;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const lines = profilesText
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);

    if (lines.length === 0) {
      setError("Enter at least one GitHub profile URL or username.");
      return;
    }

    const usernames = lines.map(extractUsername).filter(Boolean);

    setLoading(true);
    try {
      const result = await evaluateCandidates({ role: selectedRole, usernames });
      sessionStorage.setItem("evaluationResult", JSON.stringify(result));
      router.push("/results");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Evaluation failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top bar */}
      <header className="bg-slate-900 px-6 py-4 flex items-center gap-3 shrink-0">
        <div className="w-7 h-7 bg-indigo-500 rounded-md flex items-center justify-center">
          <GitHubIcon />
        </div>
        <span className="text-white font-semibold text-sm tracking-wide">StackMatch</span>
        <span className="text-slate-500 text-sm ml-1">/ Candidate Evaluator</span>
      </header>

      {/* Offline banner */}
      {rolesError && !bannerDismissed && (
        <div className="bg-amber-500 text-white px-6 py-3 flex items-center gap-3 shrink-0">
          <svg
            className="w-4 h-4 shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
            />
          </svg>
          <span className="text-sm font-medium flex-1">
            Backend not reachable —{" "}
            <code className="bg-amber-600 px-1.5 py-0.5 rounded text-xs font-mono">
              uvicorn api:app --reload
            </code>
          </span>
          <button
            onClick={() => setBannerDismissed(true)}
            className="text-amber-200 hover:text-white transition-colors ml-2"
            aria-label="Dismiss"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Main */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-lg">
          {/* Card */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-lg p-8">
            {/* Pill badge */}
            <div className="flex justify-center mb-6">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 text-slate-500 text-xs font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
                Powered by GitHub API
              </span>
            </div>

            <div className="mb-7 text-center">
              <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
                Evaluate GitHub Candidates
              </h1>
              <p className="mt-2.5 text-slate-500 text-base leading-relaxed">
                Paste profiles, pick a role, get an instant ranked report.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
              {/* Role selector */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Role
                </label>
                {loadingRoles ? (
                  <div className="h-11 bg-slate-100 rounded-lg animate-pulse" />
                ) : (
                  <select
                    value={selectedRole}
                    onChange={(e) => setSelectedRole(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    disabled={Object.keys(roles).length === 0}
                  >
                    {Object.keys(roles).length === 0 ? (
                      <option>— backend offline —</option>
                    ) : (
                      Object.entries(roles).map(([key, label]) => (
                        <option key={key} value={key}>
                          {label}
                        </option>
                      ))
                    )}
                  </select>
                )}
              </div>

              {/* GitHub URLs */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  GitHub Profiles
                </label>
                <textarea
                  value={profilesText}
                  onChange={(e) => setProfilesText(e.target.value)}
                  placeholder={"https://github.com/torvalds\nhttps://github.com/gaearon\ndhh"}
                  rows={8}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-y font-mono shadow-inner"
                />
                <p className="mt-1.5 text-xs text-slate-400">
                  One URL or username per line. Full URLs and bare usernames both work.
                  {candidateCount > 0 && (
                    <span className="ml-2 font-medium text-indigo-500">
                      {candidateCount} candidate{candidateCount !== 1 ? "s" : ""}
                    </span>
                  )}
                </p>
              </div>

              {error && (
                <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || Object.keys(roles).length === 0}
                className="flex items-center justify-center gap-2 w-full bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-700 hover:to-indigo-600 disabled:from-indigo-300 disabled:to-indigo-300 text-white font-semibold text-sm py-3.5 rounded-xl transition-all shadow-sm"
              >
                {loading ? (
                  <>
                    <svg
                      className="animate-spin h-4 w-4"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8v8H4z"
                      />
                    </svg>
                    {loadingMessage}
                  </>
                ) : (
                  <>
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                    Run Evaluation
                  </>
                )}
              </button>

              {/* Trust signals */}
              <div className="flex items-center justify-center gap-5 pt-1">
                {["No signup required", "Free to use", "~20s per candidate"].map((t) => (
                  <span key={t} className="flex items-center gap-1 text-xs text-slate-400">
                    <svg
                      className="w-3.5 h-3.5 text-emerald-500"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2.5}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    {t}
                  </span>
                ))}
              </div>
            </form>
          </div>

          <p className="mt-4 text-center text-xs text-slate-400">
            Scores are based on public GitHub data only. Private contributions are not visible.
          </p>
        </div>
      </main>
    </div>
  );
}
