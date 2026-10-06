#!/usr/bin/env python3
"""
wisnu — terminal profile promo.

A looping terminal sequence in the spirit of guilyx's profile promo:
CRT power-on, an ssh handshake that answers `whoami` with the identity card,
one true joke, an operation tree being ticked, attack paths being mapped,
the path so far, and a sign-off.

Palette and pacing follow the same school: near-black ground, one saturated
accent spent once per scene, and frame holds derived from how much text the
frame carries rather than hand-tuned.

Deps: pillow >= 10
Run:  python3 assets/promo/generate.py
"""

from __future__ import annotations

import math
import os
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

# --------------------------------------------------------------------------
# Canvas
# --------------------------------------------------------------------------

W, H = 880, 440
SS = 2
EXPORT = int(os.environ.get("PROMO_EXPORT", "2"))
DS = SS * EXPORT
FW, FH = W * DS, H * DS
OW, OH = W * EXPORT, H * EXPORT
Q = int(os.environ.get("PROMO_Q", "2"))

MOTION_MS = 40
READ_MS = 50
HOLD_SCALE = 1.95
INK_REF = 95.0
INK_MIN, INK_MAX = 0.8, 1.7


def read_time(chars: int) -> float:
    return max(INK_MIN, min(INK_MAX, chars / INK_REF))


HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "wisnu-terminal.gif")

RNG = random.Random(7)


def S(v: float) -> float:
    return v * DS


# --------------------------------------------------------------------------
# Palette — near-black ground, one saturated accent
# --------------------------------------------------------------------------

BG      = (0x0d, 0x0e, 0x12)
RAISED  = (0x15, 0x17, 0x1d)
LINE    = (0x25, 0x28, 0x33)
FAINT   = (0x55, 0x5b, 0x69)
MUTED   = (0x7c, 0x82, 0x91)
BODY    = (0xa5, 0xaa, 0xb8)
HEADING = (0xe4, 0xe6, 0xec)
ACCENT  = (0x8b, 0x95, 0xf0)
WHITE   = (0xff, 0xff, 0xff)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def fade(c, t):
    return mix(BG, c, t)


def ramp(a, b, n):
    return [mix(a, b, k / (n - 1)) for k in range(n)]


def brand_colours():
    cols: list[tuple[int, int, int]] = []
    cols += ramp((0, 0, 0), BG, 4)
    cols += ramp(BG, LINE, 6)
    cols += ramp(LINE, FAINT, 5)
    cols += ramp(FAINT, MUTED, 5)
    cols += ramp(MUTED, BODY, 4)
    cols += ramp(BODY, HEADING, 5)
    cols += ramp(HEADING, WHITE, 3)
    cols += ramp(BG, ACCENT, 12)
    cols += ramp(ACCENT, (0xd6, 0xdb, 0xff), 5)
    cols += ramp(mix(BG, HEADING, 0.5), WHITE, 20)
    cols += ramp(mix(BG, mix(HEADING, BODY, 0.35), 0.5),
                 mix(HEADING, BODY, 0.35), 10)
    cols += [RAISED, ACCENT, HEADING, MUTED, FAINT, LINE, BG, WHITE]
    return cols


def build_palette(frames_rgb):
    seen: dict[tuple[int, int, int], int] = {}
    for fr in frames_rgb[::4]:
        small = fr.resize((220, 110), Image.BILINEAR)
        for px in small.getdata():
            seen[px] = seen.get(px, 0) + 1
    top = [c for c, _ in sorted(seen.items(), key=lambda kv: -kv[1])[:150]]
    pal = top + [c for c in brand_colours() if c not in top]
    pal = pal[:256]
    while len(pal) < 256:
        pal.append((0, 0, 0))
    pimg = Image.new("P", (1, 1))
    flat = [v for c in pal for v in c]
    pimg.putpalette(flat)
    return pimg


# --------------------------------------------------------------------------
# Type
# --------------------------------------------------------------------------

MONO_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
DISP_PATH = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
DISP_REG_PATH = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def font(path, size):
    return ImageFont.truetype(path, int(round(size * DS)))


F_MONO_XS = font(MONO_PATH, 10)
F_MONO_S = font(MONO_PATH, 12)
F_MONO = font(MONO_PATH, 13.5)
F_MONO_B = font(MONO_BOLD_PATH, 13.5)
F_MONO_L = font(MONO_PATH, 17)
F_MONO_XL = font(MONO_BOLD_PATH, 30)
F_DISP_XL = font(DISP_PATH, 54)
F_DISP_M = font(DISP_REG_PATH, 21)


