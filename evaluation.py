"""
GitHub candidate evaluation — fetch public profile data and score role fit.

Usage:
    python evaluation.py <role> <username1> [username2] ... [--json]
    python evaluation.py torvalds backend [--json]   (legacy: username then role)

Roles: backend, frontend, ml, devops
"""

import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")
BASE_URL = "https://api.github.com"

headers = {
    "Accept": "application/vnd.github+json",
}
if TOKEN:
    headers["Authorization"] = f"Bearer {TOKEN}"


# Each role defines what languages and keywords we look for in repos.
ROLE_PROFILES = {
    "backend": {
        "label": "Backend Engineer",
        "preferred_languages": ["Python", "Go", "Java", "Ruby", "PHP", "C#"],
        "keywords": [
            "api", "rest", "graphql", "backend", "server",
            "fastapi", "django", "flask", "express", "spring",
            "sql", "postgres", "postgresql", "mysql", "redis",
            "microservice", "celery", "pytest",
        ],
    },
    "frontend": {
        "label": "Frontend Engineer",
        "preferred_languages": ["JavaScript", "TypeScript", "HTML", "CSS"],
        "keywords": [
            "react", "vue", "angular", "svelte", "nextjs", "next.js",
            "frontend", "ui", "ux", "tailwind", "webpack", "vite",
            "component", "spa", "css", "html",
        ],
    },
    "ml": {
        "label": "Machine Learning Engineer",
        "preferred_languages": ["Python", "R", "Julia"],
        "keywords": [
            "machine learning", "deep learning", "ml", "ai",
            "pytorch", "tensorflow", "keras", "sklearn", "scikit-learn",
            "nlp", "computer vision", "notebook", "pandas", "numpy",
            "huggingface", "llm", "model training",
        ],
    },
    "devops": {
        "label": "DevOps Engineer",
        "preferred_languages": ["Go", "Python", "Shell", "HCL"],
        "keywords": [
            "docker", "kubernetes", "k8s", "terraform", "ansible",
            "ci/cd", "github actions", "jenkins", "helm",
            "aws", "gcp", "azure", "infrastructure", "monitoring",
            "prometheus", "grafana", "devops", "deployment",
        ],
    },
}

# How many top repos to open via the Contents API (each may need 2–3 calls)
INSPECT_REPO_LIMIT = 8

# If a repo contains these files, we treat them as hints for role stack matching
SIGNAL_TO_KEYWORDS = {
    "has_package_json": ["javascript", "typescript", "react", "vue", "frontend", "node", "express"],
    "has_requirements_txt": ["python", "django", "flask", "fastapi", "pytest", "backend"],
    "has_dockerfile": ["docker", "devops", "deployment", "kubernetes", "ci/cd"],
    "has_workflows": ["ci/cd", "github actions", "devops", "deployment"],
    "has_notebooks": ["notebook", "ml", "machine learning", "pytorch", "tensorflow", "pandas"],
    "has_tests": ["pytest", "testing", "backend"],
}


