#!/usr/bin/env python3
"""
Custom 3D contribution tower: purple-dominant towers with tops colored
by the week's dominant programming language.

Public data only. No token needed.
Usage: python3 scripts/gen-tower.py [--user wisnurafi] [--out profile-3d-contrib/tower-purple.svg]
"""
import argparse, datetime, json, math, re, sys, time, urllib.request

LANG_COLORS = {
    "TypeScript": "#3178c6",
    "C++": "#f34b7d",
    "C#": "#178600",
    "Python": "#3572a5",
    "Rust": "#dea584",
}
REPOS = ["My-Kait", "universal-runtime-analyzer", "cs2-hax",
         "win-memory-cleaner", "win-files", "pvz-hax"]
REPO_LANG = {"My-Kait": "TypeScript", "universal-runtime-analyzer": "C++",
             "cs2-hax": "C++", "win-memory-cleaner": "C#",
             "win-files": "C#", "pvz-hax": "C++"}
PURPLE_TOP = "#a78bfa"   # fallback when language unknown
LEFT_FACE = "#4c1d95"
RIGHT_FACE = "#6d28d9"


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": "tower-generator", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def fetch_contributions(user):
    """date -> count, from the public contributions calendar page."""
    html = get(f"https://github.com/users/{user}/contributions")
    tips = [t.strip() for t in re.findall(r'tool-tip[^>]*>\s*([^<]+?)\s*<', html) if t.strip()]
    months = {m: i + 1 for i, m in enumerate(
        ["January", "February", "March", "April", "May", "June",
         "July", "August", "September", "October", "November", "December"])}
    today = datetime.date.today()
    daily = {}
    for t in tips:
        m = re.match(r'(No|\d+)\s+contributions?\s+on\s+(\w+)\s+(\d+)\w*\.?', t)
        if not m or m.group(2) not in months:
            continue
        n = 0 if m.group(1) == "No" else int(m.group(1))
        mo, dy = months[m.group(2)], int(m.group(3))
        yr = today.year - 1 if (mo, dy) > (today.month, today.day) else today.year
        try:
            daily[datetime.date(yr, mo, dy)] = n
        except ValueError:
            pass
    return daily


def fetch_weekly_langs(user):
    """week_start_date -> dominant language, from per-repo commit activity."""
    weekly = {}  # date -> {lang: commits}
    for repo in REPOS:
        try:
            data = json.loads(get(
                f"https://api.github.com/repos/{user}/{repo}/stats/commit_activity"))
        except Exception as e:
            print(f"warn: {repo}: {e}", file=sys.stderr)
            continue
        if not isinstance(data, list):
            continue
        lang = REPO_LANG[repo]
        for w in data:
            try:
                ws = datetime.date.fromtimestamp(w["week"]).isoformat()
            except Exception:
                continue
            weekly.setdefault(ws, {}).setdefault(lang, 0)
            weekly[ws][lang] += sum(w["days"])
        time.sleep(1)
    dom = {}
    for ws, langs in weekly.items():
        if sum(langs.values()) > 0:
            dom[ws] = max(langs, key=langs.get)
    return dom