def cw(f) -> float:
    return f.getlength("M") / DS


CW = cw(F_MONO)
LH = 19.0

_ink = 0
_reading = True
_INK_FLOOR = 60


def _legible(fill) -> bool:
    return sum(fill) / 3.0 >= _INK_FLOOR


def ink() -> int:
    return _ink


def reset_ink() -> None:
    global _ink
    _ink = 0


def text(d, x, y, s, f, fill, anchor="la"):
    global _ink
    if _reading and _legible(fill):
        _ink += len(s.strip())
    d.text((S(x), S(y)), s, font=f, fill=fill, anchor=anchor)


def text_w(s, f) -> float:
    return f.getlength(s) / DS


def ctext(d, cx, y, s, f, fill):
    global _ink
    if _reading and _legible(fill):
        _ink += len(s.strip())
    d.text((S(cx), S(y)), s, font=f, fill=fill, anchor="ma")


# --------------------------------------------------------------------------
# Motion helpers
# --------------------------------------------------------------------------

def clamp01(t):
    return max(0.0, min(1.0, t))


def ease_out(t):
    t = clamp01(t)
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = clamp01(t)
    return t * t * (3 - 2 * t)


def seg(frame, start, length):
    return clamp01((frame - start) / length)


CPS = 1.7


def _cursor(d, x, y, f, alpha=0.85):
    if int(f * 2.2) % 2 == 0:
        cwx = cw(F_MONO)
        d.rectangle([S(x), S(y + 1), S(x + cwx * 0.62), S(y + 15)],
                    fill=fade(HEADING, alpha))

# --------------------------------------------------------------------------
# Rain — monochrome cascade, bright heads falling into the hairline
# --------------------------------------------------------------------------

GLYPHS = list("0123456789ABCDEF")


class Rain:
    COL_W = 17.0
    TRAIL = 13

    def __init__(self, rng):
        self.rng = rng
        self.ncols = int(W / self.COL_W) + 1
        self.y = [rng.uniform(-H, 0) for _ in range(self.ncols)]
        self.speed = [rng.uniform(1.8, 5.0) for _ in range(self.ncols)]
        self.on = [rng.random() < 0.5 for _ in range(self.ncols)]
        self.chars = [
            [rng.choice(GLYPHS) for _ in range(self.TRAIL)] for _ in range(self.ncols)
        ]

    def step(self, dt=1.0):
        for i in range(self.ncols):
            self.y[i] += self.speed[i] * dt
            if self.y[i] > H + self.TRAIL * LH:
                self.y[i] = self.rng.uniform(-H * 0.6, -20)
                self.speed[i] = self.rng.uniform(1.8, 5.0)
                self.on[i] = self.rng.random() < 0.6
            if self.rng.random() < 0.06 * dt:
                self.chars[i][self.rng.randrange(self.TRAIL)] = self.rng.choice(GLYPHS)

    def draw(self, d, k):
        global _reading
        if k <= 0.01:
            return
        _reading = False
        try:
            for i in range(self.ncols):
                if not self.on[i]:
                    continue
                x = i * self.COL_W
                for j in range(self.TRAIL):
                    y = self.y[i] - j * LH
                    if y < -LH or y > H:
                        continue
                    f = (1 - j / self.TRAIL) ** 1.7
                    if j == 0:
                        col = fade(BODY, 0.95 * k)
                    elif j < 3:
                        col = fade(MUTED, f * k)
                    else:
                        col = fade(FAINT, f * 0.9 * k)
                    if col == BG:
                        continue
                    text(d, x, y, self.chars[i][j], F_MONO_S, col)
        finally:
            _reading = True


# --------------------------------------------------------------------------
# Operation tree — real tick semantics. A fallback returns as soon as one
# child succeeds, so `pivot` is never reached: `recon ok` wins first.
# --------------------------------------------------------------------------

BT_H = 24.0

BT_NODES = {
    "root":    (440.0, 100.0, "\u2192", "sequence"),
    "guard":   (270.0, 172.0, "?", "fallback"),
    "run":     (610.0, 172.0, "\u21c9", "parallel"),
    "recon":   (185.0, 244.0, "\u25cb", "recon ok"),
    "pivot":   (355.0, 244.0, "\u25b8", "pivot"),
    "access":  (525.0, 244.0, "\u25b8", "initial access"),
    "persist": (695.0, 244.0, "\u25b8", "persist"),
}