def get_user(username: str) -> dict:
    response = requests.get(f"{BASE_URL}/users/{username}", headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def get_repos(username: str) -> list[dict]:
    repos = []
    page = 1
    while True:
        response = requests.get(
            f"{BASE_URL}/users/{username}/repos",
            headers=headers,
            params={"per_page": 100, "page": page, "sort": "updated"},
            timeout=30,
        )
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def get_public_events(username: str) -> list[dict]:
    """
    Recent public activity (pushes, PRs, issues on public repos).

    Note: GitHub does not expose private repo work here. Many active
    developers (e.g. course creators) look quiet on this metric anyway.
    """
    response = requests.get(
        f"{BASE_URL}/users/{username}/events/public",
        headers=headers,
        params={"per_page": 100},
        timeout=30,
    )
    if response.status_code == 404:
        return []
    response.raise_for_status()
    return response.json()


def top_language(repos: list[dict]) -> str:
    counts = Counter(r.get("language") for r in repos if r.get("language"))
    if not counts:
        return "N/A"
    return counts.most_common(1)[0][0]


def total_stars(repos: list[dict]) -> int:
    return sum(r.get("stargazers_count", 0) or 0 for r in repos)


def most_recent_activity(repos: list[dict], public_events: list[dict] | None = None) -> str:
    """Latest visible activity from public repo pushes and public events."""
    dates = [r.get("pushed_at") for r in repos if r.get("pushed_at")]
    if public_events:
        dates.extend(e.get("created_at") for e in public_events if e.get("created_at"))
    if not dates:
        return "N/A"
    latest = max(dates)
    try:
        dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return latest


def top_projects(repos: list[dict], limit: int = 5) -> list[dict]:
    ranked = sorted(
        repos,
        key=lambda r: (r.get("stargazers_count", 0) or 0, r.get("pushed_at") or ""),
        reverse=True,
    )
    return ranked[:limit]


def _list_repo_paths(owner: str, repo: str, path: str = "") -> list[str]:
    """
    List file/folder names at a path in a repo (GitHub Contents API).

    Returns an empty list if the path is missing or the repo is empty.
    """
    url = f"{BASE_URL}/repos/{owner}/{repo}/contents"
    if path:
        url += f"/{path}"
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        return []
    return [item.get("name", "") for item in data]


def inspect_repo_engineering_signals(full_name: str) -> dict[str, bool]:
    """
    Check a repo's root (and .github/workflows) for common engineering files.

    We only look at names, not file contents — keeps this fast and simple.
    """
    owner, repo = full_name.split("/", 1)
    root_names = _list_repo_paths(owner, repo)
    root_lower = {name.lower() for name in root_names}

    signals = {
        "has_package_json": "package.json" in root_lower,
        # Python deps: requirements.txt or pyproject.toml
        "has_requirements_txt": (
            "requirements.txt" in root_lower or "pyproject.toml" in root_lower
        ),
        "has_dockerfile": any(
            name == "dockerfile" or name.startswith("dockerfile")
            for name in root_lower
        ),
        "has_workflows": False,
        "has_notebooks": any(name.endswith(".ipynb") for name in root_names),
        "has_tests": False,
    }

    # Notebook folder (common in ML repos)
    if "notebooks" in root_lower:
        signals["has_notebooks"] = True

    # Testing: folder names or common config files at repo root
    test_names = {"tests", "test", "__tests__", "pytest.ini", "tox.ini", "conftest.py"}
    signals["has_tests"] = bool(root_lower & test_names)

    # CI/CD: .github/workflows/*.yml (one extra API call if .github exists)
    if ".github" in root_lower:
        github_items = _list_repo_paths(owner, repo, ".github")
        if "workflows" in {name.lower() for name in github_items}:
            workflow_files = _list_repo_paths(owner, repo, ".github/workflows")
            signals["has_workflows"] = len(workflow_files) > 0

    return signals


def collect_repo_signals(repos: list[dict], limit: int = INSPECT_REPO_LIMIT) -> dict[str, dict[str, bool]]:
    """
    Inspect the top public repos and return {full_name: signals}.

    We skip archived repos and cap how many we open to avoid rate limits.
    """
    pool = [r for r in repos if not r.get("archived")]
    to_inspect = top_projects(pool, limit=limit)
    signals_by_repo: dict[str, dict[str, bool]] = {}

    for repo in to_inspect:
        full_name = repo["full_name"]
        try:
            signals_by_repo[full_name] = inspect_repo_engineering_signals(full_name)
        except requests.HTTPError:
            # Empty repo or no permission — treat as no signals
            signals_by_repo[full_name] = {}
        time.sleep(0.1)

    return signals_by_repo


def _signals_match_role(signals: dict[str, bool], role_keywords: list[str]) -> bool:
    """True if any detected file hint overlaps this role's keyword list."""
    if not signals:
        return False
    for signal_key, hint_words in SIGNAL_TO_KEYWORDS.items():
        if not signals.get(signal_key):
            continue
        for hint in hint_words:
            if any(hint in kw or kw in hint for kw in role_keywords):
                return True
    return False


def _days_since(iso_date: str) -> int | None:
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, TypeError):
        return None


