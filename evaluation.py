"""
GitHub candidate evaluation — fetch public profile data and score role fit.

Usage:
    python evaluation.py <username> [role]

Roles: backend, frontend, ml, devops
"""

import os
import sys
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


def stack_match_score(repos: list[dict], role_profile: dict) -> int:
    """
    Compare repos against a role profile.

    - language match: repo's main language is in preferred_languages
    - keyword match: role keywords appear in name, description, or topics
  """
    if not repos:
        return 0

    # Normalize preferred languages for easy comparison (e.g. "python" == "Python")
    preferred = {lang.lower() for lang in role_profile["preferred_languages"]}
    keywords = [kw.lower() for kw in role_profile["keywords"]]

    language_matches = 0
    keyword_matches = 0

    for repo in repos:
        lang = (repo.get("language") or "").lower()
        name = (repo.get("name") or "").lower()
        desc = (repo.get("description") or "").lower()
        topics = " ".join(repo.get("topics") or []).lower()
        text = f"{name} {desc} {topics}"

        if lang in preferred:
            language_matches += 1
        if any(kw in text for kw in keywords):
            keyword_matches += 1

    # What fraction of repos fit this role?
    language_ratio = language_matches / len(repos)
    keyword_ratio = keyword_matches / len(repos)

    # Languages matter slightly more than keywords in the name/description
    score = int(language_ratio * 55 + keyword_ratio * 45)
    return min(100, score)


def project_quality_score(repos: list[dict]) -> int:
    """Points for descriptions, size, and signs the repo is a real project."""
    pool = [r for r in repos if not r.get("fork")] or repos
    if not pool:
        return 0

    repo_scores = []
    for repo in pool:
        points = 0
        if repo.get("description"):
            points += 25
        if not repo.get("archived"):
            points += 25
        if (repo.get("size") or 0) >= 20:
            points += 25
        if (repo.get("stargazers_count") or 0) > 0 or (repo.get("forks_count") or 0) > 0:
            points += 25
        repo_scores.append(points)

    repo_scores.sort(reverse=True)
    top = repo_scores[:5]
    return int(sum(top) / len(top))


def final_score(activity: int, popularity: int, stack: int, quality: int) -> int:
    return round((activity + popularity + stack + quality) / 4)


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


def parse_role(argv: list[str]) -> dict:
    """Role is the second argument; default to backend if omitted."""
    if len(argv) > 2:
        role_key = argv[2].lower()
    else:
        role_key = "backend"

    if role_key not in ROLE_PROFILES:
        valid = ", ".join(ROLE_PROFILES.keys())
        print(f"Unknown role '{role_key}'. Choose one of: {valid}")
        sys.exit(1)

    return ROLE_PROFILES[role_key]


def main() -> None:
    if len(sys.argv) < 2:
        valid = ", ".join(ROLE_PROFILES.keys())
        print(f"Usage: python evaluation.py <github_username> [role]")
        print(f"Roles: {valid}")
        sys.exit(1)

    username = sys.argv[1].lstrip("@")
    role_profile = parse_role(sys.argv)

    try:
        user = get_user(username)
        repos = get_repos(username)
        public_events = get_public_events(username)
    except requests.HTTPError as e:
        print(f"Error: {e.response.status_code} — {e.response.json().get('message', e)}")
        sys.exit(1)

    projects = top_projects(repos)

    print(f"\nGitHub profile: @{user['login']}\n")
    print(f"Role:               {role_profile['label']}")
    print(f"Top language:       {top_language(repos)}")
    print(f"Public repos:       {user.get('public_repos', len(repos))}")
    print(f"Total stars:        {total_stars(repos)}")
    print(f"Most recent public activity: {most_recent_activity(repos, public_events)}")
    print("\nTop projects:")
    for i, repo in enumerate(projects, 1):
        stars = repo.get("stargazers_count", 0)
        lang = repo.get("language") or "—"
        print(f"  {i}. {repo['name']} ({lang}, {stars} stars)")
        print(f"     {repo.get('html_url', '')}")

    lang = top_language(repos)
    act = activity_score(repos, public_events)
    pop = popularity_score(repos)
    stack = stack_match_score(repos, role_profile)
    quality = project_quality_score(repos)
    score = final_score(act, pop, stack, quality)
    summary = build_explanation(act, pop, stack, quality, lang, role_profile)

    print(f"\n--- Evaluation ({role_profile['label']}) ---")
    print(f"Activity score:        {act}/100  (public repos + public events only)")
    print(f"Popularity score:      {pop}/100")
    print(f"Stack match score:     {stack}/100")
    print(f"Project quality score: {quality}/100")
    print(f"\nScore: {score}/100")
    print(summary)


if __name__ == "__main__":
    main()
