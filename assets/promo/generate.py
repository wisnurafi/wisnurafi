#!/usr/bin/env python3
"""
wisnu-terminal.gif — animated terminal banner for the GitHub profile README.
An operation tree ticks down like guilyx's behaviour tree, but red-team flavored.

Layout is authored at 880x440 and exported at 2x (1760x880).
Requires: pip install pillow
"""
import math
from PIL import Image, ImageDraw, ImageFont

W, H = 880, 440
EXPORT = 2
FPS = 12
DUR = 9.0
NFRAMES = int(FPS * DUR)

BG = (11, 13, 18)
PANEL = (18, 21, 29)
BORDER = (42, 47, 58)
TEXT = (229, 231, 235)
DIM = (107, 114, 128)
FAINT = (70, 76, 90)
ACCENT = (139, 149, 240)   # periwinkle
GREEN = (126, 231, 135)
RED = (255, 123, 114)
PURPLE = (167, 139, 250)

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONTB = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

CMD = "op tick --mission redteam"
CAPTION = "every system tells a story. behavior leaves clues."
SUB = "offensive security \u00b7 systems engineering"

# tree nodes: (key, label, x, y, w, kind)
NODES = {
    "seq":      ("\u2192 sequence", 440, 100, 150, "root"),
    "fallback": ("? fallback",     250, 182, 140, "branch"),
    "parallel": ("\u21c4 parallel", 630, 182, 140, "branch"),
    "recon":    ("\u25cb recon ok", 160, 272, 140, "leaf-ok"),
    "pivot":    ("\u00b7 pivot",    340, 272, 140, "leaf-dim"),
    "access":   ("\u25b8 access",   540, 272, 140, "leaf-hot"),
    "persist":  ("\u25b8 persist",  720, 272, 140, "leaf-hot"),
}
NH = 34
# edges: parent -> child (draw order matters)
EDGES = [("seq", "fallback"), ("seq", "parallel"),
         ("fallback", "recon"), ("fallback", "pivot"),
         ("parallel", "access"), ("parallel", "persist")]


def fonts(scale):
    return (ImageFont.truetype(FONT, int(15 * scale)),
            ImageFont.truetype(FONTB, int(15 * scale)),
            ImageFont.truetype(FONT, int(13 * scale)))


def text_center(d, xy, s, font, fill):
    d.text(xy, s, font=font, fill=fill, anchor="mm")


def rbox(d, x, y, w, h, fill, outline):
    d.rounded_rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2],
                        radius=7, fill=fill, outline=outline, width=1)


def draw_scanlines(d, w, h):
    for yy in range(0, h, 3):
        d.line([(0, yy), (w, yy)], fill=(0, 0, 0, 40))


def draw_corners(d, w, h, m=26, L=22):
    c = FAINT
    for x0, y0, dx, dy in [(m, m, 1, 1), (w - m, m, -1, 1),
                           (m, h - m, 1, -1), (w - m, h - m, -1, -1)]:
        d.line([(x0, y0), (x0 + dx * L, y0)], fill=c, width=1)
        d.line([(x0, y0), (x0, y0 + dy * L)], fill=c, width=1)


def edge_geom(a, b):
    """Manhattan path points from bottom of a to top of b via mid-y."""
    ax, ay = NODES[a][2], NODES[a][3]
    bx, by = NODES[b][2], NODES[b][3]
    y0, y1, mid = ay + NH / 2, by - NH / 2, (ay + by) / 2
    return [(ax, y0), (ax, mid), (bx, mid), (bx, y1)]


def draw_edge_partial(d, pts, frac, color, width=2):
    """Draw polyline up to frac of its total length."""
    segs = []
    total = 0.0
    for i in range(len(pts) - 1):
        l = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        segs.append(l)
        total += l
    target = total * max(0.0, min(1.0, frac))
    acc = 0.0
    for i, l in enumerate(segs):
        if acc + l <= target:
            d.line([pts[i], pts[i + 1]], fill=color, width=width)
            acc += l
        else:
            r = (target - acc) / l if l > 0 else 0
            ex = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * r
            ey = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * r
            d.line([pts[i], (ex, ey)], fill=color, width=width)
            break