def activity_score(repos: list[dict], public_events: list[dict] | None = None) -> int:
    """
    Score based on PUBLIC signals only (repo push dates + public events).

    Private contributions are invisible to the API without special access.
    """
    days_list = []

    for repo in repos:
        if repo.get("pushed_at"):
            days = _days_since(repo["pushed_at"])
            if days is not None:
                days_list.append(days)

    if public_events:
        for event in public_events:
            days = _days_since(event.get("created_at"))
            if days is not None:
                days_list.append(days)

    if not days_list:
        return 0

    latest = min(days_list)  # smallest number of days = most recent
    active_90d = sum(1 for d in days_list if d <= 90)
    active_365d = sum(1 for d in days_list if d <= 365)

    score = 0
    if latest <= 30:
        score += 40
    elif latest <= 90:
        score += 28
    elif latest <= 180:
        score += 15

    score += min(35, active_90d * 7)
    score += min(25, active_365d * 3)
    return min(100, score)


def popularity_score(repos: list[dict]) -> int:
    """Based on total stars (we do not use follower count)."""
    stars = total_stars(repos)
    if stars >= 500:
        return 100
    if stars >= 200:
        return 85
    if stars >= 50:
        return 70
    if stars >= 10:
        return 50
    if stars >= 1:
        return 30
    return 10


def stack_match_score(
    repos: list[dict],
    role_profile: dict,
    repo_signals: dict[str, dict[str, bool]] | None = None,
) -> int:
    """
    Compare repos against a role profile.

    - language match: repo's main language is in preferred_languages
    - keyword match: role keywords in name, description, or topics
    - content match: files like package.json / requirements.txt fit the role
    """
    if not repos:
        return 0

    repo_signals = repo_signals or {}
    preferred = {lang.lower() for lang in role_profile["preferred_languages"]}
    keywords = [kw.lower() for kw in role_profile["keywords"]]

    language_matches = 0
    keyword_matches = 0
    content_matches = 0

    for repo in repos:
        lang = (repo.get("language") or "").lower()
        name = (repo.get("name") or "").lower()
        desc = (repo.get("description") or "").lower()
        topics = " ".join(repo.get("topics") or []).lower()
        text = f"{name} {desc} {topics}"
        signals = repo_signals.get(repo.get("full_name", ""), {})

        if lang in preferred:
            language_matches += 1
        if any(kw in text for kw in keywords):
            keyword_matches += 1
        if _signals_match_role(signals, keywords):
            content_matches += 1

    language_ratio = language_matches / len(repos)
    keyword_ratio = keyword_matches / len(repos)
    content_ratio = content_matches / len(repos)

    # Base score from metadata; up to +15 from real files in the repo
    base = language_ratio * 55 + keyword_ratio * 45
    bonus = content_ratio * 15
    return min(100, int(base + bonus))


def project_quality_score(
    repos: list[dict],
    repo_signals: dict[str, dict[str, bool]] | None = None,
) -> int:
    """
    Points for metadata (description, size, stars) plus engineering files
    when we inspected the repo (tests, CI, Docker, dependency manifests).
    """
    repo_signals = repo_signals or {}
    pool = [r for r in repos if not r.get("fork")] or repos
    if not pool:
        return 0

    repo_scores = []
    for repo in pool:
        points = 0
        if repo.get("description"):
            points += 20
        if not repo.get("archived"):
            points += 20
        if (repo.get("size") or 0) >= 20:
            points += 20
        if (repo.get("stargazers_count") or 0) > 0 or (repo.get("forks_count") or 0) > 0:
            points += 20

        signals = repo_signals.get(repo.get("full_name", ""), {})
        if signals.get("has_tests"):
            points += 10
        if signals.get("has_workflows"):
            points += 10
        if signals.get("has_dockerfile"):
            points += 8
        if signals.get("has_package_json") or signals.get("has_requirements_txt"):
            points += 7
        if signals.get("has_notebooks"):
            points += 5

        repo_scores.append(min(100, points))

    repo_scores.sort(reverse=True)
    top = repo_scores[:5]
    return int(sum(top) / len(top))


