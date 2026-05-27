import os
import sys
from collections import Counter
from datetime import datetime

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


if __name__ == "__main__":
    main()
