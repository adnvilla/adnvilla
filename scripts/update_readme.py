#!/usr/bin/env python3
"""Regenera readme-dark.svg / readme-light.svg + README.md, estilo neofetch."""
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

USER = "adnvilla"
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN")
TZ = ZoneInfo("America/Mexico_City")
BIRTH = datetime(1988, 5, 14, 10, 30, tzinfo=TZ)

THEMES = {
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "label": "#ffa657",
        "dots": "#8b949e",
        "fg": "#c9d1d9",
        "accent": "#58a6ff",
        "green": "#3fb950",
        "red": "#f85149",
        "purple": "#a371f7",
    },
    "light": {
        "bg": "#ffffff",
        "border": "#d0d7de",
        "label": "#bc4c00",
        "dots": "#57606a",
        "fg": "#24292f",
        "accent": "#0969da",
        "green": "#1a7f37",
        "red": "#cf222e",
        "purple": "#8250df",
    },
}

INFO_W = 58  # ancho en caracteres de la columna de info


def _request(url, accept="application/vnd.github+json", data=None):
    req = urllib.request.Request(url, data=data, headers={"Accept": accept, "User-Agent": USER})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        return r.status, r.read()


def get(url, accept="application/vnd.github+json"):
    _, body = _request(url, accept)
    return json.loads(body)


def graphql(query):
    _, body = _request("https://api.github.com/graphql", data=json.dumps({"query": query}).encode())
    return json.loads(body)


def life_uptime():
    now = datetime.now(TZ)
    y = now.year - BIRTH.year
    m = now.month - BIRTH.month
    d = now.day - BIRTH.day
    hh = now.hour - BIRTH.hour
    mm = now.minute - BIRTH.minute
    if mm < 0:
        mm += 60
        hh -= 1
    if hh < 0:
        hh += 24
        d -= 1
    if d < 0:
        d += (now.replace(day=1) - timedelta(days=1)).day
        m -= 1
    if m < 0:
        m += 12
        y -= 1
    return f"{y} years, {m} months, {d} days, {hh} hours, {mm} min"