# How much each category affects the final score (must add up to 1.0).
# Stack + quality use repo contents and metadata — most reliable from public data.
# Activity is public-only and often low for strong engineers in private work — lowest weight.
SCORE_WEIGHTS = {
    "activity": 0.15,
    "popularity": 0.20,
    "stack": 0.35,
    "quality": 0.30,
}


def final_score(activity: int, popularity: int, stack: int, quality: int) -> int:
    w = SCORE_WEIGHTS
    weighted = (
        activity * w["activity"]
        + popularity * w["popularity"]
        + stack * w["stack"]
        + quality * w["quality"]
    )
    return round(weighted)


def compute_confidence(
    repos: list[dict],
    repo_signals: dict[str, dict[str, bool]],
) -> dict:
    """
    How much public evidence we had to score this candidate.

    A score from 2 repos is a guess; a score from 50 repos + file inspection
  is much more trustworthy. This does NOT change the fit score — it labels
    how much to trust it when ranking people.
    """
    repo_count = len(repos)
    inspected_count = len(repo_signals)

    # Repos with useful metadata (description, language, or topics)
    metadata_rich = 0
    for repo in repos:
        has_meta = sum(
            [
                bool(repo.get("description")),
                bool(repo.get("language")),
                bool(repo.get("topics")),
            ]
        )
        if has_meta >= 2:
            metadata_rich += 1

    # Total engineering file flags found across inspected repos
    signal_count = sum(
        sum(1 for flag in signals.values() if flag)
        for signals in repo_signals.values()
    )

    points = 0

    # 1) More public repos → more stable averages (up to 30 pts)
    if repo_count >= 30:
        points += 30
    elif repo_count >= 10:
        points += 22
    elif repo_count >= 5:
        points += 15
    elif repo_count >= 2:
        points += 8

    # 2) How many repos we opened via the Contents API (up to 25 pts)
    if inspected_count >= INSPECT_REPO_LIMIT:
        points += 25
    elif inspected_count >= 5:
        points += 18
    elif inspected_count >= 1:
        points += 10

    # 3) Share of repos with decent metadata (up to 25 pts)
    if repo_count > 0:
        metadata_ratio = metadata_rich / repo_count
        points += int(metadata_ratio * 25)

    # 4) Engineering signals detected in files (up to 20 pts)
    if signal_count >= 15:
        points += 20
    elif signal_count >= 8:
        points += 14
    elif signal_count >= 3:
        points += 8
    elif signal_count >= 1:
        points += 4

    confidence_score = min(100, points)

    if confidence_score >= 70:
        level = "High"
    elif confidence_score >= 40:
        level = "Medium"
    else:
        level = "Low"

    return {
        "level": level,
        "score": confidence_score,
        "repo_count": repo_count,
        "inspected_count": inspected_count,
        "metadata_rich": metadata_rich,
        "signal_count": signal_count,
    }


def build_explanation(
    activity: int,
    popularity: int,
    stack: int,
    quality: int,
    top_lang: str,
    role_profile: dict,
) -> str:
    """Short human-readable summary based on sub-scores and role."""
    role_name = role_profile["label"]
    parts = []

    if stack >= 65:
        parts.append(f"Strong {role_name.lower()} stack alignment")
    elif stack >= 40:
        parts.append(f"Some {role_name.lower()} signals")
    else:
        parts.append(f"Limited {role_name.lower()} stack visible on GitHub")

    if activity >= 65:
        parts.append("consistent public activity")
    elif activity >= 40:
        parts.append("moderate public activity")
    else:
        parts.append("limited recent public activity")

    if quality >= 65:
        parts.append("good repository quality")
    elif quality < 40:
        parts.append("repository quality could be stronger")

    if popularity >= 65:
        parts.append("well-received projects by star count")
    elif popularity < 30:
        parts.append("few public stars so far")

    preferred = role_profile["preferred_languages"]
    if top_lang in preferred and not any(top_lang in p for p in parts):
        parts.insert(0, f"Primary language is {top_lang} (good for this role)")

    if not parts:
        parts.append(f"Profile reviewed for {role_name}")

    text = ", ".join(parts)
    return text[0].upper() + text[1:] + "."


