#!/usr/bin/env python3
"""Slice, resize, and palette-quantize pixel art for Living Dungeon.

Writes a Godot 4.4 art/ tree and .import sidecars. The running game loads
those textures. This tool slices and quantizes; it does not change gameplay.

No third-party packages. PNG read/write is implemented here so a plain
Linux VM and GitHub Actions can run it with python3 only.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import sys
import tempfile
import zlib
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ART_ROOT = PROJECT / "art"
KINDS = ("tiles", "units", "buildings", "fx")
UID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
MAX_EDGE = 16384

Image = tuple[int, int, bytearray]  # width, height, RGBA bytes


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    distance_left = abs(estimate - left)
    distance_up = abs(estimate - up)
    distance_upper_left = abs(estimate - upper_left)
    if distance_left <= distance_up and distance_left <= distance_upper_left:
        return left
    if distance_up <= distance_upper_left:
        return up
    return upper_left


def _unfilter(filtered: bytes, height: int, row_bytes: int, bpp: int) -> bytes:
    expected = height * (row_bytes + 1)
    if len(filtered) != expected:
        raise ValueError(f"PNG scanlines are {len(filtered)} bytes, expected {expected}")
    out = bytearray(height * row_bytes)
    stride = row_bytes + 1
    for y in range(height):
        filter_type = filtered[y * stride]
        row = filtered[y * stride + 1 : (y + 1) * stride]
        previous = out[(y - 1) * row_bytes : y * row_bytes] if y else bytearray(row_bytes)
        current = bytearray(row_bytes)
        for i, value in enumerate(row):
            left = current[i - bpp] if i >= bpp else 0
            up = previous[i]
            upper_left = previous[i - bpp] if i >= bpp else 0
            if filter_type == 0:
                reconstructed = value
            elif filter_type == 1:
                reconstructed = (value + left) & 255
            elif filter_type == 2:
                reconstructed = (value + up) & 255
            elif filter_type == 3:
                reconstructed = (value + ((left + up) // 2)) & 255
            elif filter_type == 4:
                reconstructed = (value + _paeth(left, up, upper_left)) & 255
            else:
                raise ValueError(f"unsupported PNG filter {filter_type}")
            current[i] = reconstructed
        out[y * row_bytes : (y + 1) * row_bytes] = current
    return bytes(out)


def read_png(path: Path | str) -> Image:
    data = Path(path).read_bytes() if not isinstance(path, (bytes, bytearray)) else bytes(path)
    return read_png_bytes(data)


def read_png_bytes(data: bytes) -> Image:
    signature = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(signature):
        raise ValueError("missing PNG signature")
    offset = len(signature)
    width = height = bit_depth = color_type = None
    idat = bytearray()
    palette: list[tuple[int, int, int]] = []
    transparency: bytes | None = None
    while offset + 8 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        offset += 4
        tag = data[offset : offset + 4]
        offset += 4
        chunk = data[offset : offset + length]
        offset += length
        crc = struct.unpack(">I", data[offset : offset + 4])[0]
        offset += 4
        if (zlib.crc32(tag + chunk) & 0xFFFFFFFF) != crc:
            raise ValueError(f"bad CRC for PNG chunk {tag!r}")
        if tag == b"IHDR":
            width, height, bit_depth, color_type, compression, png_filter, interlace = struct.unpack(">IIBBBBB", chunk)
            if compression != 0 or png_filter != 0:
                raise ValueError("unsupported PNG compression or filter method")
            if interlace != 0:
                raise ValueError("interlaced PNG is not supported; re-export without Adam7")
            if bit_depth != 8:
                raise ValueError(f"only 8-bit PNG is supported (got bit depth {bit_depth})")
            if not (1 <= width <= MAX_EDGE and 1 <= height <= MAX_EDGE):
                raise ValueError(f"PNG dimensions {width}x{height} are out of range")
        elif tag == b"PLTE":
            if len(chunk) % 3 != 0:
                raise ValueError("PLTE chunk length is not a multiple of 3")
            palette = [tuple(chunk[i : i + 3]) for i in range(0, len(chunk), 3)]  # type: ignore[misc]
        elif tag == b"tRNS":
            transparency = bytes(chunk)
        elif tag == b"IDAT":
            idat.extend(chunk)
        elif tag == b"IEND":
            break
    if width is None or height is None or color_type is None:
        raise ValueError("PNG is missing IHDR")
    if not idat:
        raise ValueError("PNG is missing IDAT")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
    if channels is None:
        raise ValueError(f"unsupported PNG color type {color_type}")
    raw = zlib.decompress(bytes(idat))
    samples = _unfilter(raw, height, width * channels, channels)
    rgba = bytearray(width * height * 4)
    if color_type == 6:
        rgba[:] = samples
    elif color_type == 2:
        key = None
        if transparency is not None:
            if len(transparency) < 6:
                raise ValueError("tRNS chunk for RGB is too short")
            key = tuple(struct.unpack(">HHH", transparency[:6]))
        for i in range(width * height):
            r, g, b = samples[i * 3 : i * 3 + 3]
            alpha = 0 if key == (r, g, b) else 255
            rgba[i * 4 : i * 4 + 4] = bytes((r, g, b, alpha))
    elif color_type == 0:
        key_gray = None
        if transparency is not None:
            if len(transparency) < 2:
                raise ValueError("tRNS chunk for gray is too short")
            key_gray = struct.unpack(">H", transparency[:2])[0]
        for i, gray in enumerate(samples):
            alpha = 0 if key_gray == gray else 255
            rgba[i * 4 : i * 4 + 4] = bytes((gray, gray, gray, alpha))
    elif color_type == 4:
        for i in range(width * height):
            gray, alpha = samples[i * 2 : i * 2 + 2]
            rgba[i * 4 : i * 4 + 4] = bytes((gray, gray, gray, alpha))
    elif color_type == 3:
        if not palette:
            raise ValueError("indexed PNG is missing PLTE")
        alphas = [255] * len(palette)
        if transparency is not None:
            for i, alpha in enumerate(transparency[: len(palette)]):
                alphas[i] = alpha
        for i, index in enumerate(samples):
            if index >= len(palette):
                raise ValueError(f"palette index {index} is out of range")
            r, g, b = palette[index]
            rgba[i * 4 : i * 4 + 4] = bytes((r, g, b, alphas[index]))
    return width, height, rgba


def write_png(path: Path, image: Image, filter_mode: int = 0) -> None:
    width, height, rgba = image
    if len(rgba) != width * height * 4:
        raise ValueError("RGBA buffer does not match image dimensions")
    raw = _filter_rgba(width, height, rgba, filter_mode)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    blob = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)


def _filter_rgba(width: int, height: int, rgba: bytes | bytearray, mode: int) -> bytes:
    bpp = 4
    stride = width * bpp
    raw = bytearray()
    previous = bytearray(stride)
    for y in range(height):
        row = rgba[y * stride : (y + 1) * stride]
        raw.append(mode)
        current = bytearray(stride)
        for i, original in enumerate(row):
            left = current[i - bpp] if i >= bpp else 0
            up = previous[i]
            upper_left = previous[i - bpp] if i >= bpp else 0
            if mode == 0:
                filtered = original
            elif mode == 1:
                filtered = (original - left) & 255
            elif mode == 2:
                filtered = (original - up) & 255
            elif mode == 3:
                filtered = (original - ((left + up) // 2)) & 255
            elif mode == 4:
                filtered = (original - _paeth(left, up, upper_left)) & 255
            else:
                raise ValueError(f"unsupported encode filter {mode}")
            current[i] = original
            raw.append(filtered)
        previous = current
    return bytes(raw)


def crop(image: Image, x: int, y: int, width: int, height: int) -> Image:
    src_w, _src_h, src = image
    out = bytearray(width * height * 4)
    for row in range(height):
        start = ((y + row) * src_w + x) * 4
        out[row * width * 4 : (row + 1) * width * 4] = src[start : start + width * 4]
    return width, height, out


def slice_grid(image: Image, cell_w: int, cell_h: int, margin: int = 0, spacing: int = 0) -> tuple[list[Image], int, int]:
    width, height, _pixels = image
    frames: list[Image] = []
    y = margin
    rows = 0
    cols = 0
    while y + cell_h <= height - margin:
        x = margin
        row_cols = 0
        while x + cell_w <= width - margin:
            frames.append(crop(image, x, y, cell_w, cell_h))
            row_cols += 1
            x += cell_w + spacing
        if row_cols == 0:
            break
        cols = row_cols
        rows += 1
        y += cell_h + spacing
    if not frames:
        raise ValueError(f"grid {cell_w}x{cell_h} does not fit in {width}x{height} with margin {margin}")
    return frames, cols, rows


def resize_nearest(image: Image, new_w: int, new_h: int) -> Image:
    width, height, pixels = image
    if new_w == width and new_h == height:
        return image
    if new_w < 1 or new_h < 1:
        raise ValueError("resize target must be at least 1x1")
    out = bytearray(new_w * new_h * 4)
    for y in range(new_h):
        src_y = min(height - 1, y * height // new_h)
        for x in range(new_w):
            src_x = min(width - 1, x * width // new_w)
            src_i = (src_y * width + src_x) * 4
            dst_i = (y * new_w + x) * 4
            out[dst_i : dst_i + 4] = pixels[src_i : src_i + 4]
    return new_w, new_h, out


def opaque_colors(image: Image) -> list[tuple[int, int, int]]:
    _w, _h, pixels = image
    seen: set[tuple[int, int, int]] = set()
    ordered: list[tuple[int, int, int]] = []
    for i in range(0, len(pixels), 4):
        if pixels[i + 3] == 0:
            continue
        color = (pixels[i], pixels[i + 1], pixels[i + 2])
        if color not in seen:
            seen.add(color)
            ordered.append(color)
    return ordered


def palette_from_image(image: Image) -> list[tuple[int, int, int]]:
    colors = opaque_colors(image)
    if not colors:
        raise ValueError("palette image has no opaque pixels")
    return colors


def _channel_range(colors: list[tuple[int, int, int]]) -> tuple[int, int]:
    best_channel = 0
    best_span = -1
    for channel in range(3):
        values = [color[channel] for color in colors]
        span = max(values) - min(values)
        if span > best_span:
            best_span = span
            best_channel = channel
    return best_channel, best_span


def median_cut(colors: list[tuple[int, int, int]], count: int) -> list[tuple[int, int, int]]:
    unique = list(dict.fromkeys(colors))
    if count < 1:
        raise ValueError("--colors must be at least 1")
    if len(unique) <= count:
        return unique
    boxes: list[list[tuple[int, int, int]]] = [unique]
    while len(boxes) < count:
        boxes.sort(key=lambda box: _channel_range(box)[1], reverse=True)
        box = boxes.pop(0)
        channel, span = _channel_range(box)
        if span <= 0 or len(box) < 2:
            boxes.append(box)
            break
        box.sort(key=lambda color: color[channel])
        mid = len(box) // 2
        boxes.append(box[:mid])
        boxes.append(box[mid:])
    palette: list[tuple[int, int, int]] = []
    for box in boxes:
        if not box:
            continue
        palette.append(tuple(sum(color[channel] for color in box) // len(box) for channel in range(3)))  # type: ignore[misc]
    return palette


def apply_palette(image: Image, palette: list[tuple[int, int, int]]) -> Image:
    if not palette:
        return image
    width, height, pixels = image
    out = bytearray(pixels)
    cache: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    for i in range(0, len(out), 4):
        if out[i + 3] == 0:
            out[i : i + 4] = b"\x00\x00\x00\x00"
            continue
        color = (out[i], out[i + 1], out[i + 2])
        mapped = cache.get(color)
        if mapped is None:
            mapped = min(palette, key=lambda entry: (entry[0] - color[0]) ** 2 + (entry[1] - color[1]) ** 2 + (entry[2] - color[2]) ** 2)
            cache[color] = mapped
        out[i : i + 3] = bytes(mapped)
    return width, height, out


def parse_size(text: str, flag: str) -> tuple[int, int]:
    cleaned = text.lower().replace(",", "x")
    parts = cleaned.split("x")
    if len(parts) != 2:
        raise SystemExit(f"{flag} must look like 16x16, got {text!r}")
    try:
        width, height = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise SystemExit(f"{flag} must look like 16x16, got {text!r}") from exc
    if width < 1 or height < 1:
        raise SystemExit(f"{flag} must be at least 1x1")
    return width, height


def _safe_stem(name: str) -> str:
    cleaned = name.strip().replace("\\", "/")
    if not cleaned or cleaned.endswith("/") or "/" in cleaned or cleaned in {".", ".."}:
        raise SystemExit(f"invalid frame name {name!r}")
    if not all(ch.isalnum() or ch in "._-" for ch in cleaned):
        raise SystemExit(f"frame name {name!r} must use letters, digits, dot, underscore, or dash")
    return cleaned


def _safe_faction(name: str) -> str:
    if not name or not all(ch.islower() or ch.isdigit() or ch in "_-" for ch in name):
        raise SystemExit(f"faction {name!r} must be lowercase letters, digits, underscore, or dash (for example azure)")
    return name


def output_directory(art_root: Path, kind: str, faction: str) -> Path:
    if kind not in KINDS:
        raise SystemExit(f"kind must be one of {', '.join(KINDS)}")
    if kind == "units":
        return art_root / "units" / _safe_faction(faction)
    if faction:
        raise SystemExit("--faction is only used with --kind units")
    return art_root / kind


def frame_names(stem: str, count: int, names: str) -> list[str]:
    if names:
        chosen = [_safe_stem(part) for part in names.split(",") if part.strip()]
        if len(chosen) != count:
            raise SystemExit(f"--names has {len(chosen)} entries but the sheet produced {count} frame(s)")
        return chosen
    if count == 1:
        return [_safe_stem(stem)]
    return [f"{_safe_stem(stem)}_{index:02d}" for index in range(count)]


def _existing_uid(import_path: Path) -> str:
    if not import_path.exists():
        return ""
    for line in import_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("uid="):
            return stripped.split("=", 1)[1].strip().strip('"')
    return ""


def _new_uid(png_path: Path) -> str:
    digest = hashlib.sha1(png_path.as_posix().encode("utf-8")).hexdigest()
    chars = [UID_ALPHABET[int(digest[i : i + 2], 16) % len(UID_ALPHABET)] for i in range(0, 26, 2)]
    return "uid://" + "".join(chars)


def write_godot_import(png_path: Path, project_root: Path) -> None:
    try:
        relative = png_path.resolve().relative_to(project_root.resolve())
    except ValueError:
        print(f"  skip .import (outside Godot project): {png_path}", file=sys.stderr)
        return
    res_path = "res://" + relative.as_posix()
    imported = "res://.godot/imported/" + png_path.name + "-" + hashlib.md5(res_path.encode("utf-8")).hexdigest() + ".ctex"
    import_path = Path(str(png_path) + ".import")
    uid = _existing_uid(import_path) or _new_uid(png_path)
    # Godot 4.4 texture importer has no sampling-filter field. These params are
    # the 2D pixel preset: lossless, no mipmaps, no 3D VRAM recompress, and no
    # alpha-border bleed. Nearest sampling is applied at draw time.
    text = f"""; Pixel-art import for Godot 4.4. Lossless, no mipmaps, no 3D recompression.