BT_EDGES = [
    ("root", "guard"), ("root", "run"),
    ("guard", "recon"), ("guard", "pivot"),
    ("run", "access"), ("run", "persist"),
]

BT_TICK = [
    ("root", 18, "running"),
    ("guard", 20, "success"),
    ("recon", 22, "success"),
    ("guard", 24, "success"),
    ("run", 26, "running"),
    ("access", 28, "running"),
    ("persist", 30, "running"),
]

BT_LEVEL = {"root": 0, "guard": 1, "run": 1,
            "recon": 2, "pivot": 2, "access": 2, "persist": 2}


def bt_status(node, t):
    out = "idle"
    for name, frame, status in BT_TICK:
        if name == node and t >= frame:
            out = status
    return out


def bt_node_box(node):
    x, y, glyph, label = BT_NODES[node]
    w = text_w(f"{glyph} {label}", F_MONO_XS) + 20.0
    return x - w / 2, y - BT_H / 2, x + w / 2, y + BT_H / 2


def draw_bt_node(d, node, t, k):
    if k <= 0.01:
        return
    x, y, glyph, label = BT_NODES[node]
    x0, y0, x1, y1 = bt_node_box(node)
    st = bt_status(node, t)
    if st == "running":
        border, inkc = ACCENT, HEADING
    elif st == "success":
        border, inkc = MUTED, BODY
    else:
        border, inkc = LINE, FAINT
    d.rounded_rectangle([S(x0), S(y0), S(x1), S(y1)], radius=S(3),
                        fill=fade(RAISED, k * 0.9), outline=fade(border, k),
                        width=max(1, int(S(1))))
    text(d, x, y - 5.5, f"{glyph} {label}", F_MONO_XS, fade(inkc, k), anchor="ma")


def draw_bt_edge(d, parent, child, t, k):
    if k <= 0.01:
        return
    px, py, _, _ = BT_NODES[parent]
    cx, cy, _, _ = BT_NODES[child]
    top = cy - BT_H / 2
    bot = py + BT_H / 2
    mid = (bot + top) / 2
    st = bt_status(child, t)
    col = ACCENT if st == "running" else (MUTED if st == "success" else LINE)
    strength = k * (1.0 if st != "idle" else 0.85)
    d.line([S(px), S(bot), S(px), S(mid), S(cx), S(mid), S(cx), S(top)],
           fill=fade(col, strength), width=max(1, int(S(1))), joint="curve")


# --------------------------------------------------------------------------
# Attack graph — every path is a hypothesis until it is walked
# --------------------------------------------------------------------------

AG_NODES = [
    ("recon",    130.0, 150.0),
    ("initial",  330.0, 200.0),
    ("persist",  530.0, 140.0),
    ("lateral",  530.0, 260.0),
    ("exfil",    730.0, 200.0),
]
AG_EDGES = [
    ("recon", "initial"),
    ("initial", "persist"),
    ("initial", "lateral"),
    ("persist", "exfil"),
    ("lateral", "exfil"),
]
AG_PATH = ["recon", "initial", "lateral", "exfil"]  # the walked path
AG_H = 24.0


def ag_box(name):
    x, y = next((xx, yy) for n, xx, yy in AG_NODES if n == name)
    w = text_w(name, F_MONO_XS) + 20.0
    return x - w / 2, y - AG_H / 2, x + w / 2, y + AG_H / 2, x, y


def draw_graph(d, t, k):
    if k <= 0.01:
        return
    pos = {n: (x, y) for n, x, y in AG_NODES}
    # edges first, path edges in accent once walked
    for ei, (a, b) in enumerate(AG_EDGES):
        ek = ease_out(seg(t, 5 + ei * 2.5, 5))
        if ek <= 0.01:
            continue
        ax, ay = pos[a]
        bx, by = pos[b]
        on_path = AG_PATH.index(a) + 1 == AG_PATH.index(b) if a in AG_PATH and b in AG_PATH else False
        if on_path:
            wk = ease_out(seg(t, 10 + AG_PATH.index(b) * 4, 5))
            col = fade(ACCENT, ek * wk)
        else:
            col = fade(LINE, ek * 0.9)
        d.line([S(ax), S(ay), S(bx), S(by)], fill=col,
               width=max(1, int(S(1))), joint="curve")
    for ni, (name, x, y) in enumerate(AG_NODES):
        nk = ease_out(seg(t, 3 + ni * 2, 5))
        if nk <= 0.01:
            continue
        x0, y0, x1, y1, cx, cy = ag_box(name)
        hot = name in AG_PATH and ease_out(seg(t, 10 + AG_PATH.index(name) * 4, 4)) > 0.5
        border = ACCENT if hot else LINE
        inkc = HEADING if hot else FAINT
        d.rounded_rectangle([S(x0), S(y0), S(x1), S(y1)], radius=S(3),
                            fill=fade(RAISED, nk * 0.9), outline=fade(border, nk),
                            width=max(1, int(S(1))))
        text(d, cx, cy - 5.5, name, F_MONO_XS, fade(inkc, nk), anchor="ma")