def leaf_color(kind, pulse):
    if kind == "leaf-ok":
        return GREEN
    if kind == "leaf-hot":
        return tuple(int(ACCENT[i] + (255 - ACCENT[i]) * pulse * 0.35) for i in range(3))
    return DIM


def render_frame(fi, f_reg, f_bold, f_small, S):
    t = fi / FPS
    img = Image.new("RGBA", (W * S, H * S), BG + (255,))
    d = ImageDraw.Draw(img)
    sc = lambda v: v * S

    draw_corners(d, W * S, H * S)

    # --- typed command ---
    type_end, type_dur = 0.3, 1.4
    nchars = int(max(0, min(1, (t - type_end) / type_dur)) * len(CMD))
    cmd_show = CMD[:nchars]
    d.text((sc(56), sc(52)), "\u2192 " + cmd_show, font=f_reg, fill=TEXT)
    if t < type_end + type_dur + 0.6 and int(t * 2.5) % 2 == 0:
        cx = 56 + d.textlength("\u2192 " + cmd_show, font=f_reg)
        d.line([(cx, sc(46)), (cx, sc(64))], fill=ACCENT, width=max(1, S // 2))

    # --- tree grows ---
    grow_start, grow_span = 2.0, 2.6
    order = ["seq", "fallback", "parallel", "recon", "pivot", "access", "persist"]
    node_on = {}
    for idx, key in enumerate(order):
        node_on[key] = max(0.0, min(1.0, (t - grow_start - idx * 0.32) / 0.3)) > 0

    for ei, (a, b) in enumerate(EDGES):
        frac = max(0.0, min(1.0, (t - grow_start - 0.15 - ei * 0.3) / 0.35))
        if frac > 0:
            draw_edge_partial(d, [(sc(x), sc(y)) for x, y in edge_geom(a, b)],
                              frac, (86, 94, 112))

    for key in order:
        if not node_on[key]:
            continue
        label, x, y, w, kind = NODES[key]
        pulse = 0.5 + 0.5 * math.sin(t * 3.0 + x * 0.01)
        rbox(d, sc(x), sc(y), sc(w), sc(NH),
             PANEL + (255,), BORDER + (255,))
        if kind in ("leaf-ok", "leaf-hot", "leaf-dim"):
            text_center(d, (sc(x), sc(y)), label, f_small, leaf_color(kind, pulse))
        else:
            text_center(d, (sc(x), sc(y)), label, f_small,
                        ACCENT if kind == "root" else TEXT)

    # --- caption fades in ---
    cap_a = max(0.0, min(1.0, (t - 5.2) / 1.2))
    if cap_a > 0:
        col = tuple(int(TEXT[i] * cap_a + BG[i] * (1 - cap_a)) for i in range(3))
        sub = tuple(int(DIM[i] * cap_a + BG[i] * (1 - cap_a)) for i in range(3))
        text_center(d, (sc(W / 2), sc(342)), CAPTION, f_reg, col)
        text_center(d, (sc(W / 2), sc(364)), SUB, f_small, sub)

    # --- stats (top-right readout) ---
    tick = 41 + int(max(0, t - 2.0) * 1.5)
    piv = 1 if t > 6.0 else 0
    sx = sc(W - 56)
    d.text((sx, sc(46)), f"tick   {tick:04d}", font=f_small, fill=DIM, anchor="ra")
    d.text((sx, sc(66)), f"nodes  7 \u00b7 {piv} pivoted", font=f_small, fill=DIM, anchor="ra")
    d.text((sx, sc(86)), "status running", font=f_small, fill=GREEN, anchor="ra")

    d.text((sc(56), sc(H - 30)), "operation tree", font=f_small, fill=FAINT)
    d.text((sc(W - 56), sc(H - 30)), "wisnurafi", font=f_small,
           fill=FAINT, anchor="ra")

    draw_scanlines(d, W * S, H * S)
    return img.convert("P", palette=Image.ADAPTIVE, colors=128)


def main():
    S = EXPORT
    f_reg, f_bold, f_small = fonts(S)
    frames = []
    for fi in range(NFRAMES):
        frames.append(render_frame(fi, f_reg, f_bold, f_small, S))
        if fi % 24 == 0:
            print(f"frame {fi}/{NFRAMES}")
    out = "assets/promo/wisnu-terminal.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=int(1000 / FPS), loop=0)
    print("wrote", out)


if __name__ == "__main__":
    main()