def render(daily, week_lang):
    today = datetime.date.today()
    last_sunday = today - datetime.timedelta(days=(today.weekday() + 1) % 7)
    first_sunday = last_sunday - datetime.timedelta(weeks=52)

    # cell data: (week_idx, day_idx, count, top_color)
    cells = []
    for i in range(53 * 7):
        d = first_sunday + datetime.timedelta(days=i)
        if d > today:
            continue
        w, dow = i // 7, i % 7
        n = daily.get(d, 0)
        ws = (d - datetime.timedelta(days=(d.weekday() + 1) % 7)).isoformat()
        lang = week_lang.get(ws)
        top = LANG_COLORS.get(lang, PURPLE_TOP) if n > 0 else None
        cells.append((w, dow, n, top))

    # iso projection params
    XW, YW, TOP = 13, 7.5, 5
    def h_of(n):
        return 0 if n == 0 else TOP + math.sqrt(n) * 11

    # bounds
    xs = [(w - dow) * XW for w, dow, _, _ in cells]
    max_h = max(h_of(n) for _, _, n, _ in cells)
    min_x, max_x = min(xs) - 14, max(xs) + 14
    max_y = max((w + dow) * YW for w, dow, _, _ in cells) + 30
    min_y = -max_h - 40
    W, H = max_x - min_x, max_y - min_y
    OX, OY = -min_x, -min_y

    def pt(w, dow, z):
        return (OX + (w - dow) * XW, OY + (w + dow) * YW - z)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
             f'viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="3d contribution tower">']
    parts.append('<defs><linearGradient id="side" x1="0" y1="0" x2="0" y2="1">'
                 f'<stop offset="0" stop-color="{RIGHT_FACE}"/><stop offset="1" stop-color="{LEFT_FACE}"/>'
                 '</linearGradient></defs>')

    # ground shadow ellipse
    parts.append(f'<ellipse cx="{W/2:.0f}" cy="{max_y - 14 + OY:.0f}" rx="{W*0.42:.0f}" ry="26" fill="#000" opacity="0.35"/>')

    # painter's order: back (small w+dow) to front
    for s in range(0, 60):
        for (w, dow, n, top) in cells:
            if w + dow != s:
                continue
            h = h_of(n)
            # base diamond corners (z=0) and top (z=h)
            ax, ay = pt(w - 0.5, dow - 0.5, 0)
            bx, by = pt(w + 0.5, dow - 0.5, 0)
            cx_, cy_ = pt(w + 0.5, dow + 0.5, 0)
            dx, dy = pt(w - 0.5, dow + 0.5, 0)
            if h > 0:
                ax2, ay2 = pt(w - 0.5, dow - 0.5, h)
                bx2, by2 = pt(w + 0.5, dow - 0.5, h)
                cx2, cy2 = pt(w + 0.5, dow + 0.5, h)
                dx2, dy2 = pt(w - 0.5, dow + 0.5, h)
                # left face (dx,dy -> cx,cy)
                parts.append(f'<polygon points="{dx:.1f},{dy:.1f} {cx_:.1f},{cy_:.1f} {cx2:.1f},{cy2:.1f} {dx2:.1f},{dy2:.1f}" fill="{LEFT_FACE}"/>')
                # right face (bx,by -> cx,cy)
                parts.append(f'<polygon points="{bx:.1f},{by:.1f} {cx_:.1f},{cy_:.1f} {cx2:.1f},{cy2:.1f} {bx2:.1f},{by2:.1f}" fill="url(#side)"/>')
                # top face: language color
                parts.append(f'<polygon points="{ax2:.1f},{ay2:.1f} {bx2:.1f},{by2:.1f} {cx2:.1f},{cy2:.1f} {dx2:.1f},{dy2:.1f}" fill="{top}" stroke="#ffffff" stroke-opacity="0.25" stroke-width="0.8"/>')
            else:
                parts.append(f'<polygon points="{ax:.1f},{ay:.1f} {bx:.1f},{by:.1f} {cx_:.1f},{cy_:.1f} {dx:.1f},{dy:.1f}" fill="#1a1030" stroke="#ffffff" stroke-opacity="0.05"/>')

    # legend
    lx, ly = 24, H - 34
    parts.append(f'<g font-family="monospace" font-size="12" fill="#8b949e">')
    parts.append(f'<circle cx="{lx}" cy="{ly}" r="5" fill="{PURPLE_TOP}"/><text x="{lx+12}" y="{ly+4}">mixed</text>')
    x = lx + 90
    for lang, col in [("TypeScript", "#3178c6"), ("C++", "#f34b7d"), ("C#", "#178600")]:
        parts.append(f'<circle cx="{x}" cy="{ly}" r="5" fill="{col}"/><text x="{x+12}" y="{ly+4}">{lang}</text>')
        x += 110
    parts.append('</g>')
    parts.append('</svg>')
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="wisnurafi")
    ap.add_argument("--out", default="profile-3d-contrib/tower-purple.svg")
    a = ap.parse_args()
    print("fetching contributions…")
    daily = fetch_contributions(a.user)
    print(f"{len(daily)} days, {sum(daily.values())} contributions")
    print("fetching weekly languages…")
    week_lang = fetch_weekly_langs(a.user)
    print(f"{len(week_lang)} weeks with language data")
    svg = render(daily, week_lang)
    with open(a.out, "w") as f:
        f.write(svg)
    print("wrote", a.out, f"({len(svg)//1024} KB)")


if __name__ == "__main__":
    main()
