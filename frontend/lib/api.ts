import type { RolesResponse, EvaluateRequest, EvaluationResponse } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchRoles(): Promise<RolesResponse> {
  const res = await fetch(`${BASE}/roles`);
  if (!res.ok) throw new Error("Failed to fetch roles");
  return res.json();
}

export async function evaluateCandidates(
  payload: EvaluateRequest
): Promise<EvaluationResponse> {
  const res = await fetch(`${BASE}/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail = "Evaluation failed. Please try again.";
    try {
      const json = await res.json();
      if (json.detail) detail = json.detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}
