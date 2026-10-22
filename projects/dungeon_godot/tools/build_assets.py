#!/usr/bin/env python3
"""Akudama Asset Pipeline. Build-time recovery of lossless PNG sprites.
No paid API, no credentials, no third-party Python dependencies.
Payload format: ZLIB compressed PNG bytes encoded as ASCII base85 text.
Each file in assets_payload/*.b85 becomes art/<basename>.png.
"""
from pathlib import Path
import base64
import zlib
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets_payload"
DEST = ROOT / "art"

def validate_png(data: bytes, name: str) -> None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{name}: missing PNG signature")
    width, height = struct.unpack(">II", data[16:24])
    if not (1 <= width <= 4096 and 1 <= height <= 4096):
        raise ValueError(f"{name}: invalid PNG dimensions {width}x{height}")
    print(f"    {width}x{height} ({len(data):,} bytes)")

def build() -> None:
    DEST.mkdir(exist_ok=True)
    files = sorted(SOURCE.glob("*.b85")) if SOURCE.exists() else []
    for item in files:
        encoded = "".join(item.read_text(encoding="ascii").split())
        try:
            raw = zlib.decompress(base64.b85decode(encoded))
            validate_png(raw, item.name)
            target = DEST / (item.stem + ".png")
            target.write_bytes(raw)
            print(f"  OK {target.relative_to(ROOT)}")
        except Exception as ex:
            print(f"  FAILED {item.name}: {ex}", file=sys.stderr)
            raise
    print(f"Asset pipeline complete: {len(files)} PNG file(s)")

if __name__ == "__main__":
    build()
