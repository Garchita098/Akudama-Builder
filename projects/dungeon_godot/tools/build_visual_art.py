#!/usr/bin/env python3
"""Slice CC0 dungeon art and paint the small original pieces Living Dungeon adds.

Reads third_party/0x72 (DungeonTileset II, CC0) and writes art/ plus Godot
.import sidecars. Also writes a contact preview to /tmp/living_dungeon_preview.png
when invoked directly. Runtime art is the files under art/, not this script.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location("ld_assets", ROOT / "tools" / "assets.py")
assets = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(assets)

SHEET_PATH = ROOT / "third_party" / "0x72" / "0x72_DungeonTilesetII_v1.7.png"
WALLS_PATH = ROOT / "third_party" / "0x72" / "atlas_walls_low-16x16.png"
LIST_PATH = ROOT / "third_party" / "0x72" / "tile_list_v1.7"
ART = ROOT / "art"

# Godot 3x3-minimal corner states -> column, row in atlas_walls_low (12x4).
# Corner order is TL, TR, BL, BR. States: 0 outer, 1 side A, 2 side B, 3 concave, 4 filled.
WALL_TABLE = {
    (0, 0, 0, 0): (0, 3),
    (0, 0, 1, 1): (0, 0),
    (0, 2, 0, 2): (1, 3),
    (0, 2, 1, 3): (1, 0),
    (0, 2, 1, 4): (8, 0),
    (1, 1, 0, 0): (0, 2),
    (1, 1, 1, 1): (0, 1),
    (1, 3, 0, 2): (1, 2),
    (1, 3, 1, 3): (1, 1),
    (1, 3, 1, 4): (4, 1),
    (1, 4, 0, 2): (8, 3),
    (1, 4, 1, 3): (4, 2),
    (1, 4, 1, 4): (8, 1),
    (2, 0, 2, 0): (3, 3),
    (2, 0, 3, 1): (3, 0),
    (2, 0, 4, 1): (11, 0),
    (2, 2, 2, 2): (2, 3),
    (2, 2, 3, 3): (2, 0),
    (2, 2, 3, 4): (5, 0),
    (2, 2, 4, 3): (6, 0),
    (2, 2, 4, 4): (10, 0),
    (3, 1, 2, 0): (3, 2),
    (3, 1, 3, 1): (3, 1),
    (3, 1, 4, 1): (7, 1),
    (3, 3, 2, 2): (2, 2),
    (3, 3, 3, 3): (2, 1),
    (3, 3, 3, 4): (7, 3),
    (3, 3, 4, 3): (4, 3),
    (3, 3, 4, 4): (9, 0),
    (3, 4, 2, 2): (5, 3),
    (3, 4, 3, 3): (7, 0),
    (3, 4, 3, 4): (8, 2),
    (3, 4, 4, 3): (9, 1),
    (3, 4, 4, 4): (5, 1),
    (4, 1, 2, 0): (11, 3),
    (4, 1, 3, 1): (7, 2),
    (4, 1, 4, 1): (11, 2),
    (4, 3, 2, 2): (6, 3),
    (4, 3, 3, 3): (4, 0),
    (4, 3, 3, 4): (10, 2),
    (4, 3, 4, 3): (11, 1),
    (4, 3, 4, 4): (6, 1),
    (4, 4, 2, 2): (9, 3),
    (4, 4, 3, 3): (10, 3),
    (4, 4, 3, 4): (5, 2),
    (4, 4, 4, 3): (6, 2),
    (4, 4, 4, 4): (9, 2),
}

FACTION_HUE = {
    "azure": 0.58,
    "crimson": 0.01,
    "verdant": 0.34,
}

VOID = (34, 34, 34, 255)
BRICK_HI = (211, 191, 169, 255)
BRICK = (170, 141, 122, 255)
BRICK_DK = (119, 92, 85, 255)
MORTAR = (72, 59, 58, 255)
INK = (22, 16, 20, 255)


def blank(w: int, h: int, color=(0, 0, 0, 0)):
    return w, h, bytearray(bytes(color) * (w * h))


def px(img, x, y, color):
    w, h, data = img
    if 0 <= x < w and 0 <= y < h and color[3] != 0:
        i = (y * w + x) * 4
        data[i : i + 4] = bytes(color)


def getp(img, x, y):
    w, h, data = img
    i = (y * w + x) * 4
    return tuple(data[i : i + 4])


def crop_sheet(sheet, box):
    sw, _sh, sp = sheet
    x, y, w, h = box
    out = blank(w, h)
    data = out[2]
    for yy in range(h):
        for xx in range(w):
            si = ((y + yy) * sw + (x + xx)) * 4
            di = (yy * w + xx) * 4
            data[di : di + 4] = sp[si : si + 4]
    return out


def blit(dst, src, dx, dy):
    dw, dh, dp = dst
    sw, sh, sp = src
    for y in range(sh):
        if not (0 <= dy + y < dh):
            continue
        for x in range(sw):
            if not (0 <= dx + x < dw):
                continue
            si = (y * sw + x) * 4
            if sp[si + 3] == 0:
                continue
            di = ((dy + y) * dw + (dx + x)) * 4
            dp[di : di + 4] = sp[si : si + 4]


def scale_nearest(img, factor: int):
    w, h, data = img
    out = blank(w * factor, h * factor)
    od = out[2]
    ow = w * factor
    for y in range(h):
        for x in range(w):
            p = data[(y * w + x) * 4 : (y * w + x) * 4 + 4]
            for dy in range(factor):
                for dx in range(factor):
                    i = ((y * factor + dy) * ow + (x * factor + dx)) * 4
                    od[i : i + 4] = p
    return out


def save(rel: str, img) -> None:
    path = ART / rel
    assets.write_png(path, img)
    assets.write_godot_import(path, ROOT)


def load_entries():
    entries = {}
    for line in LIST_PATH.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        entries[parts[0]] = tuple(int(v) for v in parts[1:5])
    return entries


def rgb_hsv(r, g, b):
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    mx, mn = max(rf, gf, bf), min(rf, gf, bf)
    d = mx - mn
    if d < 1e-6:
        h = 0.0
    elif mx == rf:
        h = ((gf - bf) / d) % 6.0
    elif mx == gf:
        h = (bf - rf) / d + 2.0
    else:
        h = (rf - gf) / d + 4.0
    h /= 6.0
    s = 0.0 if mx == 0 else d / mx
    return h, s, mx


def hsv_rgb(h, s, v):
    h = h % 1.0
    i = int(h * 6.0)
    f = h * 6.0 - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    i %= 6
    rgb = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i]
    return tuple(max(0, min(255, int(c * 255 + 0.5))) for c in rgb)


def is_skin(h, s, v):
    return 0.02 <= h <= 0.12 and 0.15 <= s <= 0.65 and v >= 0.35


def recolor(img, hue: float, strength: float = 0.85):
    w, h, data = img
    out = blank(w, h)
    od = out[2]
    for i in range(0, len(data), 4):
        r, g, b, a = data[i : i + 4]
        if a == 0:
            continue
        hh, s, v = rgb_hsv(r, g, b)
        if s < 0.22 or v < 0.18 or is_skin(hh, s, v):
            od[i : i + 4] = bytes((r, g, b, a))
            continue
        nh = hh + (hue - hh) * strength
        ns = min(1.0, s * 0.92 + 0.08)
        nr, ng, nb = hsv_rgb(nh, ns, v)
        od[i : i + 4] = bytes((nr, ng, nb, a))
    return out


def punch_void(img):
    w, h, data = img
    out = blank(w, h)
    od = out[2]
    for i in range(0, len(data), 4):
        r, g, b, a = data[i : i + 4]
        if a == 0 or (r, g, b) == (34, 34, 34):
            continue
        od[i : i + 4] = bytes((r, g, b, a))
    return out


def solid_brick() -> tuple:
    img = blank(16, 16, MORTAR)
    for y in range(16):
        course = y // 4
        row = y % 4
        offset = 0 if course % 2 == 0 else 5
        for x in range(16):
            bx = (x + offset) % 8
            if row == 3 or bx == 7:
                color = MORTAR if (x + y) % 5 else BRICK_DK
            elif row == 0:
                color = BRICK_HI if bx % 3 != 2 else BRICK
            elif row == 1:
                color = BRICK
            else:
                color = BRICK_DK if bx % 4 == 0 else BRICK
            px(img, x, y, color)
    # A couple of cracks so interior masses are not a rubber stamp.
    for x, y in ((3, 6), (4, 6), (4, 7), (11, 11), (12, 11), (12, 12)):
        px(img, x, y, INK)
    return img


def slice_cell(atlas, col, row, cell=16):
    aw, _ah, ap = atlas
    x, y = col * cell, row * cell
    out = blank(cell, cell)
    data = out[2]
    for yy in range(cell):
        for xx in range(cell):
            si = ((y + yy) * aw + (x + xx)) * 4
            di = (yy * cell + xx) * 4
            data[di : di + 4] = ap[si : si + 4]
    return out


def radial(size: int, power: float = 1.6):
    img = blank(size, size)
    c = (size - 1) / 2.0
    for y in range(size):
        for x in range(size):
            d = ((x - c) ** 2 + (y - c) ** 2) ** 0.5 / c
            if d >= 1:
                continue
            a = int((1.0 - d) ** power * 255)
            px(img, x, y, (255, 255, 255, a))
    return img


def ellipse(w, h, color):
    img = blank(w, h)
    cx, cy = (w - 1) / 2, (h - 1) / 2
    rx, ry = w / 2, h / 2
    for y in range(h):
        for x in range(w):
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                px(img, x, y, color)
    return img


def ring(size, color, thickness=2):
    img = blank(size, size)
    c = (size - 1) / 2
    r = c - 0.5
    for y in range(size):
        for x in range(size):
            d = ((x - c) ** 2 + (y - c) ** 2) ** 0.5
            if r - thickness <= d <= r:
                px(img, x, y, color)
    return img


def paint_torch(frame: int):
    img = blank(16, 16)
    # Bracket on the lower half so it sits on a wall face.
    for y, color in ((11, BRICK_DK), (12, BRICK), (13, BRICK_HI)):
        for x in range(6, 10):
            px(img, x, y, color)
    px(img, 7, 10, BRICK_DK)
    px(img, 8, 10, BRICK_DK)
    flame = [
        [(8, 8, (255, 214, 96, 255))],
        [(7, 7, (255, 160, 48, 255)), (8, 7, (255, 214, 96, 255)), (8, 6, (255, 244, 180, 255))],
        [(7, 6, (255, 120, 32, 255)), (8, 5, (255, 236, 150, 255)), (9, 7, (255, 170, 40, 255)), (8, 8, (255, 90, 24, 255))],
        [(8, 4, (255, 250, 210, 255)), (7, 6, (255, 180, 48, 255)), (9, 6, (255, 140, 32, 255)), (8, 8, (255, 80, 20, 255))],
    ][frame % 4]
    for x, y, color in flame:
        px(img, x, y, color)
        if frame % 2 == 0:
            px(img, x, y + 1, (255, 90, 28, 180))
    return img


def paint_portal(frame: int):
    img = blank(16, 16)
    # Stone ring.
    for y in range(16):
        for x in range(16):
            d = ((x - 7.5) ** 2 + (y - 8.0) ** 2) ** 0.5
            if 5.2 <= d <= 7.2:
                px(img, x, y, BRICK_DK if (x + y + frame) % 3 else BRICK)
            elif 4.2 <= d < 5.2:
                px(img, x, y, (90, 40, 120, 255))
    # Spinning core.
    cores = [(168, 70, 210, 255), (210, 140, 255, 255), (90, 20, 120, 255), (230, 190, 255, 255)]
    for i, (ox, oy) in enumerate(((7, 7), (9, 8), (6, 9), (8, 6))):
        px(img, (ox + frame + i) % 5 + 5, (oy + frame) % 4 + 6, cores[(i + frame) % 4])
    px(img, 8, 8, (255, 230, 255, 255) if frame % 2 == 0 else (180, 90, 220, 255))
    return img


def paint_rock():
    img = blank(16, 16)
    spec = [
        "......####......",
        "....########....",
        "...##########...",
        "..############..",
        "..############..",
        "..############..",
        "...##########...",
        "....########....",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
    ]
    for y, row in enumerate(spec):
        for x, ch in enumerate(row):
            if ch != "#":
                continue
            if y < 3 or x < 5:
                color = BRICK_HI
            elif y > 5 or x > 11:
                color = BRICK_DK
            else:
                color = BRICK
            px(img, x, y + 4, color)
    px(img, 6, 6, (230, 214, 196, 255))
    return img


def paint_mushroom():
    img = blank(16, 16)
    cap = (168, 48, 52, 255)
    cap_hi = (214, 96, 88, 255)
    spot = (236, 220, 200, 255)
    stem = (214, 196, 170, 255)
    for y, row in enumerate(
        [
            "....######....",
            "...########...",
            "..##########..",
            "..##########..",
            "...########...",
            ".....####.....",
            ".....####.....",
            ".....####.....",
        ]
    ):
        for x, ch in enumerate(row):
            if ch == "#":
                color = cap_hi if y < 2 or x < 5 else cap
                px(img, x, y + 4, color)
    for sx, sy in ((6, 6), (9, 7), (7, 8)):
        px(img, sx, sy + 4, spot)
    for y in range(8, 12):
        px(img, 7, y + 4, stem)
        px(img, 8, y + 4, (180, 160, 130, 255))
    return img


def paint_moss():
    img = blank(16, 16)
    green = (70, 130, 58, 255)
    dark = (36, 78, 34, 255)
    for x, y in ((2, 12), (3, 12), (3, 11), (4, 13), (5, 12), (10, 13), (11, 12), (11, 11), (12, 13), (8, 14)):
        px(img, x, y, green if (x + y) % 2 == 0 else dark)
    return img


def paint_puddle():
    img = blank(16, 16)
    water = (64, 110, 130, 180)
    hi = (170, 220, 230, 220)
    for y in range(10, 15):
        for x in range(3, 13):
            if ((x - 8) / 5) ** 2 + ((y - 12) / 2.2) ** 2 <= 1:
                px(img, x, y, water)
    px(img, 6, 11, hi)
    px(img, 7, 11, hi)
    return img


def paint_ember():
    img = blank(16, 16)
    for x, y, color in (
        (4, 12, (90, 40, 28, 255)),
        (5, 12, (180, 70, 28, 255)),
        (6, 11, (240, 150, 48, 255)),
        (6, 12, (120, 40, 24, 255)),
        (9, 13, (200, 90, 30, 255)),
        (10, 13, (90, 36, 24, 255)),
        (11, 14, (240, 180, 60, 255)),
    ):
        px(img, x, y, color)
    return img


def paint_bone():
    img = blank(16, 16)
    bone = (220, 206, 180, 255)
    shade = (150, 130, 110, 255)
    for x, y in ((3, 12), (4, 12), (5, 11), (6, 11), (7, 12), (8, 12), (9, 13), (10, 13), (11, 12)):
        px(img, x, y, bone)
    px(img, 3, 11, bone)
    px(img, 11, 11, bone)
    px(img, 6, 12, shade)
    return img


def paint_fireball(frame: int):
    img = blank(16, 16)
    core = (255, 244, 210, 255)
    mid = (255, 150, 40, 255)
    outc = (180, 40, 20, 255)
    for y in range(16):
        for x in range(16):
            d = ((x - 7.5) ** 2 + (y - 7.5) ** 2) ** 0.5
            wobble = 0.6 if (x + y + frame) % 3 == 0 else 0
            if d < 2.2:
                px(img, x, y, core)
            elif d < 4.2 + wobble:
                px(img, x, y, mid)
            elif d < 6.2 and (x * 3 + y + frame) % 2 == 0:
                px(img, x, y, outc)
    # Sparks.
    sparks = [(2, 4), (13, 6), (4, 13), (12, 12)]
    sx, sy = sparks[frame % 4]
    px(img, sx, sy, (255, 220, 120, 255))
    return img


def paint_cloud(frame: int, color):
    img = blank(16, 16)
    puffs = [(4, 8), (8, 6), (11, 9), (7, 11)]
    for i, (cx, cy) in enumerate(puffs):
        ox = (frame + i) % 3 - 1
        for y in range(cy - 2, cy + 3):
            for x in range(cx + ox - 2, cx + ox + 3):
                if (x - (cx + ox)) ** 2 + (y - cy) ** 2 <= 5:
                    px(img, x, y, color if (x + y + i) % 3 else tuple(max(0, c - 30) if k < 3 else c for k, c in enumerate(color)))
    return img


def paint_sparkle(frame: int):
    img = blank(16, 16)
    gold = (255, 214, 96, 255)
    white = (255, 250, 230, 255)
    cx = cy = 8
    arm = 3 + (frame % 2)
    for d in range(-arm, arm + 1):
        px(img, cx + d, cy, gold)
        px(img, cx, cy + d, gold)
    px(img, cx, cy, white)
    diag = 2 if frame % 2 == 0 else 1
    for s in (-1, 1):
        px(img, cx + s * diag, cy + s * diag, white)
        px(img, cx + s * diag, cy - s * diag, gold)
    return img


def paint_shock(frame: int):
    return ring(32, (255, 220, 140, 255 - frame * 40), 2 + frame)


def paint_dust(frame: int):
    img = blank(16, 16)
    for i, (x, y) in enumerate(((4, 8), (8, 6), (11, 9), (6, 12), (10, 12))):
        px(img, x + (frame + i) % 3, y, (180, 160, 140, 200))
    return img


def paint_panel():
    img = blank(48, 48, (16, 14, 22, 240))
    gold = (186, 146, 78, 255)
    gold_dk = (92, 64, 36, 255)
    inner = (42, 34, 48, 255)
    for i in range(48):
        for t, color in ((0, gold_dk), (1, gold), (2, gold_dk), (3, inner)):
            px(img, i, t, color)
            px(img, i, 47 - t, color)
            px(img, t, i, color)
            px(img, 47 - t, i, color)
    # Corner studs.
    for x, y in ((6, 6), (41, 6), (6, 41), (41, 41)):
        px(img, x, y, (230, 200, 130, 255))
    return img


def paint_button(pressed: bool):
    img = blank(32, 32, (28, 32, 48, 255) if not pressed else (58, 36, 48, 255))
    border = (150, 112, 64, 255) if not pressed else (214, 170, 96, 255)
    for i in range(32):
        px(img, i, 0, border)
        px(img, i, 31, border)
        px(img, 0, i, border)
        px(img, 31, i, border)
        px(img, i, 1, (70, 54, 36, 255))
        px(img, i, 30, (70, 54, 36, 255))
    return img


def export_animations(sheet, entries):
    """Slice character sheets. Returns preview sprites."""
    specs = {
        "azure/warrior": ("knight_m", True),
        "azure/guard": ("knight_f", True),
        "azure/worker": ("dwarf_m", True),
        "azure/mage": ("wizzard_m", True),
        "crimson/warrior": ("orc_warrior", False),
        "crimson/guard": ("masked_orc", False),
        "crimson/worker": ("dwarf_f", True),
        "crimson/mage": ("wizzard_f", True),
        "verdant/warrior": ("elf_m", True),
        "verdant/guard": ("elf_f", True),
        "verdant/worker": ("dwarf_m", True),
        "verdant/mage": ("wizzard_m", True),
        "shared/necro": ("necromancer", False),
        "shared/undead": ("skelet", False),
        "monsters/goblin": ("goblin", False),
        "monsters/chort": ("chort", False),
        "monsters/demon": ("big_demon", False),
    }
    # Necromancer frames are named necromancer_anim_fN and used as idle.
    preview = []
    for folder, (prefix, recolor_it) in specs.items():
        faction = folder.split("/")[0]
        hue = FACTION_HUE.get(faction)
        sequences = []
        if prefix == "necromancer":
            sequences.append(("idle", [f"necromancer_anim_f{i}" for i in range(4)]))
            sequences.append(("run", [f"necromancer_anim_f{i}" for i in range(4)]))
        else:
            sequences.append(("idle", [f"{prefix}_idle_anim_f{i}" for i in range(4)]))
            run_names = [f"{prefix}_run_anim_f{i}" for i in range(4)]
            if run_names[0] not in entries:
                run_names = [f"{prefix}_idle_anim_f{i}" for i in range(4)]
            sequences.append(("run", run_names))
            hit = f"{prefix}_hit_anim_f0"
            if hit in entries:
                sequences.append(("hit", [hit]))
        for anim, names in sequences:
            for index, name in enumerate(names):
                if name not in entries:
                    raise SystemExit(f"missing frame {name}")
                img = crop_sheet(sheet, entries[name])
                if recolor_it and hue is not None and faction != "shared":
                    # Knights, elves and orcs already wear their faction color.
                    # Only recolor bodies that would otherwise all look the same.
                    if prefix.startswith("dwarf") or prefix.startswith("wizzard"):
                        img = recolor(img, hue)
                rel = f"units/{folder}_{anim}_{index}.png"
                # units/<faction>/<name>.png is what the loader expects.
                unit_faction, role = folder.split("/")
                rel = f"units/{unit_faction}/{role}_{anim}_{index}.png"
                save(rel, img)
                if index == 0 and anim == "idle":
                    preview.append(img)
    return preview


def export_buildings(sheet, entries):
    def piece(name):
        return crop_sheet(sheet, entries[name])

    tops = [piece(n) for n in ("wall_top_left", "wall_top_mid", "wall_top_right")]
    mids = [piece(n) for n in ("wall_left", "wall_mid", "wall_right")]
    banners = {
        "azure": piece("wall_banner_blue"),
        "crimson": piece("wall_banner_red"),
        "verdant": piece("wall_banner_green"),
    }
    door = piece("doors_leaf_closed")
    door_small = scale_nearest(door, 1)
    # 32x32 door halved.
    dw, dh, dd = door
    small = blank(16, 16)
    sd = small[2]
    for y in range(16):
        for x in range(16):
            sd[(y * 16 + x) * 4 : (y * 16 + x) * 4 + 4] = dd[((y * 2) * dw + (x * 2)) * 4 : ((y * 2) * dw + (x * 2)) * 4 + 4]
    door_small = small
    column = piece("column")
    previews = []
    for faction, banner in banners.items():
        # Tier 0: a gatehouse two tiles wide.
        camp = blank(48, 48)
        blit(camp, tops[0], 0, 0)
        blit(camp, tops[1], 16, 0)
        blit(camp, tops[2], 32, 0)
        blit(camp, mids[0], 0, 16)
        blit(camp, banner, 16, 16)
        blit(camp, mids[2], 32, 16)
        blit(camp, mids[0], 0, 32)
        blit(camp, door_small, 16, 32)
        blit(camp, mids[2], 32, 32)
        save(f"buildings/tier0_{faction}.png", camp)

        # Tier 1: wider keep with a full door.
        keep = blank(64, 64)
        blit(keep, tops[0], 0, 0)
        blit(keep, tops[1], 16, 0)
        blit(keep, tops[1], 32, 0)
        blit(keep, tops[2], 48, 0)
        blit(keep, mids[0], 0, 16)
        blit(keep, banner, 16, 16)
        blit(keep, mids[1], 32, 16)
        blit(keep, mids[2], 48, 16)
        blit(keep, mids[0], 0, 32)
        blit(keep, door, 16, 32)
        blit(keep, mids[2], 48, 32)
        save(f"buildings/tier1_{faction}.png", keep)

        # Tier 2: towers (columns) flanking a gate.
        castle = blank(96, 80)
        blit(castle, column, 0, 8)
        blit(castle, column, 80, 8)
        blit(castle, tops[0], 16, 8)
        blit(castle, tops[1], 32, 8)
        blit(castle, tops[1], 48, 8)
        blit(castle, tops[2], 64, 8)
        blit(castle, mids[0], 16, 24)
        blit(castle, banner, 32, 24)
        blit(castle, mids[1], 48, 24)
        blit(castle, mids[2], 64, 24)
        blit(castle, mids[0], 16, 40)
        blit(castle, door, 32, 40)
        blit(castle, mids[2], 64, 40)
        blit(castle, banner, 48, 24)
        save(f"buildings/tier2_{faction}.png", castle)
        previews.append(castle)
    return previews


def export_walls_and_floors(sheet, entries, wall_atlas):
    for i in range(1, 9):
        save(f"tiles/floor_{i}.png", crop_sheet(sheet, entries[f"floor_{i}"]))
    save("tiles/skull.png", crop_sheet(sheet, entries["skull"]))
    save("tiles/crate.png", crop_sheet(sheet, entries["crate"]))
    save("tiles/hole.png", crop_sheet(sheet, entries["hole"]))
    for row in range(4):
        for col in range(12):
            cell = punch_void(slice_cell(wall_atlas, col, row))
            save(f"tiles/wall_{col}_{row}.png", cell)
    save("tiles/wall_fill.png", solid_brick())


def build_preview(wall_atlas):
    # A tiny hand-authored maze so autotile mistakes show up before Godot.
    rows = [
        "################",
        "#......#.......#",
        "#..##..#..###..#",
        "#..#...#....#..#",
        "#..#...####.#..#",
        "#..............#",
        "#.....##.......#",
        "################",
    ]
    h, w = len(rows), len(rows[0])
    grid = [[rows[y][x] == "#" for x in range(w)] for y in range(h)]

    def is_wall(x, y):
        if x < 0 or y < 0 or x >= w or y >= h:
            return True
        return grid[y][x]

    def corner_state(a, b, c):
        if not a and not b:
            return 0
        if a and not b:
            return 1
        if not a and b:
            return 2
        if not c:
            return 3
        return 4

    scale = 4
    img = blank(w * 16 * scale, h * 16 * scale, (12, 10, 14, 255))
    floor = None
    # Use floor 1 from disk if present, else skip.
    floor_path = ART / "tiles" / "floor_1.png"
    if floor_path.exists():
        floor = assets.read_png(floor_path)
    fill = solid_brick()
    for y in range(h):
        for x in range(w):
            if floor is not None:
                blit(img, scale_nearest(floor, scale), x * 16 * scale, y * 16 * scale)
            if not grid[y][x]:
                continue
            n = is_wall(x, y - 1)
            s = is_wall(x, y + 1)
            e = is_wall(x + 1, y)
            ww = is_wall(x - 1, y)
            ne = is_wall(x + 1, y - 1)
            nw = is_wall(x - 1, y - 1)
            se = is_wall(x + 1, y + 1)
            sw = is_wall(x - 1, y + 1)
            key = (
                corner_state(n, ww, nw),
                corner_state(n, e, ne),
                corner_state(s, ww, sw),
                corner_state(s, e, se),
            )
            if key == (4, 4, 4, 4):
                tile = fill
            else:
                col, row = WALL_TABLE[key]
                tile = punch_void(slice_cell(wall_atlas, col, row))
            blit(img, scale_nearest(tile, scale), x * 16 * scale, y * 16 * scale)
    return img


def main() -> None:
    if len(WALL_TABLE) != 47:
        raise SystemExit(f"expected 47 wall patterns, got {len(WALL_TABLE)}")
    sheet = assets.read_png(SHEET_PATH)
    walls = assets.read_png(WALLS_PATH)
    entries = load_entries()
    export_walls_and_floors(sheet, entries, walls)
    chars = export_animations(sheet, entries)
    castles = export_buildings(sheet, entries)
    for i in range(4):
        save(f"fx/torch_{i}.png", paint_torch(i))
        save(f"fx/portal_{i}.png", paint_portal(i))
        save(f"fx/fire_{i}.png", paint_fireball(i))
        save(f"fx/plague_{i}.png", paint_cloud(i, (120, 210, 70, 210)))
        save(f"fx/bless_{i}.png", paint_sparkle(i))
        save(f"fx/dust_{i}.png", paint_dust(i))
        save(f"fx/hex_{i}.png", paint_cloud(i, (170, 90, 220, 210)))
    for i in range(3):
        save(f"fx/shock_{i}.png", paint_shock(i))
    save("tiles/rock.png", paint_rock())
    save("tiles/mushroom.png", paint_mushroom())
    save("tiles/moss.png", paint_moss())
    save("tiles/puddle.png", paint_puddle())
    save("tiles/ember.png", paint_ember())
    save("tiles/bones.png", paint_bone())
    save("fx/glow.png", radial(64, 1.8))
    save("fx/shadow.png", ellipse(16, 8, (0, 0, 0, 140)))
    save("fx/select.png", ring(24, (240, 204, 120, 255), 2))
    save("fx/mote.png", ellipse(3, 3, (255, 220, 160, 220)))
    save("ui/panel.png", paint_panel())
    save("ui/button.png", paint_button(False))
    save("ui/button_pressed.png", paint_button(True))

    # Contact sheet for review: walls preview, castles, a row of characters.
    maze = build_preview(walls)
    mw, mh, md = maze
    pad = 8
    row_h = 64 * 4
    sheet_w = max(mw, 96 * 4 * 3 + pad * 4)
    sheet_h = mh + pad + row_h + pad + 28 * 4
    contact = blank(sheet_w, sheet_h, (8, 8, 12, 255))
    blit(contact, maze, 0, 0)
    for i, castle in enumerate(castles):
        blit(contact, scale_nearest(castle, 3), pad + i * (96 * 3 + pad), mh + pad)
    x = pad
    y = mh + pad + row_h
    for sprite in chars[:12]:
        blit(contact, scale_nearest(sprite, 3), x, y)
        x += sprite[0] * 3 + 6
    out = Path("/tmp/living_dungeon_preview.png")
    assets.write_png(out, contact)
    print(f"wrote art under {ART}")
    print(f"preview {out} {sheet_w}x{sheet_h}")


if __name__ == "__main__":
    main()
