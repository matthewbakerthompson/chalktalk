"""
The chalktalk mark, drawn here so the package carries no image files: a chalk
circle for the player and a gold route breaking to the corner, on the turf.

It is the browser tab's icon while `chalk design` runs, and the shortcut's
icon after `chalk shortcut`.
"""
from __future__ import annotations

import functools
import math
import struct
import zlib

FIELD = (0x22, 0x50, 0x3a)    # the turf theme's field
CHALK = (0xf4, 0xf1, 0xe8)    # the offense's chalk
GOLD = (0xfb, 0xbf, 0x24)     # the ball's ring


def _png(width: int, height: int, rows: list[bytes]) -> bytes:
    """A minimal RGBA PNG."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))
    raw = b"".join(b"\x00" + r for r in rows)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def _segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def _route_segments() -> list[tuple[float, float, float, float]]:
    """A player's route: up the field, then breaking to the corner, arrowhead on."""
    p0, p1, p2 = (0.30, 0.585), (0.30, 0.40), (0.70, 0.235)
    segs = [(*p0, *p1), (*p1, *p2)]
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    n = math.hypot(dx, dy)
    ux, uy = dx / n, dy / n
    for sign in (1, -1):
        a = math.radians(28) * sign
        wx = ux * math.cos(a) - uy * math.sin(a)
        wy = ux * math.sin(a) + uy * math.cos(a)
        segs.append((p2[0], p2[1], p2[0] - wx * 0.13, p2[1] - wy * 0.13))
    return segs


@functools.lru_cache(maxsize=8)
def png(size: int, full_bleed: bool = False, content: float = 0.80) -> bytes:
    """
    The mark as a PNG, `size` pixels square. Drawn with distance fields so the
    edges are smooth at any size; rounded corners unless `full_bleed`.
    """
    ring_c, ring_r, ring_w = (0.30, 0.70), 0.105, 0.045
    route_w = 0.068
    segs = _route_segments()
    radius = 0.2                            # corner radius, when not full bleed
    rows = []
    for j in range(size):
        row = bytearray()
        for i in range(size):
            u, v = (i + 0.5) / size, (j + 0.5) / size
            if full_bleed:
                alpha = 1.0
            else:
                qx = abs(u - 0.5) - (0.5 - radius)
                qy = abs(v - 0.5) - (0.5 - radius)
                d = (math.hypot(max(qx, 0.0), max(qy, 0.0))
                     + min(max(qx, qy), 0.0) - radius)
                alpha = max(0.0, min(1.0, 0.5 - d * size))
            r, g, b = FIELD
            # the drawing, scaled into the safe area and balanced around the centre
            x = (u - 0.5) / content + 0.5 - 0.05
            y = (v - 0.5) / content + 0.5 + 0.02
            px = 1.0 / (size * content)      # one pixel, in drawing units
            if 0.1 < x < 0.9 and 0.1 < y < 0.9:
                d = min(_segment(x, y, *s) for s in segs)
                cov = max(0.0, min(1.0, (route_w / 2 - d) / px + 0.5))
                if cov:
                    r, g, b = (c + (gc - c) * cov for c, gc in zip((r, g, b), GOLD))
                dc = math.hypot(x - ring_c[0], y - ring_c[1])
                inside = max(0.0, min(1.0, (ring_r - ring_w / 2 - dc) / px + 0.5))
                if inside:                   # the circle is open: turf inside it
                    r, g, b = (c + (fc - c) * inside for c, fc in zip((r, g, b), FIELD))
                cov = max(0.0, min(1.0, (ring_w / 2 - abs(dc - ring_r)) / px + 0.5))
                if cov:
                    r, g, b = (c + (cc - c) * cov for c, cc in zip((r, g, b), CHALK))
            row += bytes((int(r + 0.5), int(g + 0.5), int(b + 0.5), int(alpha * 255 + 0.5)))
        rows.append(bytes(row))
    return _png(size, size, rows)


def ico(sizes: tuple[int, ...] = (16, 32, 48, 256)) -> bytes:
    """A Windows .ico holding the mark at each size, as PNGs (Windows Vista and later)."""
    images = [png(s) for s in sizes]
    head = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    for s, data in zip(sizes, images):
        dim = 0 if s >= 256 else s                  # 0 means 256 in an icon directory
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    return head + entries + b"".join(images)


__all__ = ["png", "ico"]