# --------------------------------------------------------------------------
# Mark — a hex sigil for the sign-off
# --------------------------------------------------------------------------

def draw_mark(d, cx, cy, size, k=1.0):
    if k <= 0.01:
        return
    pts = []
    for i in range(6):
        a = math.pi / 3 * i - math.pi / 6
        pts.append((cx + size / 2 * math.cos(a), cy + size / 2 * math.sin(a)))
    sp = [(S(x), S(y)) for x, y in pts]
    d.polygon(sp, outline=fade(ACCENT, k), width=max(1, int(S(1.6))))
    inner = [(S(cx + (x - cx) * 0.55), S(cy + (y - cy) * 0.55)) for x, y in pts]
    d.polygon(inner, outline=fade(LINE, k), width=max(1, int(S(1))))
    text(d, cx, cy - 9, "w", F_MONO_B, fade(HEADING, k), anchor="ma")


# --------------------------------------------------------------------------
# Chrome
# --------------------------------------------------------------------------

def corner_ticks(d, k, inset=16.0, arm=26.0):
    col = fade(LINE, k)
    if col == BG:
        return
    wpx = max(1, int(S(1)))
    for cx, cy, sx, sy in ((inset, inset, 1, 1), (W - inset, inset, -1, 1),
                           (inset, H - inset, 1, -1), (W - inset, H - inset, -1, -1)):
        d.line([S(cx), S(cy), S(cx + sx * arm), S(cy)], fill=col, width=wpx)
        d.line([S(cx), S(cy), S(cx), S(cy + sy * arm)], fill=col, width=wpx)


def status_bar(d, k, label, right="rafiprofile.my.id"):
    col = fade(LINE, k * 0.9)
    if col != BG:
        d.line([S(28), S(H - 30), S(W - 28), S(H - 30)], fill=col,
               width=max(1, int(S(1))))
    text(d, 28, H - 24, label, F_MONO_XS, fade(FAINT, k))
    text(d, W - 28, H - 24, right, F_MONO_XS, fade(FAINT, k), anchor="ra")


# --------------------------------------------------------------------------
# Post-processing
# --------------------------------------------------------------------------

