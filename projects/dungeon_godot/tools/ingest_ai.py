#!/usr/bin/env python3
"""Turn a raw AI image into palette-locked pixel art for Living Dungeon.

The generator is expected to return a large PNG (or any format ffmpeg can
read) of painterly pseudo-pixel art on a flat chroma background, usually
pure magenta #FF00FF. This tool keys that background out, splits a sheet
into objects, mode-pools down to a real pixel grid when one is plausible,
quantizes to art/style/palette.png in CIELAB, drops isolated specks, and
writes the Godot art tree plus a contact sheet.

No third-party packages. PNG I/O and Godot .import files come from assets.py.
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, deque
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ART_ROOT = PROJECT / "art"
DEFAULT_PALETTE = ART_ROOT / "style" / "palette.png"
PREVIEWS = PROJECT / "previews"
KINDS = ("tiles", "units", "buildings", "fx", "ui")

DEFAULT_SIZE = {
    "tiles": (32, 32),
    "units": (32, 48),
    "buildings": (48, 48),
    "fx": (16, 16),
    "ui": (32, 32),
}
DEFAULT_ANCHOR = {
    "tiles": "center",
    "units": "feet",
    "buildings": "feet",
    "fx": "center",
    "ui": "center",
}

Image = tuple[int, int, bytearray]


def _load_assets():
    path = Path(__file__).with_name("assets.py")
    spec = importlib.util.spec_from_file_location("living_dungeon_assets", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ASSETS = _load_assets()


def _dist2(r: int, g: int, b: int, key: tuple[int, int, int]) -> int:
    return (r - key[0]) ** 2 + (g - key[1]) ** 2 + (b - key[2]) ** 2


def _parse_hex(text: str) -> tuple[int, int, int]:
    cleaned = text.strip().lower().lstrip("#")
    if len(cleaned) != 6:
        raise SystemExit(f"color must be RRGGBB, got {text!r}")
    try:
        return tuple(int(cleaned[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as exc:
        raise SystemExit(f"color must be RRGGBB, got {text!r}") from exc


def _hex(color: tuple[int, int, int]) -> str:
    return f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"


def _blank(width: int, height: int) -> Image:
    return width, height, bytearray(width * height * 4)


def _opaque_bbox(image: Image) -> tuple[int, int, int, int] | None:
    width, height, pixels = image
    min_x, min_y, max_x, max_y = width, height, -1, -1
    for y in range(height):
        row = y * width * 4
        for x in range(width):
            if pixels[row + x * 4 + 3] == 0:
                continue
            if x < min_x:
                min_x = x
            if y < min_y:
                min_y = y
            if x > max_x:
                max_x = x
            if y > max_y:
                max_y = y
    if max_x < 0:
        return None
    return min_x, min_y, max_x + 1, max_y + 1


def _crop_box(image: Image, box: tuple[int, int, int, int]) -> Image:
    return ASSETS.crop(image, box[0], box[1], box[2] - box[0], box[3] - box[1])


def read_image(path: Path) -> Image:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return ASSETS.read_png(path)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise SystemExit(
            f"{path.name} is not a PNG. Re-export a PNG (flat #FF00FF background), "
            "or install ffmpeg so ingest can convert it."
        )
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "converted.png"
        result = subprocess.run(
            [ffmpeg, "-y", "-i", str(path), str(out)],
            check=False,
            capture_output=True,
        )
        if result.returncode != 0 or not out.is_file():
            detail = result.stderr.decode("utf-8", errors="replace")[-400:]
            raise SystemExit(f"ffmpeg could not read {path}: {detail}")
        return ASSETS.read_png(out)


def _border_samples(image: Image, depth: int = 2) -> list[tuple[int, int, int]]:
    width, height, pixels = image
    depth = max(1, min(depth, width, height))
    samples: list[tuple[int, int, int]] = []
    seen: set[tuple[int, int]] = set()
    for y in range(height):
        xs = range(width) if y < depth or y >= height - depth else list(range(depth)) + list(range(width - depth, width))
        for x in xs:
            if (x, y) in seen:
                continue
            seen.add((x, y))
            i = (y * width + x) * 4
            samples.append((pixels[i], pixels[i + 1], pixels[i + 2]))
    return samples


def detect_border_color(image: Image) -> tuple[tuple[int, int, int], float]:
    samples = _border_samples(image)
    if not samples:
        return (255, 0, 255), 0.0
    exact = Counter(samples)
    color, count = exact.most_common(1)[0]
    coverage = count / len(samples)
    if coverage >= 0.35:
        return color, coverage
    buckets: dict[tuple[int, int, int], list[tuple[int, int, int]]] = {}
    for sample in samples:
        key = tuple((channel // 8) * 8 for channel in sample)  # type: ignore[misc]
        buckets.setdefault(key, []).append(sample)  # type: ignore[arg-type]
    ranked = sorted(buckets.items(), key=lambda item: len(item[1]), reverse=True)
    chosen = ranked[0][1]
    mid = len(chosen) // 2
    median = tuple(sorted(pixel[channel] for pixel in chosen)[mid] for channel in range(3))
    return median, len(chosen) / len(samples)  # type: ignore[return-value]


def _border_match(image: Image, key: tuple[int, int, int], tolerance: int) -> float:
    samples = _border_samples(image)
    if not samples:
        return 0.0
    limit = tolerance * tolerance
    hits = sum(1 for sample in samples if _dist2(sample[0], sample[1], sample[2], key) <= limit)
    return hits / len(samples)


def resolve_key(
    image: Image, key_arg: str, tolerance: int
) -> tuple[tuple[int, int, int] | None, str]:
    if key_arg.lower() == "none":
        return None, "background removal off (--key none)"
    detected, coverage = detect_border_color(image)
    if key_arg.lower() == "auto":
        return detected, f"auto border {_hex(detected)} covers {coverage:.0%} of the edge"
    explicit = _parse_hex(key_arg)
    match = _border_match(image, explicit, tolerance)
    if match >= 0.35:
        return explicit, f"chroma {_hex(explicit)} matches {match:.0%} of the edge"
    if coverage >= 0.55 and _dist2(detected[0], detected[1], detected[2], explicit) > tolerance * tolerance:
        return (
            detected,
            f"fallback border {_hex(detected)} ({coverage:.0%} of the edge); "
            f"{_hex(explicit)} matched only {match:.0%}",
        )
    return explicit, f"chroma {_hex(explicit)} (edge match {match:.0%}; border is not a flat backdrop)"


def _key_planes(key: tuple[int, int, int]) -> tuple[list[int], list[int]] | None:
    high = [index for index, value in enumerate(key) if value >= 160]
    low = [index for index, value in enumerate(key) if value <= 96]
    if not high or not low:
        return None
    return high, low


def remove_background(image: Image, key: tuple[int, int, int] | None, tolerance: int, despill: bool) -> tuple[Image, int]:
    width, height, pixels = image
    out = bytearray(pixels)
    removed = 0
    if key is None:
        for i in range(0, len(out), 4):
            if out[i + 3] < 128:
                out[i : i + 4] = b"\x00\x00\x00\x00"
                removed += 1
            else:
                out[i + 3] = 255
        return (width, height, out), removed

    limit = tolerance * tolerance
    for i in range(0, len(out), 4):
        if out[i + 3] < 128 or _dist2(out[i], out[i + 1], out[i + 2], key) <= limit:
            out[i : i + 4] = b"\x00\x00\x00\x00"
            removed += 1
        else:
            out[i + 3] = 255
    keyed: Image = (width, height, out)
    keyed = _erode_fringe(pixels, keyed, key, tolerance, passes=2)
    if despill:
        keyed = _despill_edges(pixels, keyed, key, tolerance)
    keyed = _delete_specks(keyed)
    _zero_transparent(keyed)
    return keyed, removed


def _neighbors4(x: int, y: int, width: int, height: int) -> list[tuple[int, int]]:
    found = []
    if x > 0:
        found.append((x - 1, y))
    if x + 1 < width:
        found.append((x + 1, y))
    if y > 0:
        found.append((x, y - 1))
    if y + 1 < height:
        found.append((x, y + 1))
    return found


def _erode_fringe(
    original: bytes | bytearray,
    image: Image,
    key: tuple[int, int, int],
    tolerance: int,
    passes: int,
) -> Image:
    width, height, current = image
    limit = (tolerance * 2) ** 2
    for _ in range(passes):
        nxt = bytearray(current)
        for y in range(height):
            for x in range(width):
                i = (y * width + x) * 4
                if current[i + 3] == 0:
                    continue
                edge = False
                for nx, ny in _neighbors4(x, y, width, height):
                    if current[(ny * width + nx) * 4 + 3] == 0:
                        edge = True
                        break
                if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                    edge = True
                if not edge:
                    continue
                if _dist2(original[i], original[i + 1], original[i + 2], key) <= limit:
                    nxt[i : i + 4] = b"\x00\x00\x00\x00"
        current = nxt
    return width, height, current


def _despill_edges(
    original: bytes | bytearray,
    image: Image,
    key: tuple[int, int, int],
    tolerance: int,
) -> Image:
    planes = _key_planes(key)
    if planes is None:
        return image
    high, low = planes
    width, height, current = image
    limit = (tolerance * 3) ** 2
    out = bytearray(current)
    for y in range(height):
        for x in range(width):
            i = (y * width + x) * 4
            if current[i + 3] == 0:
                continue
            edge = x == 0 or y == 0 or x == width - 1 or y == height - 1
            if not edge:
                for nx, ny in _neighbors4(x, y, width, height):
                    if current[(ny * width + nx) * 4 + 3] == 0:
                        edge = True
                        break
            if not edge:
                continue
            if _dist2(original[i], original[i + 1], original[i + 2], key) > limit:
                continue
            rgb = [current[i], current[i + 1], current[i + 2]]
            cap = max(rgb[channel] for channel in low)
            for channel in high:
                if rgb[channel] > cap:
                    rgb[channel] = cap
            out[i : i + 3] = bytes(rgb)
    return width, height, out


def _delete_specks(image: Image) -> Image:
    width, height, pixels = image
    out = bytearray(pixels)
    for y in range(height):
        for x in range(width):
            i = (y * width + x) * 4
            if pixels[i + 3] == 0:
                continue
            keep = False
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if nx < 0 or ny < 0 or nx >= width or ny >= height:
                        continue
                    if pixels[(ny * width + nx) * 4 + 3] != 0:
                        keep = True
                        break
                if keep:
                    break
            if not keep:
                out[i : i + 4] = b"\x00\x00\x00\x00"
    return width, height, out


def _zero_transparent(image: Image) -> None:
    pixels = image[2]
    for i in range(0, len(pixels), 4):
        if pixels[i + 3] == 0:
            pixels[i : i + 4] = b"\x00\x00\x00\x00"
        else:
            pixels[i + 3] = 255


def _diff_signal(image: Image, axis: str) -> list[int]:
    width, height, pixels = image
    if axis == "x":
        signal = [0] * width
        step = max(1, height // 64)
        for y in range(0, height, step):
            row = y * width * 4
            for x in range(1, width):
                i = row + x * 4
                j = i - 4
                if pixels[i + 3] == 0 and pixels[j + 3] == 0:
                    continue
                signal[x] += abs(pixels[i] - pixels[j]) + abs(pixels[i + 1] - pixels[j + 1]) + abs(pixels[i + 2] - pixels[j + 2])
        return signal
    signal = [0] * height
    step = max(1, width // 64)
    for x in range(0, width, step):
        for y in range(1, height):
            i = (y * width + x) * 4
            j = ((y - 1) * width + x) * 4
            if pixels[i + 3] == 0 and pixels[j + 3] == 0:
                continue
            signal[y] += abs(pixels[i] - pixels[j]) + abs(pixels[i + 1] - pixels[j + 1]) + abs(pixels[i + 2] - pixels[j + 2])
    return signal


def _period_candidates(signal: list[int]) -> list[tuple[int, int, float]]:
    """Periods whose edges line up, scored by how much stronger they are than chance.

    A small period always collects a high fraction of noisy differences, so the
    rank is gain (fraction times period). The true cell size is the large
    period that still has a high gain; intra-block variance picks among them.
    """
    length = len(signal)
    total = sum(signal)
    if total <= 0 or length < 8:
        return []
    found: list[tuple[float, int, int]] = []
    max_period = min(length // 3, 128)
    for period in range(2, max_period + 1):
        scores = [0] * period
        for index, value in enumerate(signal):
            scores[index % period] += value
        phase = max(range(period), key=lambda item: scores[item])
        gain = scores[phase] / total * period
        if gain >= 1.8:
            found.append((gain, period, phase))
    if not found:
        return []
    found.sort(reverse=True)
    top = found[0][0]
    return [(period, phase, gain) for gain, period, phase in found if gain >= top * 0.75]


def _block_intra(image: Image, period: int, phase_x: int, phase_y: int) -> float:
    width, height, pixels = image
    step_y = max(1, period)
    variances: list[float] = []
    y = phase_y
    if y < 0:
        y = 0
    while y + period <= height:
        x = phase_x if phase_x >= 0 else 0
        while x + period <= width:
            values: list[int] = []
            opaque = 0
            for by in range(period):
                row = (y + by) * width
                for bx in range(period):
                    i = (row + x + bx) * 4
                    if pixels[i + 3] == 0:
                        continue
                    opaque += 1
                    values.append(pixels[i] + pixels[i + 1] + pixels[i + 2])
            area = period * period
            if opaque * 2 >= area and len(values) >= 2:
                mean = sum(values) / len(values)
                variances.append(sum((value - mean) ** 2 for value in values) / len(values))
            x += step_y
        y += step_y
    if not variances:
        return 1.0e9
    return sum(variances) / len(variances)


# A real texel is nearly constant. The synthetic fixture's jitter stays under
# ~100; a painterly AI figure scores in the thousands for every period.
_FLAT_CELL_INTRA = 800.0

# Master-palette ramps. A color may sit on more than one ramp (flame is both
# the hot gold glint and the fire core). Names match art/style/palette.gpl.
RAMP_GROUPS: dict[str, tuple[tuple[int, int, int], ...]] = {
    "outline": ((4, 4, 12), (9, 10, 24)),
    "dungeon": ((59, 44, 55), (44, 45, 44), (90, 85, 89), (135, 122, 129), (190, 177, 184), (101, 67, 79)),
    "azure": ((25, 26, 50), (36, 44, 89), (60, 75, 140), (71, 94, 161), (122, 154, 213), (144, 163, 208)),
    "violet": ((26, 15, 33), (44, 14, 74), (81, 16, 141), (177, 83, 231)),
    "cyan": ((17, 46, 57), (15, 102, 115), (75, 215, 222), (107, 237, 241)),
    "crimson": ((47, 15, 14), (90, 36, 29), (144, 55, 32), (200, 92, 36)),
    "fire": ((164, 70, 36), (213, 107, 30), (255, 206, 107), (255, 247, 191)),
    "gold": ((99, 76, 46), (181, 148, 101), (255, 206, 107)),
    "verdant": ((27, 41, 24), (64, 91, 34), (109, 140, 54), (177, 199, 129)),
    "bone": ((87, 75, 68), (159, 146, 129), (216, 214, 193), (250, 250, 235)),
}
GOLD_COLORS = {(181, 148, 101), (99, 76, 46)}
OUTLINE_COLORS = {(4, 4, 12), (9, 10, 24)}
_COLOR_RAMPS: dict[tuple[int, int, int], set[str]] = {}
for _ramp_name, _ramp_colors in RAMP_GROUPS.items():
    for _ramp_color in _ramp_colors:
        _COLOR_RAMPS.setdefault(_ramp_color, set()).add(_ramp_name)

_LAB_CACHE: dict[tuple[int, int, int], tuple[float, float, float]] = {}


def _max_plausible_cell(width: int, height: int) -> int:
    """Largest cell that can still be one texel of this figure.

    AI sheets have no clean lattice. The autocorrelation locks onto a period
    that is a slice of the body (63px on a ~190px knight collapsed to 2×5).
    A cell larger than about 1/8 of the shorter side is that failure.
    """
    return max(2, min(width, height) // 8)


def _srgb_channel_to_linear(channel: int) -> float:
    value = channel / 255.0
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def _cielab(color: tuple[int, int, int]) -> tuple[float, float, float]:
    """CIELAB (D65). Euclidean distance here keeps gold off the orange ramps."""
    cached = _LAB_CACHE.get(color)
    if cached is not None:
        return cached
    red = _srgb_channel_to_linear(color[0])
    green = _srgb_channel_to_linear(color[1])
    blue = _srgb_channel_to_linear(color[2])
    x = red * 0.4124564 + green * 0.3575761 + blue * 0.1804375
    y = red * 0.2126729 + green * 0.7151522 + blue * 0.0721750
    z = red * 0.0193339 + green * 0.1191920 + blue * 0.9503041

    def pivot(channel: float) -> float:
        if channel > 0.008856:
            return channel ** (1.0 / 3.0)
        return 7.787 * channel + 16.0 / 116.0

    fx, fy, fz = pivot(x / 0.95047), pivot(y / 1.0), pivot(z / 1.08883)
    lab = (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))
    _LAB_CACHE[color] = lab
    return lab


def _lab_dist2(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return (left[0] - right[0]) ** 2 + (left[1] - right[1]) ** 2 + (left[2] - right[2]) ** 2


def nearest_palette_color(
    color: tuple[int, int, int],
    palette: list[tuple[int, int, int]],
    labs: list[tuple[float, float, float]] | None = None,
) -> tuple[int, int, int]:
    sample = _cielab(color)
    if labs is None:
        labs = [_cielab(entry) for entry in palette]
    best = 0
    best_distance = _lab_dist2(sample, labs[0])
    for index, entry in enumerate(labs):
        distance = _lab_dist2(sample, entry)
        if distance < best_distance:
            best_distance = distance
            best = index
    return palette[best]


def estimate_pixel_grid(image: Image, forced: int = 0) -> tuple[int, int, int] | None:
    """Return (period, phase_x, phase_y) when a square pixel grid is visible.

    ``forced == 1`` means there is no grid: the caller mode-pools straight to
    the canvas. ``forced > 1`` uses that cell size. ``forced == 0`` estimates,
    then rejects a period that is larger than 1/8 of the figure or whose cells
    are not flat.
    """
    width, height, _pixels = image
    if forced < 0:
        raise SystemExit("--pixel-grid must be >= 0")
    if forced == 1:
        return None
    if forced > 1:
        if forced > min(width, height) // 2:
            return None
        return forced, 0, 0
    max_cell = _max_plausible_cell(width, height)
    phases: dict[int, list[int]] = {}
    for axis, signal in (("x", _diff_signal(image, "x")), ("y", _diff_signal(image, "y"))):
        for period, phase, _gain in _period_candidates(signal):
            slot = phases.setdefault(period, [0, 0])
            slot[0 if axis == "x" else 1] = phase
    for period in list(phases):
        phase_x, phase_y = phases[period]
        if period % 2 == 0 and period // 2 >= 2:
            half = period // 2
            phases.setdefault(half, [phase_x % half, phase_y % half])
        double = period * 2
        if 2 <= double <= max_cell:
            phases.setdefault(double, [phase_x, phase_y])
    scored: list[tuple[int, int, int, float]] = []
    for period, (phase_x, phase_y) in phases.items():
        if period < 2 or period > max_cell:
            continue
        intra = _block_intra(image, period, phase_x, phase_y)
        scored.append((period, phase_x, phase_y, intra))
    flat = [item for item in scored if item[3] <= _FLAT_CELL_INTRA]
    if not flat:
        return None
    period, phase_x, phase_y, _intra = max(flat, key=lambda item: item[0])
    return period, phase_x, phase_y


def _snap_box(box: tuple[int, int, int, int], period: int, phase_x: int, phase_y: int, width: int, height: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box

    def snap_start(value: int, phase: int) -> int:
        if value <= phase:
            return max(0, phase if phase < value + period else 0)
        return phase + ((value - phase) // period) * period

    def snap_end(value: int, phase: int, limit: int) -> int:
        if value <= phase:
            return min(limit, phase)
        end = phase + ((value - phase + period - 1) // period) * period
        return min(limit, max(end, value))

    return snap_start(x0, phase_x), snap_start(y0, phase_y), snap_end(x1, phase_x, width), snap_end(y1, phase_y, height)


def _mode_color(pixels: bytearray, width: int, x0: int, y0: int, x1: int, y1: int) -> tuple[int, int, int, int]:
    buckets: dict[tuple[int, int, int], list[tuple[int, int, int]]] = {}
    opaque = 0
    total = 0
    for y in range(y0, y1):
        row = y * width
        for x in range(x0, x1):
            total += 1
            i = (row + x) * 4
            if pixels[i + 3] == 0:
                continue
            opaque += 1
            bucket = (pixels[i] // 32, pixels[i + 1] // 32, pixels[i + 2] // 32)
            buckets.setdefault(bucket, []).append((pixels[i], pixels[i + 1], pixels[i + 2]))
    if total == 0 or opaque * 2 < total or not buckets:
        return (0, 0, 0, 0)
    chosen = max(buckets.values(), key=len)
    mid = len(chosen) // 2
    red = sorted(pixel[0] for pixel in chosen)[mid]
    green = sorted(pixel[1] for pixel in chosen)[mid]
    blue = sorted(pixel[2] for pixel in chosen)[mid]
    return red, green, blue, 255


def mode_pool(image: Image, period: int, phase_x: int, phase_y: int) -> Image:
    width, height, pixels = image
    xs = list(range(phase_x, width, period))
    ys = list(range(phase_y, height, period))
    if not xs or not ys:
        return image
    out_w, out_h = len(xs), len(ys)
    out = bytearray(out_w * out_h * 4)
    for oy, y0 in enumerate(ys):
        y1 = min(height, y0 + period)
        for ox, x0 in enumerate(xs):
            x1 = min(width, x0 + period)
            color = _mode_color(pixels, width, x0, y0, x1, y1)
            i = (oy * out_w + ox) * 4
            out[i : i + 4] = bytes(color)
    return out_w, out_h, out


def mode_pool_to_size(image: Image, new_w: int, new_h: int) -> Image:
    width, height, pixels = image
    if new_w == width and new_h == height:
        return image
    if new_w < 1 or new_h < 1:
        raise ValueError("mode-pool target must be at least 1x1")
    out = bytearray(new_w * new_h * 4)
    for y in range(new_h):
        y0 = y * height // new_h
        y1 = max(y0 + 1, (y + 1) * height // new_h)
        for x in range(new_w):
            x0 = x * width // new_w
            x1 = max(x0 + 1, (x + 1) * width // new_w)
            color = _mode_color(pixels, width, x0, y0, x1, y1)
            i = (y * new_w + x) * 4
            out[i : i + 4] = bytes(color)
    return new_w, new_h, out


def _fit_size(width: int, height: int, max_w: int, max_h: int) -> tuple[int, int]:
    if width <= max_w and height <= max_h:
        return width, height
    scale = min(max_w / width, max_h / height)
    fitted_w = max(1, min(max_w, int(round(width * scale))))
    fitted_h = max(1, min(max_h, int(round(height * scale))))
    return fitted_w, fitted_h


def downscale_content(image: Image, max_w: int, max_h: int, forced_grid: int) -> tuple[Image, str]:
    box = _opaque_bbox(image)
    if box is None:
        raise ValueError("frame has no opaque pixels")
    cropped = _crop_box(image, box)
    grid = estimate_pixel_grid(cropped, forced_grid)
    note = "no plausible pixel grid; mode-pool to the canvas"
    native = cropped
    if grid is not None:
        period, phase_x, phase_y = grid
        snapped = _snap_box((0, 0, cropped[0], cropped[1]), period, phase_x, phase_y, cropped[0], cropped[1])
        # Snap is in cropped coordinates. phase is relative to the crop origin,
        # which is what estimate_pixel_grid measured.
        aligned = _crop_box(cropped, snapped) if snapped[2] > snapped[0] and snapped[3] > snapped[1] else cropped
        # The snap moved the origin onto the grid, so the aligned image starts on a cell.
        native = mode_pool(aligned, period, 0, 0)
        native = _trim(native)
        note = f"pixel grid {period}px phase {phase_x},{phase_y} -> {native[0]}x{native[1]}"
    fitted_w, fitted_h = _fit_size(native[0], native[1], max_w, max_h)
    if (fitted_w, fitted_h) != (native[0], native[1]):
        native = mode_pool_to_size(native, fitted_w, fitted_h)
        native = _trim(native)
        note += f" fit {native[0]}x{native[1]}"
    return native, note


def _trim(image: Image) -> Image:
    box = _opaque_bbox(image)
    if box is None:
        return image
    if box == (0, 0, image[0], image[1]):
        return image
    return _crop_box(image, box)


def components(image: Image, min_area: int, connectivity: int) -> list[Image]:
    width, height, pixels = image
    seen = bytearray(width * height)
    found: list[tuple[tuple[int, int, int, int], list[tuple[int, int]]]] = []
    offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if connectivity == 8:
        offsets += [(-1, -1), (1, -1), (-1, 1), (1, 1)]
    for y in range(height):
        for x in range(width):
            start = y * width + x
            if seen[start]:
                continue
            if pixels[start * 4 + 3] == 0:
                seen[start] = 1
                continue
            queue: deque[tuple[int, int]] = deque([(x, y)])
            seen[start] = 1
            points: list[tuple[int, int]] = []
            min_x = max_x = x
            min_y = max_y = y
            while queue:
                cx, cy = queue.popleft()
                points.append((cx, cy))
                if cx < min_x:
                    min_x = cx
                if cy < min_y:
                    min_y = cy
                if cx > max_x:
                    max_x = cx
                if cy > max_y:
                    max_y = cy
                for dx, dy in offsets:
                    nx, ny = cx + dx, cy + dy
                    if nx < 0 or ny < 0 or nx >= width or ny >= height:
                        continue
                    nid = ny * width + nx
                    if seen[nid] or pixels[nid * 4 + 3] == 0:
                        continue
                    seen[nid] = 1
                    queue.append((nx, ny))
            if len(points) >= min_area:
                found.append(((min_x, min_y, max_x + 1, max_y + 1), points))
    if not found:
        return []
    frames: list[Image] = []
    for box, points in _reading_order(found):
        frame_w = box[2] - box[0]
        frame_h = box[3] - box[1]
        frame = bytearray(frame_w * frame_h * 4)
        for px, py in points:
            src = (py * width + px) * 4
            dst = ((py - box[1]) * frame_w + (px - box[0])) * 4
            frame[dst : dst + 4] = pixels[src : src + 4]
        frames.append((frame_w, frame_h, frame))
    return frames


def _reading_order(
    found: list[tuple[tuple[int, int, int, int], list[tuple[int, int]]]],
) -> list[tuple[tuple[int, int, int, int], list[tuple[int, int]]]]:
    """Left to right, then top to bottom. Overlapping vertical spans share a row."""
    remaining = sorted(found, key=lambda item: (item[0][1], item[0][0]))
    rows: list[list[tuple[tuple[int, int, int, int], list[tuple[int, int]]]]] = []
    for item in remaining:
        box = item[0]
        placed = False
        for row in rows:
            other = row[0][0]
            overlap = min(box[3], other[3]) - max(box[1], other[1])
            smaller = min(box[3] - box[1], other[3] - other[1])
            if smaller > 0 and overlap >= smaller * 0.4:
                row.append(item)
                placed = True
                break
        if not placed:
            rows.append([item])
    ordered: list[tuple[tuple[int, int, int, int], list[tuple[int, int]]]] = []
    for row in rows:
        ordered.extend(sorted(row, key=lambda item: item[0][0]))
    return ordered


def slice_components(
    image: Image,
    separate: str,
    grid: tuple[int, int] | None,
    margin: int,
    spacing: int,
    min_area: int,
    connectivity: int,
) -> list[Image]:
    if separate == "grid":
        if grid is None:
            raise SystemExit("--separate grid needs --grid WxH")
        frames, _cols, _rows = ASSETS.slice_grid(image, grid[0], grid[1], margin, spacing)
        kept = []
        for frame in frames:
            _zero_transparent(frame)
            if _opaque_bbox(frame) is not None and _opaque_count(frame) >= min_area:
                kept.append(_trim(frame))
        return kept
    if separate == "none":
        box = _opaque_bbox(image)
        if box is None:
            return []
        return [_crop_box(image, box)]
    return components(image, min_area, connectivity)


def _opaque_count(image: Image) -> int:
    pixels = image[2]
    return sum(1 for i in range(3, len(pixels), 4) if pixels[i] != 0)


def add_outline(image: Image, color: tuple[int, int, int]) -> Image:
    width, height, pixels = image
    grown_w, grown_h = width + 2, height + 2
    out = bytearray(grown_w * grown_h * 4)
    for y in range(height):
        src = y * width * 4
        dst = ((y + 1) * grown_w + 1) * 4
        out[dst : dst + width * 4] = pixels[src : src + width * 4]
    outlined = bytearray(out)
    for y in range(grown_h):
        for x in range(grown_w):
            i = (y * grown_w + x) * 4
            if out[i + 3] != 0:
                continue
            touch = False
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if nx < 0 or ny < 0 or nx >= grown_w or ny >= grown_h:
                        continue
                    if out[(ny * grown_w + nx) * 4 + 3] != 0:
                        touch = True
                        break
                if touch:
                    break
            if touch:
                outlined[i : i + 4] = bytes((color[0], color[1], color[2], 255))
    return grown_w, grown_h, outlined


def anchor(image: Image, canvas_w: int, canvas_h: int, mode: str, foot_pad: int) -> Image:
    width, height, pixels = image
    if width > canvas_w or height > canvas_h:
        fitted_w, fitted_h = _fit_size(width, height, canvas_w, canvas_h)
        image = mode_pool_to_size(image, fitted_w, fitted_h)
        width, height, pixels = image
    canvas = bytearray(canvas_w * canvas_h * 4)
    if mode == "feet":
        origin_x = (canvas_w - width) // 2
        origin_y = canvas_h - height - foot_pad
    elif mode == "top":
        origin_x = (canvas_w - width) // 2
        origin_y = foot_pad
    else:
        origin_x = (canvas_w - width) // 2
        origin_y = (canvas_h - height) // 2
    origin_x = max(0, origin_x)
    origin_y = max(0, origin_y)
    for y in range(height):
        dest_y = origin_y + y
        if dest_y >= canvas_h:
            break
        for x in range(width):
            dest_x = origin_x + x
            if dest_x >= canvas_w:
                break
            src = (y * width + x) * 4
            dst = (dest_y * canvas_w + dest_x) * 4
            canvas[dst : dst + 4] = pixels[src : src + 4]
    return canvas_w, canvas_h, canvas


def load_palette(path: Path | None, colors: int) -> list[tuple[int, int, int]] | None:
    if path is not None:
        if not path.is_file():
            raise SystemExit(f"palette not found: {path}")
        suffix = path.suffix.lower()
        if suffix == ".gpl":
            return _read_gpl(path)
        if suffix == ".hex":
            return _read_hex(path)
        return ASSETS.palette_from_image(ASSETS.read_png(path))
    if colors > 0:
        return None
    if DEFAULT_PALETTE.is_file():
        return ASSETS.palette_from_image(ASSETS.read_png(DEFAULT_PALETTE))
    raise SystemExit(f"master palette not found at {DEFAULT_PALETTE}; pass --palette or --colors")


def _read_gpl(path: Path) -> list[tuple[int, int, int]]:
    colors: list[tuple[int, int, int]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            colors.append((int(parts[0]), int(parts[1]), int(parts[2])))
        except ValueError:
            continue
    if not colors:
        raise SystemExit(f"no colors in {path}")
    return colors


def _read_hex(path: Path) -> list[tuple[int, int, int]]:
    colors: list[tuple[int, int, int]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") and len(cleaned) != 7:
            if cleaned.startswith(";") or cleaned.startswith("//"):
                continue
            if not cleaned or cleaned.startswith("#") and len(cleaned) < 7:
                continue
        token = cleaned.split()[0]
        if token.startswith("#"):
            token = token[1:]
        if len(token) == 6:
            colors.append(_parse_hex(token))
    if not colors:
        raise SystemExit(f"no colors in {path}")
    return colors


def floyd_steinberg(image: Image, palette: list[tuple[int, int, int]]) -> Image:
    width, height, pixels = image
    labs = [_cielab(entry) for entry in palette]
    work = [[0.0, 0.0, 0.0, 0.0] for _ in range(width * height)]
    for i in range(width * height):
        src = i * 4
        work[i][0] = float(pixels[src])
        work[i][1] = float(pixels[src + 1])
        work[i][2] = float(pixels[src + 2])
        work[i][3] = float(pixels[src + 3])
    out = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            i = y * width + x
            if work[i][3] < 128:
                continue
            sample = (
                int(min(255, max(0, round(work[i][0])))),
                int(min(255, max(0, round(work[i][1])))),
                int(min(255, max(0, round(work[i][2])))),
            )
            chosen = nearest_palette_color(sample, palette, labs)
            out[i * 4 : i * 4 + 4] = bytes((chosen[0], chosen[1], chosen[2], 255))
            error = [sample[channel] - chosen[channel] for channel in range(3)]
            for dx, dy, weight in ((1, 0, 7), (-1, 1, 3), (0, 1, 5), (1, 1, 1)):
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                    continue
                j = ny * width + nx
                if work[j][3] < 128:
                    continue
                for channel in range(3):
                    work[j][channel] += error[channel] * weight / 16
    return width, height, out


def _apply_palette_lab(image: Image, palette: list[tuple[int, int, int]]) -> Image:
    width, height, pixels = image
    out = bytearray(pixels)
    labs = [_cielab(entry) for entry in palette]
    cache: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    for i in range(0, len(out), 4):
        if out[i + 3] == 0:
            out[i : i + 4] = b"\x00\x00\x00\x00"
            continue
        color = (out[i], out[i + 1], out[i + 2])
        mapped = cache.get(color)
        if mapped is None:
            mapped = nearest_palette_color(color, palette, labs)
            cache[color] = mapped
        out[i : i + 3] = bytes(mapped)
    return width, height, out


def select_palette(
    image: Image,
    palette: list[tuple[int, int, int]],
    mode: str,
) -> list[tuple[int, int, int]]:
    """Restrict ``palette`` to ramps. ``all`` keeps every color.

    ``auto`` opens the ramp of each palette color that covers at least 1.5% of
    the figure (and at least 3 pixels), plus outline and any real gold trim.
    A comma-separated list opens those ramps by name.
    """
    if not palette or mode in ("", "all"):
        return palette
    cleaned = mode.strip().lower()
    known = {color for colors in RAMP_GROUPS.values() for color in colors}
    if cleaned != "auto":
        names = [part.strip() for part in cleaned.split(",") if part.strip()]
        unknown = [name for name in names if name not in RAMP_GROUPS]
        if unknown:
            known_names = ", ".join(RAMP_GROUPS)
            raise SystemExit(f"unknown ramp {unknown[0]!r}; expected {known_names}, auto, or all")
        chosen: list[tuple[int, int, int]] = []
        seen: set[tuple[int, int, int]] = set()
        for name in names:
            for color in RAMP_GROUPS[name]:
                if color in palette and color not in seen:
                    chosen.append(color)
                    seen.add(color)
        if not chosen:
            raise SystemExit("none of the requested ramps are in the palette")
        return chosen

    if sum(1 for color in palette if color in known) < 8:
        return palette
    counts: Counter[tuple[int, int, int]] = Counter()
    _width, _height, pixels = image
    opaque = 0
    labs = [_cielab(entry) for entry in palette]
    cache: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    for i in range(0, len(pixels), 4):
        if pixels[i + 3] == 0:
            continue
        opaque += 1
        color = (pixels[i], pixels[i + 1], pixels[i + 2])
        mapped = cache.get(color)
        if mapped is None:
            mapped = nearest_palette_color(color, palette, labs)
            cache[color] = mapped
        counts[mapped] += 1
    if opaque == 0:
        return palette
    threshold = max(3, int(round(opaque * 0.015)))
    opened = {"outline"}
    for color, count in counts.items():
        if count >= threshold or (color in GOLD_COLORS and count >= 3):
            opened.update(_COLOR_RAMPS.get(color, ()))
    if counts and opened == {"outline"}:
        opened.update(_COLOR_RAMPS.get(counts.most_common(1)[0][0], ()))
    chosen = []
    seen = set()
    for name in sorted(opened):
        for color in RAMP_GROUPS.get(name, ()):
            if color in palette and color not in seen:
                chosen.append(color)
                seen.add(color)
    return chosen or palette


def _majority(colors: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    counts = Counter(colors)
    return max(colors, key=lambda color: (counts[color], -colors.index(color)))


def _established_ramps(pixels: bytearray | bytes, width: int, height: int) -> set[str]:
    """Ramps that actually cover this sprite, plus outline.

    A handful of violet or rust pixels on blue steel is not a material. Gold
    trim is allowed through ``GOLD_COLORS`` even when the ramp is small.
    """
    counts: Counter[str] = Counter()
    opaque = 0
    for y in range(height):
        for x in range(width):
            i = (y * width + x) * 4
            if pixels[i + 3] == 0:
                continue
            opaque += 1
            color = (pixels[i], pixels[i + 1], pixels[i + 2])
            for ramp in _COLOR_RAMPS.get(color, ()):
                counts[ramp] += 1
    if opaque == 0:
        return set(RAMP_GROUPS)
    threshold = max(4, int(round(opaque * 0.08)))
    established = {"outline"}
    for ramp, count in counts.items():
        if count >= threshold:
            established.add(ramp)
    return established


def _ramp_allowed(color: tuple[int, int, int], established: set[str]) -> bool:
    if color in OUTLINE_COLORS or color in GOLD_COLORS:
        return True
    ramps = _COLOR_RAMPS.get(color)
    if not ramps:
        return True
    return bool(ramps & established)


def _scrub_foreign(pixels: bytearray, width: int, height: int) -> int:
    """Repaint islands whose ramp is not actually used by the sprite.

    Reads neighbours from the previous pass so a rust-colored belt shrinks
    from its gold and steel edges instead of surviving as a solid run.
    """
    established = _established_ramps(pixels, width, height)
    replaced = 0
    current = pixels
    for _ in range(8):
        nxt = bytearray(current)
        changed = 0
        for y in range(height):
            for x in range(width):
                i = (y * width + x) * 4
                if current[i + 3] == 0:
                    continue
                color = (current[i], current[i + 1], current[i + 2])
                if _ramp_allowed(color, established):
                    continue
                neighbors: list[tuple[int, int, int]] = []
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if nx < 0 or ny < 0 or nx >= width or ny >= height:
                            continue
                        j = (ny * width + nx) * 4
                        if current[j + 3] == 0:
                            continue
                        neighbor = (current[j], current[j + 1], current[j + 2])
                        if _ramp_allowed(neighbor, established):
                            neighbors.append(neighbor)
                if not neighbors:
                    continue
                nxt[i : i + 3] = bytes(_majority(neighbors))
                changed += 1
        current = nxt
        replaced += changed
        if changed == 0:
            break
    if current is not pixels:
        pixels[:] = current
    return replaced


def despeckle(image: Image) -> tuple[Image, int]:
    """Replace isolated 1px colors with the majority neighbour.

    A pixel is isolated when none of its eight neighbours share its color.
    The 1px outline (void / abyss, or a dark rim on transparency), 1px gold
    trim, and 1px speculars that are a lighter step of the neighbour ramp
    stay put. A second pass drops small islands on a ramp the sprite does
    not actually use (violet specks and rust on blue steel) without eating
    a real violet robe or a gold buckle.
    """
    width, height, pixels = image
    out = bytearray(pixels)
    replaced = 0
    for y in range(height):
        for x in range(width):
            i = (y * width + x) * 4
            if pixels[i + 3] == 0:
                continue
            color = (pixels[i], pixels[i + 1], pixels[i + 2])
            neighbors: list[tuple[int, int, int]] = []
            touches_clear = False
            same = False
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if nx < 0 or ny < 0 or nx >= width or ny >= height:
                        touches_clear = True
                        continue
                    j = (ny * width + nx) * 4
                    if pixels[j + 3] == 0:
                        touches_clear = True
                        continue
                    neighbor = (pixels[j], pixels[j + 1], pixels[j + 2])
                    neighbors.append(neighbor)
                    if neighbor == color:
                        same = True
            if same or not neighbors:
                continue
            if _keep_isolated(color, neighbors, touches_clear):
                continue
            majority = _majority(neighbors)
            out[i : i + 3] = bytes(majority)
            replaced += 1
    replaced += _scrub_foreign(out, width, height)
    return (width, height, out), replaced


def _keep_isolated(
    color: tuple[int, int, int],
    neighbors: list[tuple[int, int, int]],
    touches_clear: bool,
) -> bool:
    if color in OUTLINE_COLORS or color in GOLD_COLORS:
        return True
    majority = _majority(neighbors)
    if touches_clear and _cielab(color)[0] + 8.0 < _cielab(majority)[0]:
        return True
    if not (_COLOR_RAMPS.get(color, set()) & _COLOR_RAMPS.get(majority, set())):
        return False
    return _cielab(color)[0] >= _cielab(majority)[0] + 8.0


def quantize(image: Image, palette: list[tuple[int, int, int]] | None, dither: str) -> Image:
    if not palette:
        _zero_transparent(image)
        return image
    if dither == "floyd":
        image = floyd_steinberg(image, palette)
    else:
        image = _apply_palette_lab(image, palette)
    _zero_transparent(image)
    return image


def contact_sheet(frames: list[Image], scale: int) -> Image:
    if not frames:
        raise ValueError("contact sheet has no frames")
    scale = max(1, scale)
    scaled = [ASSETS.resize_nearest(frame, frame[0] * scale, frame[1] * scale) for frame in frames]
    columns = min(8, len(scaled))
    rows = (len(scaled) + columns - 1) // columns
    cell_w = max(frame[0] for frame in scaled)
    cell_h = max(frame[1] for frame in scaled)
    gap = max(2, scale)
    margin = gap
    width = margin * 2 + columns * cell_w + (columns - 1) * gap
    height = margin * 2 + rows * cell_h + (rows - 1) * gap
    dark = (9, 10, 24, 255)
    light = (25, 26, 50, 255)
    pixels = bytearray(width * height * 4)
    checker = max(4, scale)
    for y in range(height):
        for x in range(width):
            color = dark if ((x // checker) + (y // checker)) % 2 == 0 else light
            i = (y * width + x) * 4
            pixels[i : i + 4] = bytes(color)
    for index, frame in enumerate(scaled):
        col = index % columns
        row = index // columns
        origin_x = margin + col * (cell_w + gap) + (cell_w - frame[0]) // 2
        origin_y = margin + row * (cell_h + gap) + (cell_h - frame[1]) // 2
        fw, fh, fp = frame
        for y in range(fh):
            for x in range(fw):
                src = (y * fw + x) * 4
                if fp[src + 3] == 0:
                    continue
                dst = ((origin_y + y) * width + (origin_x + x)) * 4
                pixels[dst : dst + 4] = fp[src : src + 4]
    return width, height, pixels


def _output_names(stem: str, count: int, names: str, force_index: bool, index_width: int) -> list[str]:
    if names:
        chosen = [ASSETS._safe_stem(part) for part in names.split(",") if part.strip()]
        if len(chosen) != count:
            raise SystemExit(f"--names has {len(chosen)} entries but ingest produced {count} frame(s)")
        return chosen
    if count == 1 and not force_index:
        return [ASSETS._safe_stem(stem)]
    width = max(1, index_width)
    return [f"{ASSETS._safe_stem(stem)}_{index:0{width}d}" for index in range(count)]


def _destination(art_root: Path, kind: str, faction: str) -> Path:
    if kind == "ui":
        if faction:
            raise SystemExit("--faction is only used with --kind units")
        return art_root / "ui"
    return ASSETS.output_directory(art_root, kind, faction)


def process(args: argparse.Namespace) -> list[Path]:
    source = Path(args.input)
    if not source.is_file():
        raise SystemExit(f"input not found: {source}")
    kind = args.kind
    if kind not in KINDS:
        raise SystemExit(f"kind must be one of {', '.join(KINDS)}")
    faction = args.faction
    if kind == "units" and not faction:
        raise SystemExit("--faction is required for --kind units (azure, crimson, verdant, shared, monsters)")
    size = ASSETS.parse_size(args.size, "--size") if args.size else DEFAULT_SIZE[kind]
    canvas = ASSETS.parse_size(args.canvas, "--canvas") if args.canvas else size
    anchor_mode = args.anchor or DEFAULT_ANCHOR[kind]
    if anchor_mode not in {"feet", "center", "top"}:
        raise SystemExit("--anchor must be feet, center, or top")
    grid = ASSETS.parse_size(args.grid, "--grid") if args.grid else None
    separate = args.separate
    if separate == "auto":
        separate = "grid" if grid else "components"
    if separate == "grid" and grid is None:
        raise SystemExit("--separate grid needs --grid WxH")

    image = read_image(source)
    key, key_note = resolve_key(image, args.key, args.tolerance)
    print(f"  {key_note}")
    keyed, removed = remove_background(image, key, args.tolerance, despill=not args.no_despill)
    print(f"  keyed out {removed} background pixels")
    frames = slice_components(keyed, separate, grid, args.margin, args.spacing, args.min_area, args.connectivity)
    if not frames:
        raise SystemExit("no objects left after background removal (check --key, --tolerance, and --min-area)")
    print(f"  {len(frames)} frame(s) via {separate}")

    palette = load_palette(Path(args.palette) if args.palette else None, args.colors)
    if palette is None and args.colors > 0:
        collected: list[tuple[int, int, int]] = []
        for frame in frames:
            collected.extend(ASSETS.opaque_colors(frame))
        palette = ASSETS.median_cut(collected, args.colors) if collected else None
    outline_color = _parse_hex(args.outline_color) if args.outline_color else (4, 4, 12)
    if args.outline and palette and outline_color not in palette:
        outline_color = min(palette, key=lambda color: color[0] + color[1] + color[2])

    pad = 2 if args.outline else 0
    max_w = canvas[0] - pad
    max_h = canvas[1] - pad
    if max_w < 1 or max_h < 1:
        raise SystemExit("--canvas is too small for a 1px outline")

    art_root = Path(args.art_root) if args.art_root else ART_ROOT
    project_root = art_root.parent
    stem = args.name or source.stem
    names = _output_names(stem, len(frames), args.names, args.force_index, args.index_width)
    destination = _destination(art_root, kind, faction)
    ramp_mode = getattr(args, "ramps", "all") or "all"
    finished: list[Image] = []
    written: list[Path] = []
    for name, frame in zip(names, frames):
        reduced, note = downscale_content(frame, max_w, max_h, args.pixel_grid)
        print(f"  {name}: {note}")
        active = palette
        if palette is not None:
            active = select_palette(reduced, palette, ramp_mode)
            if len(active) != len(palette):
                print(f"  {name}: ramps {ramp_mode} -> {len(active)} palette colors")
            reduced = quantize(reduced, active, args.dither)
            if args.dither != "floyd":
                reduced, speckles = despeckle(reduced)
                if speckles:
                    print(f"  {name}: despeckled {speckles} isolated pixel(s)")
        if args.outline:
            reduced = add_outline(reduced, outline_color)
            if palette is not None and args.dither != "floyd":
                reduced = quantize(reduced, active if active is not None else palette, "none")
        placed = anchor(reduced, canvas[0], canvas[1], anchor_mode, args.foot_pad)
        _zero_transparent(placed)
        target = destination / f"{name}.png"
        ASSETS.write_png(target, placed)
        if not args.no_import:
            ASSETS.write_godot_import(target, project_root)
        try:
            display = target.relative_to(project_root)
        except ValueError:
            display = target
        print(f"  OK {display}")
        finished.append(placed)
        written.append(target)

    if not args.no_preview:
        preview_path = Path(args.preview) if args.preview else PREVIEWS / f"{kind}_{faction + '_' if faction else ''}{ASSETS._safe_stem(stem)}_contact.png"
        sheet = contact_sheet(finished, args.preview_scale)
        ASSETS.write_png(preview_path, sheet)
        print(f"  contact {preview_path}")
    return written


def build_synthetic_sheet() -> Image:
    """Painterly stand-in: two blocky figures on magenta, 8px cells, noise, fringe."""
    scale = 8
    width, height = 112, 80
    image = _blank(width, height)
    pixels = image[2]
    magenta = (255, 0, 255, 255)
    for i in range(0, len(pixels), 4):
        pixels[i : i + 4] = bytes(magenta)

    def paint_block(origin_x: int, origin_y: int, color: tuple[int, int, int], mixed: bool = False) -> None:
        seed = origin_x * 131 + origin_y * 17 + color[0]
        for by in range(scale):
            for bx in range(scale):
                local = (seed + bx * 13 + by * 29) & 0x7FFFFFFF
                amp = 3
                jitter = (local % (amp * 2 + 1)) - amp
                red, green, blue = color
                if mixed and bx >= 6:
                    red, green, blue = 20, 20, 220
                    jitter = (local % 5) - 2
                pixels[((origin_y + by) * width + origin_x + bx) * 4 : ((origin_y + by) * width + origin_x + bx) * 4 + 4] = bytes(
                    (
                        max(0, min(255, red + jitter)),
                        max(0, min(255, green + (jitter // 2))),
                        max(0, min(255, blue + (jitter // 3))),
                        255,
                    )
                )

    red = (200, 92, 36)
    blue = (71, 94, 161)
    bone = (159, 146, 129)
    green = (109, 140, 54)
    rows_a = [
        [red, blue, red, blue],
        [blue, red, blue, red],
        [red, bone, red, bone],
        [bone, red, bone, red],
        [red, blue, red, blue],
        [blue, red, blue, red],
    ]
    # Mark the mixed cell at local (1, 1): 75% red, 25% blue, so mode-pool must keep red.
    for row, colors in enumerate(rows_a):
        for col, color in enumerate(colors):
            paint_block(16 + col * scale, 16 + row * scale, color, mixed=(row == 1 and col == 1))
    rows_b = [
        [green, red, green],
        [red, green, red],
        [green, bone, green],
        [bone, green, bone],
        [green, red, green],
    ]
    for row, colors in enumerate(rows_b):
        for col, color in enumerate(colors):
            paint_block(72 + col * scale, 16 + row * scale, color, mixed=False)
    # Magenta fringe just outside each figure, close enough to key away.
    for x, y in ((15, 20), (48, 20), (71, 20), (96, 20), (20, 15), (20, 64)):
        pixels[(y * width + x) * 4 : (y * width + x) * 4 + 4] = bytes((255, 32, 255, 255))
    # Semi-transparent fringe and a one-pixel speck that must not become a frame.
    pixels[(40 * width + 60) * 4 : (40 * width + 60) * 4 + 4] = bytes((255, 0, 255, 90))
    pixels[(10 * width + 100) * 4 : (10 * width + 100) * 4 + 4] = bytes((255, 220, 40, 255))
    # Contaminated edge pixel on figure A. Dist to magenta is inside the despill band.
    pixels[(20 * width + 16) * 4 : (20 * width + 16) * 4 + 4] = bytes((230, 80, 230, 255))
    return image


def _palette_colors(image: Image) -> set[tuple[int, int, int]]:
    return set(ASSETS.opaque_colors(image))


def command_self_test(_args: argparse.Namespace) -> None:
    palette = load_palette(DEFAULT_PALETTE, 0)
    if palette is None or not 32 <= len(palette) <= 48:
        raise SystemExit(f"master palette should hold 32 to 48 colors, got {0 if palette is None else len(palette)}")
    required = {(4, 4, 12), (71, 94, 161), (200, 92, 36), (15, 102, 115), (250, 250, 235), (181, 148, 101)}
    missing = required - set(palette)
    if missing:
        raise SystemExit(f"master palette is missing {sorted(missing)}")
    fixture = PROJECT / "tools" / "fixtures" / "ai_ingest_sheet.png"
    synthetic = build_synthetic_sheet()
    if not fixture.is_file():
        raise SystemExit(f"missing synthetic fixture {fixture}")
    if ASSETS.read_png(fixture)[:2] != synthetic[:2] or bytes(ASSETS.read_png(fixture)[2]) != bytes(synthetic[2]):
        raise SystemExit("tools/fixtures/ai_ingest_sheet.png does not match the synthetic generator")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        art = root / "art"
        project = root / "proj"
        # art_root's parent is the Godot project root for .import paths.
        art = project / "art"
        preview = root / "contact.png"
        written = process(
            argparse.Namespace(
                input=str(fixture),
                kind="units",
                faction="azure",
                name="warrior_idle",
                size="16x28",
                canvas="",
                anchor="feet",
                foot_pad=0,
                key="FF00FF",
                tolerance=40,
                no_despill=False,
                separate="auto",
                grid="",
                margin=0,
                spacing=0,
                min_area=24,
                connectivity=8,
                # The fixture is a 32px-wide figure on an 8px lattice. That cell
                # is larger than 1/8 of the figure, so auto-estimate rejects it.
                # The mode-pool check below forces the lattice the fixture was built on.
                pixel_grid=8,
                palette=str(DEFAULT_PALETTE),
                colors=0,
                dither="none",
                outline=False,
                outline_color="",
                force_index=False,
                index_width=1,
                names="",
                art_root=str(art),
                preview=str(preview),
                no_preview=False,
                preview_scale=4,
                no_import=False,
            )
        )
        if len(written) != 2:
            raise SystemExit(f"expected 2 separated figures, got {len(written)}")
        first = ASSETS.read_png(art / "units" / "azure" / "warrior_idle_0.png")
        second = ASSETS.read_png(art / "units" / "azure" / "warrior_idle_1.png")
        if (first[0], first[1]) != (16, 28) or (second[0], second[1]) != (16, 28):
            raise SystemExit("canvas is not 16x28")
        allowed = set(palette)
        for frame in (first, second):
            colors = _palette_colors(frame)
            if not colors <= allowed:
                raise SystemExit(f"quantized frame left the master palette: {colors - allowed}")
            pixels = frame[2]
            for i in range(0, len(pixels), 4):
                alpha = pixels[i + 3]
                if alpha not in (0, 255):
                    raise SystemExit("semi-transparent fringe survived")
                if alpha == 0 and bytes(pixels[i : i + 4]) != b"\x00\x00\x00\x00":
                    raise SystemExit("transparent pixel kept RGB fringe")
                if alpha == 255 and pixels[i] > 200 and pixels[i + 2] > 200 and pixels[i + 1] < 80:
                    raise SystemExit("magenta spill survived")
        box = _opaque_bbox(first)
        if box != (6, 22, 10, 28):
            raise SystemExit(f"feet/grid placement expected opaque box (6,22,10,28), got {box}")
        second_box = _opaque_bbox(second)
        if second_box != (6, 23, 9, 28):
            raise SystemExit(f"second figure expected opaque box (6,23,9,28), got {second_box}")
        gpl = _read_gpl(PROJECT / "art" / "style" / "palette.gpl")
        hex_colors = _read_hex(PROJECT / "art" / "style" / "palette.hex")
        if gpl != palette or hex_colors != palette:
            raise SystemExit("palette.png, palette.gpl, and palette.hex disagree")
        # Local (1, 1) of the 4x6 figure sits at canvas (7, 23) and must be the
        # mode of the red block, crimson_hot #C85C24, not a blend toward the blue noise.
        mode_pixel = tuple(first[2][(23 * 16 + 7) * 4 : (23 * 16 + 7) * 4 + 3])
        if mode_pixel != (200, 92, 36):
            raise SystemExit(f"mode-pool diluted the red block to {mode_pixel}")
        import_text = (art / "units" / "azure" / "warrior_idle_0.png.import").read_text(encoding="utf-8")
        for needle in ("mipmaps/generate=false", "compress/mode=0", "detect_3d/compress_to=0", "process/fix_alpha_border=false"):
            if needle not in import_text:
                raise SystemExit(f".import missing {needle}")
        sheet = ASSETS.read_png(preview)
        if sheet[0] < 16 * 4 * 2:
            raise SystemExit("contact sheet is too small to show both frames")

        green = _blank(48, 40)
        gp = green[2]
        for i in range(0, len(gp), 4):
            gp[i : i + 4] = bytes((0, 170, 0, 255))
        for y in range(12, 28):
            for x in range(16, 32):
                gp[(y * 48 + x) * 4 : (y * 48 + x) * 4 + 4] = bytes((220, 120, 40, 255))
        green_path = root / "green.png"
        ASSETS.write_png(green_path, green)
        fallback_art = project / "fallback"
        process(
            argparse.Namespace(
                input=str(green_path),
                kind="fx",
                faction="",
                name="spark",
                size="8x8",
                canvas="",
                anchor="center",
                foot_pad=0,
                key="FF00FF",
                tolerance=40,
                no_despill=False,
                separate="none",
                grid="",
                margin=0,
                spacing=0,
                min_area=8,
                connectivity=4,
                pixel_grid=4,
                palette=str(DEFAULT_PALETTE),
                colors=0,
                dither="none",
                outline=True,
                outline_color="04040C",
                force_index=False,
                index_width=1,
                names="",
                art_root=str(fallback_art),
                preview=str(root / "green_contact.png"),
                no_preview=False,
                preview_scale=2,
                no_import=False,
            )
        )
        sparked = ASSETS.read_png(fallback_art / "fx" / "spark.png")
        if (sparked[0], sparked[1]) != (8, 8):
            raise SystemExit("outline canvas is not 8x8")
        outline_px = tuple(sparked[2][(1 * 8 + 1) * 4 : (1 * 8 + 1) * 4 + 3])
        if outline_px != (4, 4, 12):
            raise SystemExit(f"outline pass did not paint void on the silhouette, got {outline_px}")
        center = tuple(sparked[2][(3 * 8 + 3) * 4 : (3 * 8 + 3) * 4 + 3])
        if center != (213, 107, 30):
            raise SystemExit(f"green-screen sprite quantized to {center}, expected fire #D56B1E")

        tiled = _blank(32, 16)
        tp = tiled[2]
        for y in range(16):
            for x in range(32):
                color = (71, 94, 161, 255) if x < 16 else (200, 92, 36, 255)
                tp[(y * 32 + x) * 4 : (y * 32 + x) * 4 + 4] = bytes(color)
        tile_path = root / "grid.png"
        ASSETS.write_png(tile_path, tiled)
        process(
            argparse.Namespace(
                input=str(tile_path),
                kind="tiles",
                faction="",
                name="cell",
                size="4x4",
                canvas="",
                anchor="center",
                foot_pad=0,
                key="none",
                tolerance=40,
                no_despill=True,
                separate="grid",
                grid="16x16",
                margin=0,
                spacing=0,
                min_area=1,
                connectivity=4,
                pixel_grid=4,
                palette=str(DEFAULT_PALETTE),
                colors=0,
                dither="none",
                outline=False,
                outline_color="",
                force_index=True,
                index_width=1,
                names="",
                art_root=str(project / "gridart"),
                preview="",
                no_preview=True,
                preview_scale=1,
                no_import=True,
            )
        )
        left = ASSETS.read_png(project / "gridart" / "tiles" / "cell_0.png")
        right = ASSETS.read_png(project / "gridart" / "tiles" / "cell_1.png")
        if tuple(left[2][0:3]) != (71, 94, 161) or tuple(right[2][0:3]) != (200, 92, 36):
            raise SystemExit("grid slice did not keep the two cell colors")
    _extra_self_tests(palette)
    print("ai ingest self-test passed")


def _put(image: Image, x: int, y: int, color: tuple[int, int, int], alpha: int = 255) -> None:
    width = image[0]
    image[2][(y * width + x) * 4 : (y * width + x) * 4 + 4] = bytes((color[0], color[1], color[2], alpha))


def _at(image: Image, x: int, y: int) -> tuple[int, int, int, int]:
    width = image[0]
    i = (y * width + x) * 4
    return tuple(image[2][i : i + 4])  # type: ignore[return-value]


def _fill(width: int, height: int, color: tuple[int, int, int]) -> Image:
    image = _blank(width, height)
    paint = bytes((color[0], color[1], color[2], 255))
    pixels = image[2]
    for i in range(0, len(pixels), 4):
        pixels[i : i + 4] = paint
    return image


def _clean_grid_body(cell: int = 8, cols: int = 10, rows: int = 12) -> Image:
    image = _blank(cell * cols, cell * rows)
    colors = ((71, 94, 161), (122, 154, 213), (181, 148, 101))
    for row in range(rows):
        for col in range(cols):
            color = colors[(row + col) % len(colors)]
            for by in range(cell):
                for bx in range(cell):
                    jitter = ((bx + by + row) % 5) - 2
                    _put(
                        image,
                        col * cell + bx,
                        row * cell + by,
                        (
                            max(0, min(255, color[0] + jitter)),
                            max(0, min(255, color[1] + jitter // 2)),
                            color[2],
                        ),
                    )
    return image


def _false_period_body() -> Image:
    """Gradient figure with a bright column every 60px. That period is not a texel."""
    width, height = 180, 260
    image = _blank(width, height)
    for y in range(height):
        for x in range(width):
            if x % 60 == 0:
                color = (250, 250, 250)
            else:
                color = (30 + (x * 3) % 80, 40 + (y % 37), 110 + (x % 50))
            _put(image, x, y, color)
    return image


def _extra_self_tests(palette: list[tuple[int, int, int]]) -> None:
    if DEFAULT_SIZE["units"] != (32, 48) or DEFAULT_SIZE["tiles"] != (32, 32):
        raise SystemExit(f"default canvases drifted: {DEFAULT_SIZE}")
    azure = (71, 94, 161)
    ice = (144, 163, 208)
    violet = (177, 83, 231)
    gold = (181, 148, 101)
    gold_dark = (99, 76, 46)
    void = (4, 4, 12)
    cyan = (15, 102, 115)
    bone = (159, 146, 129)
    fire = (213, 107, 30)
    ember = (164, 70, 36)

    gold_samples = {
        (181, 148, 101): gold,
        (186, 142, 64): gold,
        (170, 130, 60): gold,
        (160, 120, 50): gold,
        (150, 110, 40): gold,
        (99, 76, 46): gold_dark,
        (80, 60, 30): gold_dark,
        (130, 100, 50): gold_dark,
    }
    for sample, expected in gold_samples.items():
        got = nearest_palette_color(sample, palette)
        if got != expected:
            raise SystemExit(f"CIELAB mapped {sample} to {got}, expected gold {expected}")
    warm = {
        (213, 107, 30): fire,
        (220, 120, 40): fire,
        (200, 90, 40): (200, 92, 36),
        (180, 70, 30): ember,
        (20, 80, 140): (60, 75, 140),
    }
    for sample, expected in warm.items():
        got = nearest_palette_color(sample, palette)
        if got != expected:
            raise SystemExit(f"CIELAB mapped {sample} to {got}, expected {expected}")

    speck = _fill(7, 7, azure)
    _put(speck, 3, 3, violet)
    cleaned, count = despeckle(speck)
    if _at(cleaned, 3, 3)[:3] != azure or count != 1:
        raise SystemExit("despeckle left a violet speck on azure steel")
    glint = _fill(7, 7, azure)
    _put(glint, 3, 3, ice)
    kept, count = despeckle(glint)
    if _at(kept, 3, 3)[:3] != ice or count != 0:
        raise SystemExit("despeckle ate the 1px ice specular")
    buckle = _fill(7, 7, azure)
    _put(buckle, 3, 3, gold)
    trimmed, _count = despeckle(buckle)
    if _at(trimmed, 3, 3)[:3] != gold:
        raise SystemExit("despeckle ate the 1px gold trim")
    _put(buckle, 3, 3, gold_dark)
    trimmed, _count = despeckle(buckle)
    if _at(trimmed, 3, 3)[:3] != gold_dark:
        raise SystemExit("despeckle ate gold_dark trim")
    eye = _fill(7, 7, bone)
    _put(eye, 3, 3, void)
    eyed, _count = despeckle(eye)
    if _at(eyed, 3, 3)[:3] != void:
        raise SystemExit("despeckle ate the 1px void eye")
    cyan_speck = _fill(7, 7, azure)
    _put(cyan_speck, 3, 3, cyan)
    cleaned, _count = despeckle(cyan_speck)
    if _at(cleaned, 3, 3)[:3] != azure:
        raise SystemExit("despeckle left a cyan speck on azure steel")
    core = _fill(4, 4, azure)
    outlined = add_outline(core, void)
    outlined, _count = despeckle(outlined)
    if _at(outlined, 0, 2)[:3] != void or _at(outlined, 2, 2)[:3] != azure:
        raise SystemExit("despeckle ate the 1px void outline")
    belt = _fill(16, 12, azure)
    for x in range(6, 11):
        _put(belt, x, 6, (47, 15, 14))
    belt, belt_count = despeckle(belt)
    if any(_at(belt, x, 6)[:3] == (47, 15, 14) for x in range(6, 11)) or belt_count < 5:
        raise SystemExit("rust belt on azure steel survived despeckle")
    if _at(belt, 1, 1)[:3] != azure:
        raise SystemExit("foreign-ramp scrub repainted the azure field")

    field = _fill(24, 24, azure)
    for y in range(4, 8):
        for x in range(4, 8):
            _put(field, x, y, (186, 142, 64))
    _put(field, 20, 20, violet)
    restricted = select_palette(field, palette, "auto")
    if gold not in restricted or azure not in restricted:
        raise SystemExit("auto ramps dropped azure or gold")
    if violet in restricted or cyan in restricted:
        raise SystemExit(f"auto ramps kept a noise ramp: violet={violet in restricted} cyan={cyan in restricted}")
    snapped = despeckle(quantize(field, restricted, "none"))[0]
    if violet in _palette_colors(snapped) or cyan in _palette_colors(snapped):
        raise SystemExit("auto-ramp quantize left violet or cyan on the azure figure")
    if gold not in _palette_colors(snapped):
        raise SystemExit("auto-ramp quantize lost the gold block")
    named = select_palette(field, palette, "azure,gold")
    if violet in named or fire in named:
        raise SystemExit("explicit ramps included colors outside azure and gold")
    if gold not in named or azure not in named:
        raise SystemExit("explicit azure,gold ramps missed a requested color")

    lattice = _clean_grid_body()
    if _max_plausible_cell(lattice[0], lattice[1]) < 8:
        raise SystemExit("clean-grid fixture is too small for an 8px cell")
    found = estimate_pixel_grid(lattice, 0)
    if found is None or found[0] != 8:
        raise SystemExit(f"clean 8px lattice estimated as {found}")
    if estimate_pixel_grid(lattice, 1) is not None:
        raise SystemExit("--pixel-grid 1 still estimated a lattice")
    pooled, note = downscale_content(lattice, 32, 48, 1)
    if not note.startswith("no plausible pixel grid") or pooled[0] < 24:
        raise SystemExit(f"--pixel-grid 1 did not mode-pool to the canvas ({note}, {pooled[0]}x{pooled[1]})")
    gridded, grid_note = downscale_content(lattice, 32, 48, 0)
    if gridded[0] != 10 or "pixel grid 8px" not in grid_note:
        raise SystemExit(f"auto grid should stay 10px wide, got {grid_note} {gridded[0]}x{gridded[1]}")

    false_grid = _false_period_body()
    if _max_plausible_cell(false_grid[0], false_grid[1]) >= 60:
        raise SystemExit("false-period fixture does not make a 60px cell implausible")
    bogus = estimate_pixel_grid(false_grid, 0)
    if bogus is not None:
        raise SystemExit(f"implausible grid was accepted: {bogus}")
    fallback, fallback_note = downscale_content(false_grid, 30, 46, 0)
    if fallback[0] < 16 or fallback[1] < 24 or not fallback_note.startswith("no plausible pixel grid"):
        raise SystemExit(f"false grid collapsed the figure ({fallback_note}, {fallback[0]}x{fallback[1]})")
    skipped, skipped_note = downscale_content(false_grid, 30, 46, 1)
    if not skipped_note.startswith("no plausible pixel grid") or (skipped[0], skipped[1]) != (fallback[0], fallback[1]):
        raise SystemExit("--pixel-grid 1 disagreed with the rejected-grid fallback")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest AI-generated art into the Living Dungeon palette")
    sub = parser.add_subparsers(dest="cmd", required=True)
    ingest = sub.add_parser("ingest", help="Key, slice, mode-pool, quantize, and write art/")
    ingest.add_argument("--input", required=True, help="Raw AI image. PNG, or any file ffmpeg can convert.")
    ingest.add_argument("--kind", required=True, choices=KINDS)
    ingest.add_argument("--faction", default="", help="Required for units: azure, crimson, verdant, shared, monsters")
    ingest.add_argument("--name", default="", help="Output stem. Defaults to the file name.")
    ingest.add_argument("--size", default="", help="Target pixel size WxH. Defaults from the kind (units 32x48, tiles 32x32).")
    ingest.add_argument("--canvas", default="", help="Pad size WxH. Defaults to --size.")
    ingest.add_argument("--anchor", default="", help="feet, center, or top. Units and buildings default to feet.")
    ingest.add_argument("--foot-pad", type=int, default=0, help="Pixels between the baseline and the canvas edge.")
    ingest.add_argument("--key", default="FF00FF", help="Chroma key RRGGBB, auto, or none. Default FF00FF.")
    ingest.add_argument("--tolerance", type=int, default=40, help="Euclidean distance that still counts as the key.")
    ingest.add_argument("--no-despill", action="store_true", help="Keep key-colored spill on the silhouette.")
    ingest.add_argument("--separate", default="auto", choices=("auto", "components", "grid", "none"))
    ingest.add_argument("--grid", default="", help="Slice the source into WxH cells before downscale.")
    ingest.add_argument("--margin", type=int, default=0)
    ingest.add_argument("--spacing", type=int, default=0)
    ingest.add_argument("--min-area", type=int, default=24, help="Drop specks smaller than this many source pixels.")
    ingest.add_argument("--connectivity", type=int, default=8, choices=(4, 8))
    ingest.add_argument(
        "--pixel-grid",
        type=int,
        default=0,
        help="Source cell size. 0 estimates and rejects a cell larger than 1/8 of the figure. 1 means no grid, mode-pool to the canvas. N>1 forces an N-pixel cell.",
    )
    ingest.add_argument("--palette", default="", help="PNG, GPL, or HEX palette. Default art/style/palette.png.")
    ingest.add_argument(
        "--ramps",
        default="all",
        help="Palette ramps: all, auto (ramps used by the figure's dominant colors), or a comma-separated list such as azure,gold.",
    )
    ingest.add_argument("--colors", type=int, default=0, help="Median-cut to N colors instead of the master palette.")
    ingest.add_argument("--dither", default="none", choices=("none", "floyd"))
    ingest.add_argument("--outline", action="store_true", help="Add a 1px outside outline.")
    ingest.add_argument("--outline-color", default="", help="Outline RRGGBB. Default void #04040C, snapped to the palette.")
    ingest.add_argument("--force-index", action="store_true", help="Write name_0.png even when there is one frame.")
    ingest.add_argument("--index-width", type=int, default=1, help="Digits in the frame suffix. 1 writes _0; 2 writes _00.")
    ingest.add_argument("--names", default="", help="Comma-separated output stems, one per frame.")
    ingest.add_argument("--art-root", default="", help="Destination art directory.")
    ingest.add_argument("--preview", default="", help="Contact-sheet PNG path.")
    ingest.add_argument("--no-preview", action="store_true")
    ingest.add_argument("--preview-scale", type=int, default=4)
    ingest.add_argument("--no-import", action="store_true")
    ingest.set_defaults(func=process)

    test = sub.add_parser("self-test", help="Run the synthetic ingest fixture")
    test.set_defaults(func=command_self_test)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