; Sampling filter is nearest via CanvasItem.texture_filter (see tools/pixel_filter.gd).

[remap]

importer="texture"
type="CompressedTexture2D"
uid="{uid}"
path="{imported}"
metadata={{
"vram_texture": false
}}

[deps]

source_file="{res_path}"
dest_files=["{imported}"]

[params]

compress/mode=0
compress/high_quality=false
compress/lossy_quality=0.7
compress/hdr_compression=1
compress/normal_map=0
compress/channel_pack=0
mipmaps/generate=false
mipmaps/limit=-1
roughness/mode=0
roughness/src_normal=""
process/fix_alpha_border=false
process/premult_alpha=false
process/normal_map_invert_y=false
process/hdr_as_srgb=false
process/hdr_clamp_exposure=false
process/size_limit=0
detect_3d/compress_to=0
"""
    import_path.write_text(text, encoding="utf-8")


def prepare_frames(image: Image, grid: tuple[int, int] | None, margin: int, spacing: int) -> tuple[list[Image], str]:
    if grid is None:
        return [image], ""
    cell_w, cell_h = grid
    width, height = image[0], image[1]
    if width < cell_w or height < cell_h:
        raise ValueError(f"image {width}x{height} is smaller than grid {cell_w}x{cell_h}")
    frames, cols, rows = slice_grid(image, cell_w, cell_h, margin, spacing)
    used_w = margin * 2 + cols * cell_w + max(0, cols - 1) * spacing
    used_h = margin * 2 + rows * cell_h + max(0, rows - 1) * spacing
    note = ""
    if used_w != width or used_h != height:
        note = f"leftover pixels {width - used_w}x{height - used_h} were not sliced"
    if len(frames) == 1 and (width != cell_w or height != cell_h):
        note = note or "sheet produced a single cell"
    return frames, note


def process_image(
    source: Path,
    *,
    kind: str,
    faction: str,
    art_root: Path,
    project_root: Path,
    grid: tuple[int, int] | None,
    resize: tuple[int, int] | None,
    margin: int,
    spacing: int,
    names: str,
    palette: list[tuple[int, int, int]] | None,
    write_import: bool,
) -> list[Path]:
    image = read_png(source)
    frames, note = prepare_frames(image, grid, margin, spacing)
    if note:
        print(f"  note {source.name}: {note}")
    written: list[Path] = []
    destination = output_directory(art_root, kind, faction)
    for name, frame in zip(frame_names(source.stem, len(frames), names), frames):
        if resize is not None:
            frame = resize_nearest(frame, resize[0], resize[1])
        if palette is not None:
            frame = apply_palette(frame, palette)
        target = destination / f"{name}.png"
        write_png(target, frame)
        if write_import:
            write_godot_import(target, project_root)
        print(f"  OK {target.relative_to(project_root) if target.is_relative_to(project_root) else target}")
        written.append(target)
    return written


def _load_optional_palette(path: str) -> list[tuple[int, int, int]] | None:
    if not path:
        return None
    return palette_from_image(read_png(Path(path)))


def _shared_palette(frames: list[Image], colors: int, explicit: list[tuple[int, int, int]] | None) -> list[tuple[int, int, int]] | None:
    if explicit is not None:
        return explicit
    if colors <= 0:
        return None
    collected: list[tuple[int, int, int]] = []
    for frame in frames:
        collected.extend(opaque_colors(frame))
    if not collected:
        return None
    return median_cut(collected, colors)


def command_slice(args: argparse.Namespace) -> None:
    art_root = Path(args.art_root) if args.art_root else ART_ROOT
    project_root = art_root.parent
    source = Path(args.input)
    if not source.is_file():
        raise SystemExit(f"input not found: {source}")
    grid = parse_size(args.grid, "--grid") if args.grid else None
    resize = parse_size(args.resize, "--resize") if args.resize else None
    explicit = _load_optional_palette(args.palette)
    image = read_png(source)
    frames, _note = prepare_frames(image, grid, args.margin, args.spacing)
    palette = _shared_palette(frames, args.colors, explicit)
    if args.write_palette and palette is not None:
        _write_palette_strip(art_root / "palette.png", palette)
    process_image(
        source,
        kind=args.kind,
        faction=args.faction,
        art_root=art_root,
        project_root=project_root,
        grid=grid,
        resize=resize,
        margin=args.margin,
        spacing=args.spacing,
        names=args.names,
        palette=palette,
        write_import=not args.no_import,
    )


def _discover_batch(src: Path) -> list[tuple[str, str, Path]]:
    jobs: list[tuple[str, str, Path]] = []
    for kind in ("tiles", "buildings", "fx"):
        folder = src / kind
        if folder.is_dir():
            jobs.extend((kind, "", png) for png in sorted(folder.glob("*.png")))
    units = src / "units"
    if units.is_dir():
        for faction_dir in sorted(path for path in units.iterdir() if path.is_dir()):
            jobs.extend(("units", faction_dir.name, png) for png in sorted(faction_dir.glob("*.png")))
    return jobs


def _write_palette_strip(path: Path, palette: list[tuple[int, int, int]]) -> None:
    width = len(palette)
    pixels = bytearray()
    for color in palette:
        pixels.extend((*color, 255))
    write_png(path, (width, 1, pixels))
    print(f"  OK {path}")


def command_batch(args: argparse.Namespace) -> None:
    src = Path(args.src)
    if not src.is_dir():
        raise SystemExit(f"source directory not found: {src}")
    art_root = Path(args.art_root) if args.art_root else ART_ROOT
    project_root = art_root.parent
    jobs = _discover_batch(src)
    if not jobs:
        raise SystemExit(f"no PNG files under {src} (expected tiles/, units/<faction>/, buildings/, fx/)")
    grid = parse_size(args.grid, "--grid") if args.grid else None
    resize = parse_size(args.resize, "--resize") if args.resize else None
    explicit = _load_optional_palette(args.palette)
    if explicit is None and (src / "palette.png").is_file() and not args.ignore_src_palette:
        explicit = palette_from_image(read_png(src / "palette.png"))
        print(f"  palette {src / 'palette.png'} ({len(explicit)} colors)")
    loaded: list[tuple[str, str, Path, list[Image]]] = []
    all_frames: list[Image] = []
    for kind, faction, source in jobs:
        image = read_png(source)
        frames, note = prepare_frames(image, grid, args.margin, args.spacing)
        if note:
            print(f"  note {source.name}: {note}")
        loaded.append((kind, faction, source, frames))
        all_frames.extend(frames)
    palette = _shared_palette(all_frames, args.colors, explicit)
    if args.write_palette and palette is not None:
        _write_palette_strip(art_root / "palette.png", palette)
    for kind, faction, source, frames in loaded:
        destination = output_directory(art_root, kind, faction)
        for name, frame in zip(frame_names(source.stem, len(frames), ""), frames):
            if resize is not None:
                frame = resize_nearest(frame, resize[0], resize[1])
            if palette is not None:
                frame = apply_palette(frame, palette)
            target = destination / f"{name}.png"
            write_png(target, frame)
            if not args.no_import:
                write_godot_import(target, project_root)
            print(f"  OK {target}")


def analyze_png(path: Path) -> dict[str, float]:
    width, height, pixels = read_png(path)
    colors: set[tuple[int, int, int]] = set()
    bright = 0
    total = 0
    sum_l = 0
    for y in range(0, height, 3):
        for x in range(0, width, 3):
            i = (y * width + x) * 4
            r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
            colors.add((r >> 3, g >> 3, b >> 3))
            luminance = r + g + b
            sum_l += luminance
            if luminance > 140:
                bright += 1
            total += 1
    return {
        "w": width,
        "h": height,
        "colors": len(colors),
        "bright": bright,
        "mean": (sum_l / total) if total else 0.0,
    }


def screenshot_is_visible(stats: dict[str, float]) -> bool:
    # A flat clear or black frame has one color bucket. A drawn frame has terrain,
    # HUD panels, and at least a few bright faction or text pixels.
    return stats["w"] >= 320 and stats["h"] >= 480 and stats["colors"] >= 4 and stats["bright"] >= 8 and stats["mean"] > 12


def command_check_screenshot(args: argparse.Namespace) -> None:
    failed = False
    if not args.paths:
        raise SystemExit("check-screenshot needs at least one PNG")
    for raw in args.paths:
        path = Path(raw)
        try:
            stats = analyze_png(path)
        except Exception as exc:
            print(f"FAIL {path}: {exc}", file=sys.stderr)
            failed = True
            continue
        status = "OK" if screenshot_is_visible(stats) else "FAIL"
        print(
            f"{status} {path.name} {int(stats['w'])}x{int(stats['h'])} "
            f"colors={int(stats['colors'])} bright={int(stats['bright'])} mean={stats['mean']:.1f}"
        )
        if status != "OK":
            failed = True
    if failed:
        raise SystemExit("one or more screenshots look blank or unreadable")


def _solid(width: int, height: int, color: tuple[int, int, int, int]) -> Image:
    pixel = bytes(color)
    return width, height, bytearray(pixel * (width * height))


def _put(image: Image, x: int, y: int, color: tuple[int, int, int, int]) -> None:
    width, _height, pixels = image
    i = (y * width + x) * 4
    pixels[i : i + 4] = bytes(color)


def command_self_test(_args: argparse.Namespace) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        original = _solid(2, 2, (0, 0, 0, 0))
        _put(original, 0, 0, (10, 20, 30, 255))
        _put(original, 1, 0, (40, 50, 60, 255))
        _put(original, 0, 1, (70, 80, 90, 128))
        _put(original, 1, 1, (1, 2, 3, 0))
        for mode in (0, 1, 2, 3, 4):
            file_path = root / f"filter{mode}.png"
            write_png(file_path, original, filter_mode=mode)
            roundtrip = read_png(file_path)
            if roundtrip != original:
                raise SystemExit(f"PNG filter {mode} roundtrip mismatch")
        indexed = _indexed_png(root / "indexed.png")
        got = read_png(indexed)
        if got[0] != 2 or got[1] != 1 or bytes(got[2][:4]) != bytes((1, 2, 3, 255)) or bytes(got[2][4:]) != bytes((4, 5, 6, 0)):
            raise SystemExit("indexed PNG decode mismatch")
        sheet = _solid(32, 16, (0, 0, 0, 255))
        for x in range(16):
            for y in range(16):
                _put(sheet, x, y, (200, 10, 10, 255))
                _put(sheet, 16 + x, y, (10, 10, 220, 255))
        sheet_path = root / "sheet.png"
        write_png(sheet_path, sheet)
        art = root / "proj" / "art"
        project = root / "proj"
        project.mkdir()
        slice_args = argparse.Namespace(
            input=str(sheet_path),
            kind="tiles",
            faction="",
            art_root=str(art),
            grid="16x16",
            resize="8x8",
            margin=0,
            spacing=0,
            names="",
            palette="",
            colors=0,
            write_palette=False,
            no_import=False,
        )
        command_slice(slice_args)
        left = read_png(art / "tiles" / "sheet_00.png")
        right = read_png(art / "tiles" / "sheet_01.png")
        if left[0] != 8 or right[0] != 8:
            raise SystemExit("resize did not produce 8x8 frames")
        if bytes(left[2][:3]) != bytes((200, 10, 10)) or bytes(right[2][:3]) != bytes((10, 10, 220)):
            raise SystemExit("nearest slice did not preserve frame colors")
        import_text = (art / "tiles" / "sheet_00.png.import").read_text(encoding="utf-8")
        for needle in ("mipmaps/generate=false", "compress/mode=0", "detect_3d/compress_to=0", "process/fix_alpha_border=false"):
            if needle not in import_text:
                raise SystemExit(f".import missing {needle}")
        noisy = _solid(4, 4, (255, 0, 0, 255))
        _put(noisy, 1, 1, (0, 255, 0, 255))
        _put(noisy, 2, 2, (0, 0, 255, 255))
        _put(noisy, 3, 3, (255, 255, 0, 255))
        reduced = apply_palette(noisy, median_cut(opaque_colors(noisy), 2))
        if len(opaque_colors(reduced)) > 2:
            raise SystemExit("palette quantization kept more than 2 colors")
        block = resize_nearest(_solid(2, 2, (9, 8, 7, 255)), 4, 4)
        if block[0] != 4 or bytes(block[2][:4]) != bytes((9, 8, 7, 255)):
            raise SystemExit("nearest resize failed")
        visible = _solid(360, 640, (18, 24, 36, 255))
        for x in range(40, 120):
            for y in range(80, 200):
                _put(visible, x, y, (90, 70, 50, 255))
        for i, color in enumerate(((226, 196, 154, 255), (91, 189, 241, 255), (237, 105, 105, 255), (143, 216, 120, 255))):
            for dx in range(12):
                for dy in range(12):
                    _put(visible, 20 + i * 20 + dx, 40 + dy, color)
        visible_path = root / "visible.png"
        write_png(visible_path, visible)
        black_path = root / "black.png"
        write_png(black_path, _solid(360, 640, (0, 0, 0, 255)))
        if not screenshot_is_visible(analyze_png(visible_path)):
            raise SystemExit("visible synthetic screenshot was rejected")
        if screenshot_is_visible(analyze_png(black_path)):
            raise SystemExit("black screenshot was accepted")
        batch_src = root / "src"
        (batch_src / "units" / "azure").mkdir(parents=True)
        (batch_src / "fx").mkdir()
        write_png(batch_src / "units" / "azure" / "idle.png", _solid(8, 8, (12, 34, 56, 255)))
        write_png(batch_src / "fx" / "spark.png", _solid(4, 4, (240, 220, 40, 255)))
        command_batch(
            argparse.Namespace(
                src=str(batch_src),
                art_root=str(art),
                grid="",
                resize="4x4",
                margin=0,
                spacing=0,
                palette="",
                colors=8,
                write_palette=True,
                no_import=False,
                ignore_src_palette=False,
            )
        )
        idle = read_png(art / "units" / "azure" / "idle.png")
        if idle[0] != 4 or idle[1] != 4:
            raise SystemExit("batch resize failed for unit frame")
        if not (art / "palette.png").is_file():
            raise SystemExit("shared palette strip was not written")
    print("asset pipeline self-test passed")


def _indexed_png(path: Path) -> Path:
    palette = bytes((1, 2, 3, 4, 5, 6))
    trns = bytes((255, 0))
    raw = bytes((0, 0, 1))
    ihdr = struct.pack(">IIBBBBB", 2, 1, 8, 3, 0, 0, 0)
    blob = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"PLTE", palette)
        + _chunk(b"tRNS", trns)
        + _chunk(b"IDAT", zlib.compress(raw))
        + _chunk(b"IEND", b"")
    )
    path.write_bytes(blob)
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Living Dungeon pixel-art asset pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    slice_cmd = sub.add_parser("slice", help="Slice one sprite sheet or copy one image into art/")
    slice_cmd.add_argument("--input", required=True, help="Source PNG")
    slice_cmd.add_argument("--kind", required=True, choices=KINDS)
    slice_cmd.add_argument("--faction", default="", help="Required for --kind units, for example azure")
    slice_cmd.add_argument("--grid", default="", help="Cell size WxH in source pixels. Omit to keep the image whole.")
    slice_cmd.add_argument("--resize", default="", help="Nearest-neighbor output size WxH for each frame")
    slice_cmd.add_argument("--margin", type=int, default=0, help="Pixels to skip at the sheet border")
    slice_cmd.add_argument("--spacing", type=int, default=0, help="Pixels between cells")
    slice_cmd.add_argument("--names", default="", help="Comma-separated output names, one per frame")
    slice_cmd.add_argument("--palette", default="", help="PNG whose opaque colors are the shared palette")
    slice_cmd.add_argument("--colors", type=int, default=0, help="Quantize to N colors when --palette is omitted")
    slice_cmd.add_argument("--art-root", default="", help="Output art directory (default: projects/dungeon_godot/art)")
    slice_cmd.add_argument("--write-palette", action="store_true", help="Also write art/palette.png")
    slice_cmd.add_argument("--no-import", action="store_true", help="Do not write Godot .import sidecars")
    slice_cmd.set_defaults(func=command_slice)

    batch = sub.add_parser("batch", help="Process a source tree that mirrors art/")
    batch.add_argument("--src", required=True, help="Source root with tiles/, units/<faction>/, buildings/, fx/")
    batch.add_argument("--grid", default="")
    batch.add_argument("--resize", default="")
    batch.add_argument("--margin", type=int, default=0)
    batch.add_argument("--spacing", type=int, default=0)
    batch.add_argument("--palette", default="")
    batch.add_argument("--colors", type=int, default=0)
    batch.add_argument("--art-root", default="")
    batch.add_argument("--write-palette", action="store_true")
    batch.add_argument("--ignore-src-palette", action="store_true", help="Do not auto-use src/palette.png")
    batch.add_argument("--no-import", action="store_true")
    batch.set_defaults(func=command_batch)

    check = sub.add_parser("check-screenshot", help="Fail if a game screenshot is missing, tiny, or blank")
    check.add_argument("paths", nargs="+")
    check.set_defaults(func=command_check_screenshot)

    test = sub.add_parser("self-test", help="Run built-in pipeline checks")
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