def bloom(img, radius=7 * EXPORT, strength=0.55):
    small = img.resize((FW // 4, FH // 4), Image.BILINEAR)
    small = ImageChops.subtract(small, Image.new("RGB", small.size, (46, 46, 46)))
    small = small.filter(ImageFilter.GaussianBlur(radius))
    up = small.resize((FW, FH), Image.BILINEAR)
    up = up.point(lambda v: int(v * strength))
    return ImageChops.screen(img, up)


def build_screen_mask():
    m = Image.new("L", (OW, OH), 255)
    px = m.load()
    cx, cy = OW / 2.0, OH / 2.0
    maxd = math.hypot(cx, cy)
    for y in range(OH):
        scan = 0.88 if ((y // EXPORT) % 2) else 1.0
        for x in range(OW):
            dd = math.hypot(x - cx, y - cy) / maxd
            vig = 1.0 - 0.14 * (dd ** 2.0)
            px[x, y] = max(0, min(255, int(255 * scan * vig)))
    return Image.merge("RGB", (m, m, m))


def build_scanline_mask():
    m = Image.new("L", (OW, OH), 255)
    px = m.load()
    for y in range(OH):
        v = 214 if ((y // EXPORT) % 2) else 255
        for x in range(OW):
            px[x, y] = v
    return Image.merge("RGB", (m, m, m))


SCREEN_MASK = build_screen_mask()
SCANLINE_MASK = build_scanline_mask()


def slice_glitch(img, amount, rng, band=14 * DS // 2):
    if amount <= 0:
        return img
    out = img.copy()
    y = 0
    while y < FH:
        h = rng.randint(band, band * 4)
        if rng.random() < 0.45:
            dx = int(rng.uniform(-amount, amount) * DS)
            if dx:
                box = (0, y, FW, min(FH, y + h))
                strip = img.crop(box)
                out.paste(strip, (dx, y))
        y += h
    if amount > 4:
        r, g, b = out.split()
        off = int(max(1, amount * 0.25) * DS)
        r = ImageChops.offset(r, off, 0)
        b = ImageChops.offset(b, -off, 0)
        out = Image.merge("RGB", (r, g, b))
    return out

# --------------------------------------------------------------------------
# Content — every string traces back to the profile README or rafiprofile.my.id
# --------------------------------------------------------------------------

TERM_LINES = [
    (0,  0, [("wisnu", MUTED), (" on ", FAINT), ("main", MUTED),
             (" [!?] ", FAINT), ("took 8s", FAINT)], False),
    (2,  0, [("\u2192 ", ACCENT), ("ssh wisnu@10.13.37.7", BODY)], True),
    (17, 1, [("handshake ", FAINT), ("\u00b7" * 14, LINE), (" ok", BODY)], False),
    (20, 1, [("locale ", FAINT), ("\u00b7" * 17, LINE),
             (" jakarta, id \u00b7 utc+07", BODY)], False),
    (22, 0, [("\u2192 ", ACCENT), ("whoami", BODY)], True),
]

JOKE_LINES = [
    (0,  0, [("wisnu", MUTED), (" on ", FAINT), ("main", MUTED),
             (" [!?]", FAINT)], False),
    (2,  0, [("\u2192 ", ACCENT), ("write secure code", BODY)], True),
    (15, 1, [("there is no secure code.", BODY)], False),
    (18, 1, [("only code nobody has audited yet.", MUTED)], False),
]

SPEC = [
    ("role", "systems software engineer \u00b7 offensive security"),
    ("based", "jakarta, id"),
    ("building", "windows internals \u00b7 binary analysis"),
    ("also", "game security research"),
]

PATH_STOPS = [
    ("independent", "penetration tester"),
    ("game security", "client integrity \u00b7 re"),
    ("beyondsoft sg", "systems software engineer"),
    ("private clients", "offensive security"),
]


def draw_terminal(d, f, t, lines, y0=74.0, tail_from=None):
    x0 = 54.0
    last_x = last_y = None
    for row, (start, indent, segments, typed) in enumerate(lines):
        if t < start:
            continue
        y = y0 + row * (LH + 4)
        x = x0 + indent * CW * 2
        full = "".join(s for s, _ in segments)
        n = int((t - start) * CPS) if typed else len(full)
        if n <= 0:
            continue
        used = 0
        for s, col in segments:
            if used >= n:
                break
            take = min(len(s), n - used)
            text(d, x + used * CW, y, s[:take], F_MONO, fade(col, 1.0))
            used += take
        last_x, last_y = x + used * CW, y
        if typed and used < len(full):
            _cursor(d, x + used * CW, y, f, 0.8)
            return
    if tail_from is not None and t >= tail_from and last_x is not None:
        _cursor(d, last_x, last_y, f, 0.9)


# --------------------------------------------------------------------------
# Timeline
# --------------------------------------------------------------------------

T_POWER = 0
T_TERM = 11
T_ID = 33
T_JOKE = 56
T_TREE = 78
T_GRAPH = 114
T_PATH = 144
T_SIGN = 166
T_END = 185

CUTS = (T_ID, T_JOKE, T_TREE, T_GRAPH, T_PATH, T_SIGN)

HOLD_MS = {
    T_ID - 2: 400, T_ID - 1: 400,
    T_JOKE - 3: 380, T_JOKE - 2: 380, T_JOKE - 1: 380,
    T_JOKE + 16: 460, T_JOKE + 17: 460,
    T_TREE - 3: 480, T_TREE - 2: 480, T_TREE - 1: 480,
    T_GRAPH - 2: 480, T_GRAPH - 1: 480,
    T_PATH - 2: 480, T_PATH - 1: 480,
    T_SIGN - 2: 400, T_SIGN - 1: 400,
    T_END - 7: 480, T_END - 6: 480,
}


# --------------------------------------------------------------------------
# Scenes
# --------------------------------------------------------------------------

def scene_power(d, f):
    """CRT power-on: a bright line opens vertically into the screen."""
    t = seg(f, 1, 8)
    if t <= 0:
        return
    e = ease_out(t)
    half = max(1.0, e * H * 0.55)
    cy = H / 2.0
    steps = 30
    for i in range(steps):
        f0 = i / steps
        f1 = (i + 1) / steps
        v = ((1 - f0) ** 2.4) * 0.62 * (1 - e)
        col = mix(BG, HEADING, v)
        if col == BG:
            continue
        d.rectangle([0, S(cy - half * f1), FW, S(cy - half * f0)], fill=col)
        d.rectangle([0, S(cy + half * f0), FW, S(cy + half * f1)], fill=col)
    if t < 0.95:
        lw = max(1, int(S(2.2 * (1 - e) + 0.7)))
        d.line([0, S(cy), FW, S(cy)], fill=mix(HEADING, WHITE, 1 - e), width=lw)


def scene_term(d, f):
    draw_terminal(d, f, f - T_TERM, TERM_LINES, tail_from=27)


def scene_joke(d, f):
    draw_terminal(d, f, f - T_JOKE, JOKE_LINES, y0=172.0, tail_from=20)


def scene_identity(d, f):
    t = f - T_ID
    x0 = 54.0
    if t >= 1:
        text(d, x0, 78, "Wisnu Rafi", F_DISP_XL, HEADING)
    if t >= 3:
        e = ease_out(seg(t, 3, 8))
        d.line([S(x0), S(172), S(x0 + 300 * e), S(172)],
               fill=fade(ACCENT, 0.9), width=max(1, int(S(1.5))))
    if t >= 5:
        n = int((t - 5) * 3.4)
        l1 = "Ship reliable systems."
        l2 = "Then break them."
        text(d, x0, 188, l1[:n], F_DISP_M, MUTED)
        if n > len(l1):
            text(d, x0, 214, l2[:n - len(l1)], F_DISP_M, MUTED)
    for i, (k, v) in enumerate(SPEC):
        st = 11 + i * 2
        if t < st:
            continue
        a = ease_out(seg(t, st, 5))
        y = 258 + i * 19
        text(d, x0, y, k, F_MONO_S, fade(FAINT, a))
        text(d, x0 + 92, y, v, F_MONO_S, fade(BODY, a))
    if t >= 17:
        draw_mark(d, W - 100, 112, 48, ease_out(seg(t, 17, 5)))


def scene_tree(d, f):
    t = f - T_TREE
    if t >= 1:
        text(d, 54, 52, "\u2192 ", F_MONO, fade(ACCENT, 0.9))
        n = int((t - 1) * 1.9)
        text(d, 54 + 2 * CW, 52, "op tick --mission redteam"[:n], F_MONO, BODY)
    for parent, child in BT_EDGES:
        k = ease_out(seg(t, 6 + BT_LEVEL[child] * 3, 5))
        draw_bt_edge(d, parent, child, t, k)
    for node in BT_NODES:
        k = ease_out(seg(t, 6 + BT_LEVEL[node] * 3, 5))
        draw_bt_node(d, node, t, k)
    if t >= 32:
        a = ease_out(seg(t, 32, 5))
        ctext(d, W / 2, 312, "every system tells a story. behavior leaves clues.",
              F_MONO_S, fade(MUTED, a))
    if t >= 34:
        a = ease_out(seg(t, 34, 4))
        ctext(d, W / 2, 334, "offensive security \u00b7 systems engineering",
              F_MONO_XS, fade(FAINT, a * 0.9))
    if t >= 20:
        a = ease_out(seg(t, 20, 6))
        rows = [("tick", "0042"), ("nodes", "7 \u00b7 1 not reached"), ("status", "running")]
        for i, (k, v) in enumerate(rows):
            y = H - 96 + i * 15
            text(d, 54, y, k, F_MONO_XS, fade(FAINT, a))
            text(d, 54 + 54, y, v, F_MONO_XS, fade(MUTED, a))


def scene_graph(d, f):
    t = f - T_GRAPH
    if t >= 1:
        text(d, 54, 52, "\u2192 ", F_MONO, fade(ACCENT, 0.9))
        n = int((t - 1) * 1.9)
        text(d, 54 + 2 * CW, 52, "map attack paths"[:n], F_MONO, BODY)
    draw_graph(d, t, ease_out(seg(t, 5, 6)))
    if t >= 24:
        a = ease_out(seg(t, 24, 5))
        ctext(d, W / 2, 314, "every path is a hypothesis.", F_MONO_S, fade(MUTED, a))
    if t >= 27:
        a = ease_out(seg(t, 27, 4))
        ctext(d, W / 2, 336, "attack graphs \u00b7 assumed breach",
              F_MONO_XS, fade(FAINT, a * 0.9))


def scene_path(d, f):
    t = f - T_PATH
    ax0, ax1 = 74.0, W - 74.0
    ay = 214.0
    text(d, 54, 54, "\u2192 ", F_MONO, fade(ACCENT, 0.9))
    n = int(max(0, t) * 2.4)
    text(d, 54 + 2 * CW, 54, "path --so-far"[:n], F_MONO, BODY)

    def px(i):
        return ax0 + i / (len(PATH_STOPS) - 1) * (ax1 - ax0)

    e = ease_in_out(seg(t, 3, 16))
    if e > 0:
        d.line([S(ax0), S(ay), S(ax0 + (ax1 - ax0) * e), S(ay)],
               fill=fade(LINE, 1.0), width=max(1, int(S(1.4))))
    for i, (name, role) in enumerate(PATH_STOPS):
        x = px(i)
        reach = i / (len(PATH_STOPS) - 1)
        if e < reach:
            continue
        a = ease_out(seg(t, 3 + reach * 16, 4))
        up = i % 2 == 0
        stem = 26.0
        d.line([S(x), S(ay), S(x), S(ay - stem if up else ay + stem)],
               fill=fade(LINE, a), width=max(1, int(S(1))))
        r = 3.0
        d.ellipse([S(x - r), S(ay - r), S(x + r), S(ay + r)], fill=fade(MUTED, a))
        ly = ay - stem - 30 if up else ay + stem + 8
        ctext(d, x, ly, name, F_MONO_S, fade(BODY, a))
        ctext(d, x, ly + 15, role, F_MONO_XS, fade(FAINT, a * 0.9))
    if e > 0.02:
        hx = ax0 + (ax1 - ax0) * e
        d.ellipse([S(hx - 4), S(ay - 4), S(hx + 4), S(ay + 4)], fill=fade(ACCENT, 1.0))
    if t >= 20:
        a = ease_out(seg(t, 20, 6))
        ctext(d, W / 2, H - 66, "from breaking in to building unbreakable",
              F_MONO_XS, fade(FAINT, a))


def scene_sign(d, f):
    t = f - T_SIGN
    cx = W / 2.0
    a = ease_out(seg(t, 1, 5))
    draw_mark(d, cx, 158, 62, a)
    if t >= 3:
        b = ease_out(seg(t, 3, 4))
        ctext(d, cx, 206, "wisnurafi", F_MONO_XL, fade(HEADING, b))
    if t >= 5:
        b = ease_out(seg(t, 5, 4))
        ctext(d, cx, 256, "Wisnu Rafi \u2014 systems & offensive security engineer",
              F_MONO_S, fade(MUTED, b))
    if t >= 7:
        b = ease_out(seg(t, 7, 3))
        w = 210 * b
        d.line([S(cx - w), S(284), S(cx + w), S(284)],
               fill=fade(LINE, b), width=max(1, int(S(1))))
    if t >= 9:
        b = ease_out(seg(t, 9, 3))
        left, right = "github.com/wisnurafi", "rafiprofile.my.id"
        total = text_w(left, F_MONO_S) + text_w(" \u00b7 ", F_MONO_S) + text_w(right, F_MONO_S)
        x = cx - total / 2
        text(d, x, 302, left, F_MONO_S, fade(BODY, b))
        x += text_w(left, F_MONO_S)
        text(d, x, 302, " \u00b7 ", F_MONO_S, fade(FAINT, b))
        x += text_w(" \u00b7 ", F_MONO_S)
        text(d, x, 302, right, F_MONO_S, fade(ACCENT, b))
    if t >= 11 and (f // 4) % 2 == 0:
        half = text_w("wisnurafi", F_MONO_XL) / 2.0
        cwx = cw(F_MONO_XL)
        x = cx + half + cwx * 0.35
        d.rectangle([S(x), S(214), S(x + cwx * 0.8), S(240)],
                    fill=fade(HEADING, 0.55))


def flash_card(img, f):
    t = f - T_ID
    if not (-2 <= t < 0):
        return None
    ground = HEADING if t < -1 else mix(HEADING, BODY, 0.35)
    card = Image.new("RGB", (FW, FH), ground)
    d = ImageDraw.Draw(card)
    ctext(d, W / 2, H / 2 - 22, "whoami", F_MONO_XL, BG)
    col = mix(ground, BG, 0.55)
    for cx, cy, sx, sy in ((16, 16, 1, 1), (W - 16, 16, -1, 1),
                           (16, H - 16, 1, -1), (W - 16, H - 16, -1, -1)):
        d.line([S(cx), S(cy), S(cx + sx * 26), S(cy)], fill=col, width=max(1, int(S(1))))
        d.line([S(cx), S(cy), S(cx), S(cy + sy * 26)], fill=col, width=max(1, int(S(1))))
    return card


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------

def render():
    rain = Rain(RNG)
    frames: list[Image.Image] = []
    durations: list[int] = []
    prev_ink = 0

    for i in range(T_END * Q):
        f = i / Q
        layout = int(f)
        frozen = layout in HOLD_MS
        reset_ink()
        img = Image.new("RGB", (FW, FH), BG)
        d = ImageDraw.Draw(img)

        if f < T_TERM:
            k_rain = seg(f, 5, 8) * 0.17
        elif f < T_ID:
            k_rain = 0.17
        elif f < T_JOKE:
            k_rain = 0.10
        elif f < T_TREE:
            k_rain = 0.12
        elif f < T_TREE + 8:
            k_rain = 0.12 * (1 - seg(f, T_TREE, 7))
        elif f < T_PATH:
            k_rain = 0.0
        elif f < T_SIGN:
            k_rain = 0.05
        else:
            k_rain = 0.07 * (1 - seg(f, T_SIGN + 8, 8))
        if not frozen:
            rain.step(1.0 / Q)
        rain.draw(d, k_rain)

        if f < T_TERM:
            scene_power(d, f)
        elif f < T_ID:
            scene_term(d, f)
        elif f < T_JOKE:
            scene_identity(d, f)
        elif f < T_TREE:
            scene_joke(d, f)
        elif f < T_GRAPH:
            scene_tree(d, f)
        elif f < T_PATH:
            scene_graph(d, f)
        elif f < T_SIGN:
            scene_path(d, f)
        else:
            scene_sign(d, f)

        if f >= T_ID:
            corner_ticks(d, 0.9)
            labels = {
                T_ID: "identity",
                T_JOKE: "payload",
                T_TREE: "operation tree",
                T_GRAPH: "attack paths",
                T_PATH: "path",
                T_SIGN: "open channel",
            }
            key = max(k for k in labels if k <= f)
            status_bar(d, 0.85, labels[key])

        amount = 0.0
        for c in CUTS:
            if c <= f < c + 2:
                amount = max(amount, 6.0 * (1 - (f - c) / 2.0))
        if T_ID <= f < T_ID + 4:
            amount = max(amount, 4.5 * (1 - (f - T_ID) / 4.0))
        if amount > 0.3:
            img = slice_glitch(img, amount, RNG)

        card = flash_card(img, f)
        if card is not None:
            img = card

        chars = ink()
        if frozen:
            dur = HOLD_MS[layout] * HOLD_SCALE * read_time(chars) / Q
        elif chars > prev_ink:
            dur = READ_MS
        else:
            dur = MOTION_MS
        dur = max(20, int(round(dur / 10.0)) * 10)
        durations.append(dur)
        prev_ink = chars

        if card is None:
            img = bloom(img)
        small = img.resize((OW, OH), Image.LANCZOS)
        small = ImageChops.multiply(
            small, SCANLINE_MASK if card is not None else SCREEN_MASK)

        if f >= T_END - 5:
            k = 1 - seg(f, T_END - 5, 5)
            small = ImageChops.multiply(
                small, Image.new("RGB", (OW, OH), (int(255 * k),) * 3))

        frames.append(small)
        if f % 20 == 0:
            print(f"  frame {f}/{T_END}")

    print("  building palette")
    palette = build_palette(frames)
    print(f"  encoding {len(frames)} frames -> {OUT}")
    quantised = [fr.quantize(palette=palette, dither=Image.Dither.NONE) for fr in frames]
    quantised[0].save(OUT, save_all=True, append_images=quantised[1:],
                      duration=durations, loop=0, optimize=True, disposal=1)
    size = os.path.getsize(OUT)
    print(f"  done: {OUT} ({OW}x{OH}, {size / 1024 / 1024:.2f} MB, "
          f"{len(frames)} frames, {sum(durations) / 1000:.1f}s)")


if __name__ == "__main__":
    render()