def contributors_stats(repo):
    """stats/contributors devuelve 202 mientras GitHub calcula; reintenta."""
    url = f"{API}/repos/{USER}/{repo}/stats/contributors"
    for _ in range(4):
        try:
            status, body = _request(url)
        except Exception:
            return []
        if status == 200 and body:
            return json.loads(body)
        time.sleep(2)
    return []


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
        commits = 0

    contributed = 0
    if TOKEN:
        try:
            q = f'{{ user(login: "{USER}") {{ repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST], first: 1) {{ totalCount }} }} }}'
            contributed = graphql(q)["data"]["user"]["repositoriesContributedTo"]["totalCount"]
        except Exception:
            pass

    additions = deletions = 0
    for r in repos:
        if r["fork"]:
            continue
        for c in contributors_stats(r["name"]):
            if c.get("author") and c["author"]["login"] == USER:
                for w in c["weeks"]:
                    additions += w["a"]
                    deletions += w["d"]

    def search_count(q):
        try:
            return get(f"{API}/search/issues?q={urllib.parse.quote(q)}")["total_count"]
        except Exception:
            return 0

    followup = {
        "issues_repos_open": search_count(f"user:{USER} is:issue is:open"),
        "issues_repos_closed": search_count(f"user:{USER} is:issue is:closed"),
        "issues_mine_open": search_count(f"author:{USER} is:issue is:open"),
        "issues_mine_closed": search_count(f"author:{USER} is:issue is:closed"),
        "prs_repos_open": search_count(f"user:{USER} is:pr is:open"),
        "prs_repos_closed": search_count(f"user:{USER} is:pr is:closed is:unmerged"),
        "prs_repos_merged": search_count(f"user:{USER} is:pr is:merged"),
        "prs_mine_open": search_count(f"author:{USER} is:pr is:open"),
        "prs_mine_closed": search_count(f"author:{USER} is:pr is:closed is:unmerged"),
        "prs_mine_merged": search_count(f"author:{USER} is:pr is:merged"),
    }

    langs = {}
    for r in repos:
        if r["language"]:
            langs[r["language"]] = langs.get(r["language"], 0) + 1
    top_langs = ", ".join(sorted(langs, key=langs.get, reverse=True)[:5])

    return {
        "repos": user["public_repos"],
        "contributed": contributed,
        "stars": stars,
        "commits": commits,
        "followers": user["followers"],
        "additions": additions,
        "deletions": deletions,
        "loc": additions - deletions,
        "languages": top_langs,
        **followup,
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


def seg_dots(P, label, value, width, value_color=None):
    value = str(value)
    pad = width - len(label) - len(value) - 2
    return [
        (label, P["label"]),
        (" " + "." * max(pad, 3) + " ", P["dots"]),
        (value, value_color or P["fg"]),
    ]


def seg_multi(P, label, parts, width):
    vlen = sum(len(t) for t, _ in parts)
    pad = width - len(label) - vlen - 2
    return [(label, P["label"]), (" " + "." * max(pad, 3) + " ", P["dots"])] + parts


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_lines(s, P):
    # Dos campos por línea: ancho izquierdo dinámico para que "|" quede alineado
    left_pairs = [("Repos:", f'{s["repos"]} {{Contributed: {s["contributed"]}}}'), ("Commits:", f'{s["commits"]:,}')]
    left_w = max(len(l) + len(v) + 5 for l, v in left_pairs)  # 2 espacios + min 3 dots
    right_w = INFO_W - left_w - 3
    sep = [(" | ", P["dots"])]
    lines = [
        [(f"{USER}@github ", P["accent"]), ("─" * (INFO_W - len(USER) - 8), P["dots"])],
        seg_dots(P, "OS:", "macOS, Linux", INFO_W),
        seg_dots(P, "Uptime:", life_uptime(), INFO_W),
        seg_dots(P, "Kernel:", "Works On My Machine™ Certified", INFO_W),
        seg_dots(P, "IDE:", "Claude Code, Cursor, Codex, VS Code", INFO_W),
        [],
        seg_dots(P, "Languages:", s["languages"], INFO_W),
        seg_dots(P, "Hobbies:", "Chess", INFO_W),
        [],
        [("─ Contact", P["accent"])],
        seg_dots(P, "Email:", "adnvilla@gmail.com", INFO_W),
        seg_dots(P, "Blog:", "adrianvillafana.com", INFO_W),
        seg_dots(P, "LinkedIn:", "in/adrian-villafaña", INFO_W),
        [],
        [("─ GitHub Stats", P["accent"])],
        seg_dots(P, *left_pairs[0], left_w) + sep + seg_dots(P, "Stars:", f'{s["stars"]:,}', right_w),
        seg_dots(P, *left_pairs[1], left_w) + sep + seg_dots(P, "Followers:", f'{s["followers"]:,}', right_w),
        seg_multi(P, "Issues on repos:", [
            (f'{s["issues_repos_open"]:,} open', P["green"]),
            (" / ", P["dots"]),
            (f'{s["issues_repos_closed"]:,} closed', P["purple"]),
        ], INFO_W),
        seg_multi(P, "Issues by me:", [
            (f'{s["issues_mine_open"]:,} open', P["green"]),
            (" / ", P["dots"]),
            (f'{s["issues_mine_closed"]:,} closed', P["purple"]),
        ], INFO_W),
        seg_multi(P, "PRs on repos:", [
            (f'{s["prs_repos_open"]:,} open', P["green"]),
            (" / ", P["dots"]),
            (f'{s["prs_repos_closed"]:,} closed', P["red"]),
            (" / ", P["dots"]),
            (f'{s["prs_repos_merged"]:,} merged', P["purple"]),
        ], INFO_W),
        seg_multi(P, "PRs by me:", [
            (f'{s["prs_mine_open"]:,} open', P["green"]),
            (" / ", P["dots"]),
            (f'{s["prs_mine_closed"]:,} closed', P["red"]),
            (" / ", P["dots"]),
            (f'{s["prs_mine_merged"]:,} merged', P["purple"]),
        ], INFO_W),
        [
            ("Lines of Code: ", P["label"]),
            (f'{s["loc"]:,} ', P["fg"]),
            ("( ", P["dots"]),
            (f'{s["additions"]:,}++', P["green"]),
            (", ", P["dots"]),
            (f'{s["deletions"]:,}--', P["red"]),
            (" )", P["dots"]),
        ],
    ]
    return lines


def render_svg(s, theme):
    P = THEMES[theme]
    char_w = 8.6
    line_h = 20
    art_lines = ASCII.split("\n")
    art_w = max(len(l) for l in art_lines)
    art_x = 28
    info_x = art_x + int(art_w * char_w) + 40
    width = info_x + int(INFO_W * char_w) + 34

    info = build_lines(s, P)
    top = 40
    height = top + len(info) * line_h + 24
    art_top = top + ((len(info) - len(art_lines)) * line_h) // 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>text { font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 14px; }</style>",
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" fill="{P["bg"]}" stroke="{P["border"]}"/>',
    ]
    for i, line in enumerate(art_lines):
        parts.append(
            f'<text x="{art_x}" y="{art_top + i * line_h}" xml:space="preserve" fill="{P["accent"]}">{esc(line)}</text>'
        )
    for i, segments in enumerate(info):
        if not segments:
            continue
        tspans = "".join(f'<tspan fill="{c}">{esc(t)}</tspan>' for t, c in segments)
        parts.append(f'<text x="{info_x}" y="{top + i * line_h}" xml:space="preserve">{tspans}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


README_TEMPLATE = """<a href="https://adrianvillafana.com/">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="readme-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="readme-light.svg">
    <img src="readme-dark.svg" alt="adnvilla" width="900">
  </picture>
</a>
"""


if __name__ == "__main__":
    root = os.path.join(os.path.dirname(__file__), "..")
    stats = fetch_stats()
    for theme in THEMES:
        with open(os.path.join(root, f"readme-{theme}.svg"), "w") as f:
            f.write(render_svg(stats, theme))
    with open(os.path.join(root, "README.md"), "w") as f:
        f.write(README_TEMPLATE)
    print("readme-dark.svg + readme-light.svg + README.md regenerados")