def parse_cli(argv: list[str]) -> tuple[dict, list[str], bool, str]:
    """
    Parse command-line args into a role profile, usernames, and --json flag.

    Preferred:  python evaluation.py frontend gaearon torvalds --json
    Legacy:     python evaluation.py gaearon frontend
                python evaluation.py gaearon
    """
    json_output = "--json" in argv
    args = [arg for arg in argv if arg != "--json"]

    valid_roles = set(ROLE_PROFILES.keys())

    if len(args) < 2:
        valid = ", ".join(ROLE_PROFILES.keys())
        print(f"Usage: python evaluation.py <role> <username1> [username2] ... [--json]")
        print(f"Roles: {valid}")
        sys.exit(1)

    first = args[1].lower()

    # New style: role first, then all usernames
    if first in valid_roles:
        role_key = first
        usernames = [name.lstrip("@") for name in args[2:]]
    # Legacy: username first, optional role as second arg
    elif len(args) > 2 and args[2].lower() in valid_roles:
        role_key = args[2].lower()
        usernames = [args[1].lstrip("@")]
    else:
        role_key = "backend"
        usernames = [args[1].lstrip("@")]

    if not usernames:
        print("Error: provide at least one GitHub username after the role.")
        sys.exit(1)

    return ROLE_PROFILES[role_key], usernames, json_output, role_key


def evaluate_candidate(username: str, role_profile: dict) -> dict:
    """Fetch data, score one candidate, return all results as a dict."""
    user = get_user(username)
    repos = get_repos(username)
    public_events = get_public_events(username)

    print(f"  Inspecting @{user['login']}...", file=sys.stderr)
    repo_signals = collect_repo_signals(repos)

    lang = top_language(repos)
    act = activity_score(repos, public_events)
    pop = popularity_score(repos)
    stack = stack_match_score(repos, role_profile, repo_signals)
    quality = project_quality_score(repos, repo_signals)
    score = final_score(act, pop, stack, quality)
    confidence = compute_confidence(repos, repo_signals)
    summary = build_explanation(act, pop, stack, quality, lang, role_profile)

    return {
        "username": user["login"],
        "user": user,
        "repos": repos,
        "public_events": public_events,
        "projects": top_projects(repos),
        "top_lang": lang,
        "activity": act,
        "popularity": pop,
        "stack": stack,
        "quality": quality,
        "score": score,
        "confidence": confidence,
        "summary": summary,
    }


def print_candidate_report(result: dict, role_profile: dict) -> None:
    """Full breakdown for a single candidate."""
    user = result["user"]
    repos = result["repos"]
    confidence = result["confidence"]
    w = SCORE_WEIGHTS

    print(f"\nGitHub profile: @{result['username']}\n")
    print(f"Role:               {role_profile['label']}")
    print(f"Top language:       {result['top_lang']}")
    print(f"Public repos:       {user.get('public_repos', len(repos))}")
    print(f"Total stars:        {total_stars(repos)}")
    print(f"Most recent public activity: {most_recent_activity(repos, result.get('public_events'))}")
    print("\nTop projects:")
    for i, repo in enumerate(result["projects"], 1):
        stars = repo.get("stargazers_count", 0)
        lang = repo.get("language") or "—"
        print(f"  {i}. {repo['name']} ({lang}, {stars} stars)")
        print(f"     {repo.get('html_url', '')}")

    print(f"\n--- Evaluation ({role_profile['label']}) ---")
    print(f"Public Activity Score: {result['activity']}/100  (weight {int(w['activity'] * 100)}%, public data only)")
    print(f"Popularity score:      {result['popularity']}/100  (weight {int(w['popularity'] * 100)}%)")
    print(f"Stack match score:     {result['stack']}/100  (weight {int(w['stack'] * 100)}%)")
    print(f"Project quality score: {result['quality']}/100  (weight {int(w['quality'] * 100)}%)")
    print(f"\nScore: {result['score']}/100")
    print(f"Confidence: {confidence['level']} ({confidence['score']}/100)")
    print(
        f"  Evidence: {confidence['repo_count']} public repos, "
        f"{confidence['inspected_count']} inspected, "
        f"{confidence['metadata_rich']} with rich metadata, "
        f"{confidence['signal_count']} file signals detected."
    )
    if confidence["level"] == "Low":
        print("  Note: Limited public data — treat this score as a rough signal.")
    print(result["summary"])


