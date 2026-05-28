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


def top_language(repos: list[dict]) -> str:
    counts = Counter(r.get("language") for r in repos if r.get("language"))
    if not counts:
        return "N/A"
    return counts.most_common(1)[0][0]


def total_stars(repos: list[dict]) -> int:
    return sum(r.get("stargazers_count", 0) or 0 for r in repos)


def most_recent_activity(repos: list[dict]) -> str:
    dates = [r.get("pushed_at") for r in repos if r.get("pushed_at")]
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


# --- Scoring (backend Python engineer) ---

BACKEND_PYTHON_KEYWORDS = [
    "python", "fastapi", "django", "flask", "api", "backend",
    "rest", "sql", "postgres", "postgresql", "celery", "pytest",
]


def _days_since(iso_date: str) -> int | None:
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, TypeError):
        return None


def activity_score(repos: list[dict]) -> int:
    """Higher if they push code regularly and recently."""
    if not repos:
        return 0

    days_list = [_days_since(r["pushed_at"]) for r in repos if r.get("pushed_at")]
    days_list = [d for d in days_list if d is not None]
    if not days_list:
        return 0

    latest = min(days_list)
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
    """Based on stars on their repos (not followers)."""
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


def stack_match_score(repos: list[dict]) -> int:
    """How well their repos match a backend Python role."""
    if not repos:
        return 0

    python_count = 0
    keyword_count = 0

    for repo in repos:
        lang = (repo.get("language") or "").lower()
        name = (repo.get("name") or "").lower()
        desc = (repo.get("description") or "").lower()
        topics = " ".join(repo.get("topics") or []).lower()
        text = f"{name} {desc} {topics}"

        if lang == "python":
            python_count += 1
        if any(kw in text for kw in BACKEND_PYTHON_KEYWORDS):
            keyword_count += 1

    python_ratio = python_count / len(repos)
    keyword_ratio = keyword_count / len(repos)

    score = int(python_ratio * 55 + keyword_ratio * 45)
    return min(100, score)


def project_quality_score(repos: list[dict]) -> int:
    """Simple signals: real projects, not just empty forks."""
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


def final_score(
    activity: int, popularity: int, stack: int, quality: int
) -> int:
    return round((activity + popularity + stack + quality) / 4)


def build_explanation(
    activity: int,
    popularity: int,
    stack: int,
    quality: int,
    top_lang: str,
) -> str:
    """Builds an explanation of the score based on the activity, popularity, stack, and quality scores."""
    parts = []

    # Stack match score for backend Python engineer
    if stack >= 65:
        parts.append("Strong Python backend alignment")
    elif stack >= 40:
        parts.append("Some Python/backend signals")
    else:
        parts.append("Limited Python backend stack visible on GitHub")

    if activity >= 65:
        parts.append("consistent activity")
    elif activity >= 40:
        parts.append("moderate activity")
    else:
        parts.append("low recent activity")

    if quality >= 65:
        parts.append("good repository quality")
    elif quality < 40:
        parts.append("repository quality could be stronger")

    if popularity >= 65:
        parts.append("well-received projects by star count")
    elif popularity < 30:
        parts.append("few public stars so far")

    # python gets highlighted if it's the top language and not already mentioned
    if top_lang == "Python" and not any("Python" in p for p in parts):
        parts.insert(0, "Primary language is Python")

    if not parts:
        parts.append("Profile reviewed against backend Python criteria")

    text = ", ".join(parts)
    return text[0].upper() + text[1:] + "."


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python fetch_githubdata.py <github_username>")
        sys.exit(1)

    username = sys.argv[1].lstrip("@")

    try:
        user = get_user(username)
        repos = get_repos(username)
    except requests.HTTPError as e:
        print(f"Error: {e.response.status_code} — {e.response.json().get('message', e)}")
        sys.exit(1)

    projects = top_projects(repos)

    print(f"\nGitHub profile: @{user['login']}\n")
    print(f"Top language:       {top_language(repos)}")
    print(f"Public repos:       {user.get('public_repos', len(repos))}")
    print(f"Total stars:        {total_stars(repos)}")
    print(f"Most recent activity: {most_recent_activity(repos)}")
    print("\nTop projects:")
    for i, repo in enumerate(projects, 1):
        stars = repo.get("stargazers_count", 0)
        lang = repo.get("language") or "—"
        print(f"  {i}. {repo['name']} ({lang}, {stars} stars)")
        print(f"     {repo.get('html_url', '')}")

    lang = top_language(repos)
    act = activity_score(repos)
    pop = popularity_score(repos)
    stack = stack_match_score(repos)
    quality = project_quality_score(repos)
    score = final_score(act, pop, stack, quality)
    summary = build_explanation(act, pop, stack, quality, lang)

    print("\n--- Evaluation (backend Python engineer) ---")
    print(f"Activity score:        {act}/100")
    print(f"Popularity score:      {pop}/100")
    print(f"Stack match score:     {stack}/100")
    print(f"Project quality score: {quality}/100")
    print(f"\nScore: {score}/100")
    print(summary)


if __name__ == "__main__":
    main()
