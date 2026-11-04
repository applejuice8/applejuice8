"""Animated contribution heatmap as a self-contained SVG.

Reads the contribution calendar from the GitHub GraphQL API and writes
assets/ascii/contrib-heatmap.svg. Uses only the standard library.

    GITHUB_TOKEN=... GH_USER=applejuice8 python make_heatmap.py
    STATIC=1 ...  # no animation (for static previews)

If GITHUB_TOKEN is not set, it falls back to `gh auth token` (GitHub CLI).
"""

import datetime
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

USER = os.environ.get("GH_USER") or os.environ.get("USERNAME") or "applejuice8"
STATIC = bool(os.environ.get("STATIC"))
OUT = Path(__file__).resolve().parents[2] / "assets/ascii/contrib-heatmap.svg"

# Intensity colors, dark to bright (purple accent)
LEVELS = {
    "NONE": "#161b22",
    "FIRST_QUARTILE": "#3b2f73",
    "SECOND_QUARTILE": "#5b45b0",
    "THIRD_QUARTILE": "#7d62e0",
    "FOURTH_QUARTILE": "#a78bfa",
}

CELL, GAP = 12, 3
LEFT, TOP = 40, 74
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel weekday } }
      }
    }
  }
}
"""


def get_token():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def fetch_calendar():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    headers = {"Authorization": f"bearer {get_token()}", "Content-Type": "application/json"}
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
    except urllib.error.URLError:
        # Some local Python installs lack SSL certificates; curl does not.
        out = subprocess.check_output(
            ["curl", "-sf", "--max-time", "60", "-X", "POST", "https://api.github.com/graphql",
             "-H", f"Authorization: bearer {get_token()}", "-H", "Content-Type: application/json",
             "--data-binary", "@-"],
            input=body,
        )
        data = json.loads(out)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def render(calendar):
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]
    width = LEFT + len(weeks) * (CELL + GAP) + 20
    height = TOP + 7 * (CELL + GAP) + 44

    cells, months = [], []
    last_month = None
    for wi, week in enumerate(weeks):
        x = LEFT + wi * (CELL + GAP)
        first = datetime.date.fromisoformat(week["contributionDays"][0]["date"])
        if first.month != last_month and first.day <= 14:
            months.append(f'<text x="{x}" y="{TOP - 10}" class="m">{first.strftime("%b")}</text>')
            last_month = first.month
        for day in week["contributionDays"]:
            y = TOP + day["weekday"] * (CELL + GAP)
            color = LEVELS.get(day["contributionLevel"], LEVELS["NONE"])
            delay = wi * 0.018 + day["weekday"] * 0.012
            style = "" if STATIC else f' style="animation-delay:{delay:.3f}s"'
            cls = "x" if STATIC else "c"
            count = day["contributionCount"]
            cells.append(
                f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                f'fill="{color}"{style}><title>{count} on {day["date"]}</title></rect>'
            )

    day_labels = "".join(
        f'<text x="{LEFT - 8}" y="{TOP + i * (CELL + GAP) + 10}" class="m" text-anchor="end">{name}</text>'
        for i, name in ((1, "Mon"), (3, "Wed"), (5, "Fri"))
    )

    lx = width - 20 - 5 * (CELL + GAP) - 70
    legend = f'<text x="{lx}" y="{height - 14}" class="m" text-anchor="end">Less</text>' + "".join(
        f'<rect x="{lx + 8 + i * (CELL + GAP)}" y="{height - 24}" width="{CELL}" height="{CELL}" rx="2" fill="{c}"/>'
        for i, c in enumerate(LEVELS.values())
    ) + f'<text x="{lx + 8 + 5 * (CELL + GAP) + 4}" y="{height - 14}" class="m">More</text>'

    css = f"""
    .t{{font:600 15px {FONT};fill:#c9d1d9}}
    .s{{font:12px {FONT};fill:#8b949e}}
    .m{{font:11px {FONT};fill:#8b949e}}
    .c{{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .4s ease-out forwards}}
    @keyframes pop{{0%{{opacity:0;transform:scale(.2)}}100%{{opacity:1;transform:scale(1)}}}}
    @media (prefers-reduced-motion:reduce){{.c{{animation:none;opacity:1}}}}
    """
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{USER} GitHub contribution heatmap">'
        f"<title>{USER}: {total} contributions in the last year</title>"
        f"<style>{css}</style>"
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" fill="#0d1117" stroke="#30363d"/>'
        f'<text x="{LEFT}" y="26" class="t">{USER}@github</text>'
        f'<text x="{LEFT}" y="42" class="s">{total:,} contributions in the last year</text>'
        + "".join(months) + day_labels + "".join(cells) + legend + "</svg>"
    )


if __name__ == "__main__":
    svg = render(fetch_calendar())
    OUT.write_text(svg, encoding="utf-8")
    print(f"Wrote {OUT} ({len(svg):,} bytes)")
