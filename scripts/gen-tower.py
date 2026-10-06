#!/usr/bin/env python3
"""
Custom 3D contribution tower: purple-dominant isometric skyline with
language-colored tower tops, stats panel, dark backdrop.

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
MIXED_TOP = "#c4b5fd"

# 5 quartile purple shades for tower sides (dark -> light)
QUART = ["#2e1065", "#4c1d95", "#6d28d9", "#7c3aed", "#8b5cf6"]
BOUNDS = [10, 25, 50, 75]  # commits/day thresholds

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, monospace"


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": "tower-generator", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def fetch_contributions(user):
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
    weekly = {}
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


def quartile(n):
    for i, b in enumerate(BOUNDS):
        if n < b:
            return i
    return 4


def render(daily, week_lang, user):
    today = datetime.date.today()
    total = sum(daily.values())
    peak = max(daily.values()) if daily else 0
    streak = 0
    d = today
    while daily.get(d, 0) > 0:
        streak += 1
        d -= datetime.timedelta(days=1)

    last_sunday = today - datetime.timedelta(days=(today.weekday() + 1) % 7)
    first_sunday = last_sunday - datetime.timedelta(weeks=52)

    cells = []
    for i in range(53 * 7):
        dt = first_sunday + datetime.timedelta(days=i)
        if dt > today:
            continue
        w, dow = i // 7, i % 7
        n = daily.get(dt, 0)
        ws = (dt - datetime.timedelta(days=(dt.weekday() + 1) % 7)).isoformat()
        lang = week_lang.get(ws)
        top = LANG_COLORS.get(lang, MIXED_TOP) if n > 0 else None
        cells.append((w, dow, n, top))

    # iso projection: weeks recede into the distance (compressed), days come forward
    XW, YW, WK = 20, 9, 0.5
    CX, CY = 770, 150
    HS = 0.44  # cell half-size (chunky, small gaps)

    def h_of(n):
        return 0 if n == 0 else 8 + math.sqrt(n) * 12.5

    def pt(w, dow, z, fx=0.0, fy=0.0):
        return (CX + ((w + fx) * WK - (dow + fy)) * XW,
                CY + ((w + fx) * WK + (dow + fy)) * YW - z)

    W, H = 1200, 520
    P = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" role="img" aria-label="3d contribution tower">']
    P.append('<defs>'
             '<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
             '<stop offset="0" stop-color="#231239"/><stop offset="1" stop-color="#0e0718"/>'
             '</linearGradient>'
             '<radialGradient id="glow" cx="0.65" cy="0.55" r="0.5">'
             '<stop offset="0" stop-color="#7c3aed" stop-opacity="0.28"/>'
             '<stop offset="1" stop-color="#7c3aed" stop-opacity="0"/>'
             '</radialGradient>'
             '</defs>')
    P.append(f'<rect width="{W}" height="{H}" rx="18" fill="url(#bg)"/>')
    P.append(f'<rect width="{W}" height="{H}" rx="18" fill="url(#glow)"/>')

    # ---- left stats panel ----
    x0 = 56
    P.append(f'<text x="{x0}" y="72" font-family="{SANS}" font-size="30" font-weight="700" fill="#ffffff">Contribution skyline</text>')
    P.append(f'<text x="{x0}" y="100" font-family="{MONO}" font-size="12" letter-spacing="3" fill="#a78bfa">{today.year} · RENDERED NIGHTLY</text>')
    P.append(f'<line x1="{x0}" y1="124" x2="{x0+220}" y2="124" stroke="#3b2a5e" stroke-width="1"/>')
    P.append(f'<text x="{x0}" y="156" font-family="{MONO}" font-size="10" letter-spacing="2" fill="#8b7bb8">COMMITS PER DAY</text>')
    bx = x0
    for i, c in enumerate(QUART):
        P.append(f'<rect x="{bx}" y="168" width="30" height="14" rx="3" fill="{c}"/>')
        bx += 36
    P.append(f'<text x="{x0}" y="202" font-family="{MONO}" font-size="10" fill="#8b7bb8">under 10</text>')
    P.append(f'<text x="{x0+144}" y="202" font-family="{MONO}" font-size="10" fill="#8b7bb8" text-anchor="end">75+</text>')
    stats = [("TOTAL", f"{total:,}"), ("PEAK", str(peak)), ("STREAK", f"{streak}d")]
    sx = x0
    for label, val in stats:
        P.append(f'<text x="{sx}" y="248" font-family="{MONO}" font-size="10" letter-spacing="2" fill="#8b7bb8">{label}</text>')
        P.append(f'<text x="{sx}" y="276" font-family="{SANS}" font-size="24" font-weight="700" fill="#ffffff">{val}</text>')
        sx += 96
    # language legend
    P.append(f'<text x="{x0}" y="326" font-family="{MONO}" font-size="10" letter-spacing="2" fill="#8b7bb8">TOWER TOPS · LANGUAGE</text>')
    lx = x0
    for label, col in [("mixed", MIXED_TOP), ("TypeScript", "#3178c6"), ("C++", "#f34b7d"), ("C#", "#178600")]:
        P.append(f'<circle cx="{lx}" cy="348" r="6" fill="{col}"/>')
        P.append(f'<text x="{lx+14}" y="352" font-family="{MONO}" font-size="11" fill="#b8a8e0">{label}</text>')
        lx += 118 if label != "mixed" else 96

    # ---- towers ----
    # ground shadow
    P.append(f'<ellipse cx="{CX}" cy="452" rx="330" ry="30" fill="#000" opacity="0.4"/>')

    order = sorted(set(round(w * WK + dow, 2) for w, dow, _, _ in cells))
    for s in order:
        for (w, dow, n, top) in cells:
            if round(w * WK + dow, 2) != s:
                continue
            h = h_of(n)
            c = [pt(w, dow, 0, -HS, -HS), pt(w, dow, 0, HS, -HS),
                 pt(w, dow, 0, HS, HS), pt(w, dow, 0, -HS, HS)]
            (ax, ay), (bx_, by_), (cx_, cy_), (dx, dy) = c
            if h > 0:
                q = QUART[quartile(n)]
                t = [pt(w, dow, h, -HS, -HS), pt(w, dow, h, HS, -HS),
                     pt(w, dow, h, HS, HS), pt(w, dow, h, -HS, HS)]
                (ax2, ay2), (bx2, by2), (cx2, cy2), (dx2, dy2) = t
                # left face (darker)
                P.append(f'<polygon points="{dx:.1f},{dy:.1f} {cx_:.1f},{cy_:.1f} {cx2:.1f},{cy2:.1f} {dx2:.1f},{dy2:.1f}" fill="#1e0a3c"/>')
                # right face (quartile purple)
                P.append(f'<polygon points="{bx_:.1f},{by_:.1f} {cx_:.1f},{cy_:.1f} {cx2:.1f},{cy2:.1f} {bx2:.1f},{by2:.1f}" fill="{q}"/>')
                # top face (language color)
                P.append(f'<polygon points="{ax2:.1f},{ay2:.1f} {bx2:.1f},{by2:.1f} {cx2:.1f},{cy2:.1f} {dx2:.1f},{dy2:.1f}" fill="{top}" stroke="#ffffff" stroke-opacity="0.3" stroke-width="1"/>')
            else:
                P.append(f'<polygon points="{ax:.1f},{ay:.1f} {bx_:.1f},{by_:.1f} {cx_:.1f},{cy_:.1f} {dx:.1f},{dy:.1f}" fill="#1a0f2e" stroke="#ffffff" stroke-opacity="0.04"/>')

    P.append(f'<text x="{W-40}" y="{H-24}" font-family="{MONO}" font-size="10" letter-spacing="2" fill="#5b4a7a" text-anchor="end">rendered nightly · {user}</text>')
    P.append('</svg>')
    return "\n".join(P), dict(total=total, peak=peak, streak=streak)


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
    svg, stats = render(daily, week_lang, a.user)
    with open(a.out, "w") as f:
        f.write(svg)
    print("stats:", stats)
    print("wrote", a.out, f"({len(svg)//1024} KB)")


if __name__ == "__main__":
    main()
