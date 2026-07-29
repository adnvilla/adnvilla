#!/usr/bin/env python3
"""Regenera readme.svg + README.md con stats de GitHub, estilo neofetch con colores."""
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

USER = "adnvilla"
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN")
TZ = ZoneInfo("America/Mexico_City")
BIRTH = datetime(1988, 5, 14, 10, 30, tzinfo=TZ)

# Paleta (GitHub dark)
BG = "#0d1117"
BORDER = "#30363d"
ORANGE = "#ffa657"
GRAY = "#8b949e"
FG = "#c9d1d9"
BLUE = "#58a6ff"
GREEN = "#3fb950"
RED = "#f85149"

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


def seg_dots(label, value, width, value_color=FG):
    value = str(value)
    pad = width - len(label) - len(value) - 2
    return [
        (label, ORANGE),
        (" " + "." * max(pad, 3) + " ", GRAY),
        (value, value_color),
    ]


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_lines(s):
    half = (INFO_W - 3) // 2  # dos campos por línea: "A | B"
    sep = [(" | ", GRAY)]
    lines = [
        [(f"{USER}@github ", BLUE), ("─" * (INFO_W - len(USER) - 8), GRAY)],
        seg_dots("OS:", "macOS, Linux", INFO_W),
        seg_dots("Uptime:", life_uptime(), INFO_W),
        seg_dots("Kernel:", "Works On My Machine™ Certified", INFO_W),
        seg_dots("IDE:", "Claude Code, VS Code", INFO_W),
        [],
        seg_dots("Languages:", s["languages"], INFO_W),
        seg_dots("Hobbies:", "Ajedrez", INFO_W),
        [],
        [("─ Contact", BLUE)],
        seg_dots("Email:", "adnvilla@gmail.com", INFO_W),
        seg_dots("Blog:", "adrianvillafana.com", INFO_W),
        seg_dots("LinkedIn:", "in/adrian-villafaña", INFO_W),
        [],
        [("─ GitHub Stats", BLUE)],
        seg_dots("Repos:", f'{s["repos"]} {{Contributed: {s["contributed"]}}}', half)
        + sep
        + seg_dots("Stars:", f'{s["stars"]:,}', half),
        seg_dots("Commits:", f'{s["commits"]:,}', half)
        + sep
        + seg_dots("Followers:", f'{s["followers"]:,}', half),
        [
            ("Lines of Code: ", ORANGE),
            (f'{s["loc"]:,} ', FG),
            ("( ", GRAY),
            (f'{s["additions"]:,}++', GREEN),
            (", ", GRAY),
            (f'{s["deletions"]:,}--', RED),
            (" )", GRAY),
        ],
    ]
    return lines


def render_svg(s):
    char_w = 8.43
    line_h = 20
    art_lines = ASCII.split("\n")
    art_w = max(len(l) for l in art_lines)
    art_x = 28
    info_x = art_x + int(art_w * char_w) + 40
    width = info_x + int(INFO_W * char_w) + 28

    info = build_lines(s)
    top = 40
    height = top + len(info) * line_h + 24
    art_top = top + ((len(info) - len(art_lines)) * line_h) // 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>text { font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 14px; }</style>",
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" fill="{BG}" stroke="{BORDER}"/>',
    ]
    for i, line in enumerate(art_lines):
        parts.append(
            f'<text x="{art_x}" y="{art_top + i * line_h}" xml:space="preserve" fill="{BLUE}">{esc(line)}</text>'
        )
    for i, segments in enumerate(info):
        if not segments:
            continue
        tspans = "".join(f'<tspan fill="{c}">{esc(t)}</tspan>' for t, c in segments)
        parts.append(f'<text x="{info_x}" y="{top + i * line_h}" xml:space="preserve">{tspans}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


README_TEMPLATE = """# Hola, soy adnvilla 👋

<img src="readme.svg" alt="adnvilla" width="900"/>

📝 [Blog](https://adrianvillafana.com/) · 💼 [LinkedIn](https://www.linkedin.com/in/adrian-villafa%C3%B1a/) · ✉️ adnvilla@gmail.com

Repo con las diferentes tecnologias que experimento.

<sub>Actualizado automáticamente: {updated}</sub>
"""


if __name__ == "__main__":
    root = os.path.join(os.path.dirname(__file__), "..")
    stats = fetch_stats()
    with open(os.path.join(root, "readme.svg"), "w") as f:
        f.write(render_svg(stats))
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open(os.path.join(root, "README.md"), "w") as f:
        f.write(README_TEMPLATE.format(updated=updated))
    print("readme.svg + README.md regenerados")
