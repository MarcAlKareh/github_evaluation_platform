export interface RolesResponse {
  [key: string]: string;
}

export interface ConfidenceInfo {
  level: "High" | "Medium" | "Low";
  score: number;
  repo_count: number;
  inspected_count: number;
  metadata_rich: number;
  signal_count: number;
}

export interface CandidateScores {
  public_activity: number;
  popularity: number;
  stack_match: number;
  project_quality: number;
}

export interface CandidateProfile {
  top_language: string;
  public_repos: number;
  total_stars: number;
  most_recent_public_activity: string;
}

export interface TopProject {
  name: string;
  language: string;
  stars: number;
  url: string;
}

export interface Candidate {
  rank: number;
  username: string;
  score: number;
  summary: string;
  confidence: ConfidenceInfo;
  scores: CandidateScores;
  profile: CandidateProfile;
  top_projects: TopProject[];
}

export interface Weights {
  activity: number;
  popularity: number;
  stack: number;
  quality: number;
}

export interface EvaluationError {
  username: string;
  status_code: number | null;
  message: string;
}

export interface EvaluationResponse {
  role: string;
  role_label: string;
  weights: Weights;
  candidate_count: number;
  ranking: Candidate[];
  errors: EvaluationError[];
}

export interface EvaluateRequest {
  role: string;
  usernames: string[];
}
