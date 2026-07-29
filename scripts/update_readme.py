#!/usr/bin/env python3
"""Regenera README.md con stats de GitHub, estilo neofetch."""
import json
import os
import urllib.request
from datetime import datetime, timezone

USER = "adnvilla"
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN")


def get(url, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def account_uptime(created_at):
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    delta = datetime.now(timezone.utc) - created
    years, rem = divmod(delta.days, 365)
    months, days = divmod(rem, 30)
    return f"{years} years, {months} months, {days} days"


def fetch_stats():
    user = get(f"{API}/users/{USER}")
    repos = []
    page = 1
    while True:
        batch = get(f"{API}/users/{USER}/repos?per_page=100&page={page}")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    stars = sum(r["stargazers_count"] for r in repos)
    try:
        commits = get(
            f"{API}/search/commits?q=author:{USER}",
            accept="application/vnd.github.cloak-preview+json",
        )["total_count"]
    except Exception:
        commits = "n/a"
    langs = {}
    for r in repos:
        if r["language"]:
            langs[r["language"]] = langs.get(r["language"], 0) + 1
    top_langs = ", ".join(sorted(langs, key=langs.get, reverse=True)[:5])
    return {
        "uptime": account_uptime(user["created_at"]),
        "repos": user["public_repos"],
        "stars": stars,
        "commits": commits,
        "followers": user["followers"],
        "languages": top_langs,
    }


ASCII = r"""
        _______  ______   _
       (  ___  )(  __  \ ( (    /|
       | (   ) || (  \  )|  \  ( |
       | (___) || |   ) ||   \ | |
       |  ___  || |   | || (\ \) |
       | (   ) || |   ) || | \   |
       | )   ( || (__/  )| )  \  |
       |/     \|(______/ |/    )_)
""".strip("\n")


def dots(label, value, width=76):
    pad = width - len(label) - len(str(value)) - 2
    return f"{label} {'.' * max(pad, 3)} {value}"


def render(s):
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"{USER}@github",
        "-" * 40,
        dots("OS:", "macOS, Linux"),
        dots("Uptime:", s["uptime"]),
        dots("Kernel:", "Software Engineer"),
        dots("IDE:", "Claude Code, VS Code"),
        "",
        dots("Languages:", s["languages"]),
        "",
        "- GitHub Stats",
        dots("Repos:", s["repos"]),
        dots("Stars:", s["stars"]),
        dots("Commits:", s["commits"]),
        dots("Followers:", s["followers"]),
        "",
        dots("Contact:", "adnvilla@gmail.com"),
    ]
    body = "\n".join(lines)
    return f"""# Hola, soy adnvilla 👋

```text
{ASCII}

{body}
```

Repo con las diferentes tecnologias que experimento.

<sub>Actualizado automáticamente: {updated}</sub>
"""


if __name__ == "__main__":
    readme = render(fetch_stats())
    path = os.path.join(os.path.dirname(__file__), "..", "README.md")
    with open(path, "w") as f:
        f.write(readme)
    print("README.md regenerado")