def build_json_report(results: list[dict], role_profile: dict, role_key: str) -> dict:
    """Build a JSON-serializable report for APIs and frontends."""
    ranking = []
    for rank, result in enumerate(results, 1):
        user = result["user"]
        repos = result["repos"]
        ranking.append(
            {
                "rank": rank,
                "username": result["username"],
                "score": result["score"],
                "summary": result["summary"],
                "confidence": result["confidence"],
                "scores": {
                    "public_activity": result["activity"],
                    "popularity": result["popularity"],
                    "stack_match": result["stack"],
                    "project_quality": result["quality"],
                },
                "profile": {
                    "top_language": result["top_lang"],
                    "public_repos": user.get("public_repos", len(repos)),
                    "total_stars": total_stars(repos),
                    "most_recent_public_activity": most_recent_activity(
                        repos, result.get("public_events")
                    ),
                },
                "top_projects": [
                    {
                        "name": repo["name"],
                        "language": repo.get("language"),
                        "stars": repo.get("stargazers_count", 0),
                        "url": repo.get("html_url", ""),
                    }
                    for repo in result["projects"]
                ],
            }
        )

    return {
        "role": role_key,
        "role_label": role_profile["label"],
        "weights": SCORE_WEIGHTS,
        "candidate_count": len(ranking),
        "ranking": ranking,
    }


def print_leaderboard(results: list[dict], role_profile: dict) -> None:
    """Ranked list when comparing multiple candidates for the same role."""
    print(f"\n{'=' * 60}")
    print(f"LEADERBOARD — {role_profile['label']}")
    print(f"{'=' * 60}\n")

    for rank, result in enumerate(results, 1):
        conf = result["confidence"]
        print(f"#{rank}  @{result['username']}")
        print(f"     Score: {result['score']}/100  |  Confidence: {conf['level']}")
        print(f"     {result['summary']}")
        print()


def main() -> None:
    role_profile, usernames, json_output, role_key = parse_cli(sys.argv)
    results: list[dict] = []

    print(f"\nEvaluating {len(usernames)} candidate(s) for {role_profile['label']}...\n", file=sys.stderr)

    for username in usernames:
        try:
            result = evaluate_candidate(username, role_profile)
            results.append(result)
        except requests.HTTPError as e:
            message = e.response.json().get("message", str(e)) if e.response else str(e)
            print(f"  Skipped @{username}: {e.response.status_code} — {message}", file=sys.stderr)

    if not results:
        print("No candidates could be evaluated.", file=sys.stderr if json_output else sys.stdout)
        sys.exit(1)

    # Sort by score (highest first); use confidence as tiebreaker
    results.sort(key=lambda r: (r["score"], r["confidence"]["score"]), reverse=True)

    if json_output:
        report = build_json_report(results, role_profile, role_key)
        print(json.dumps(report, indent=2))
        return

    # One candidate: show full report. Several: show brief per-person + leaderboard.
    if len(results) == 1:
        print_candidate_report(results[0], role_profile)
    else:
        for result in results:
            conf = result["confidence"]
            print(f"@{result['username']}: {result['score']}/100 (Confidence: {conf['level']})")
        print_leaderboard(results, role_profile)


if __name__ == "__main__":
    main()
