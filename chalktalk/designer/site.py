"""
chalktalk.designer.site — the designer as an installable web app.

`build_site(out)` writes a folder any static host can serve: GitHub Pages,
Netlify, Cloudflare Pages, a school web server.

    index.html              the designer, plus a manifest link and a service worker
    manifest.webmanifest    name, colours and icons, so browsers offer "Install"
    sw.js                   caches the app so it opens with no connection
    *.png                   icons, drawn here, so the repo carries no image files

The designer template is untouched and stays one self-contained file; the site
only wraps it. The service worker caches the app itself. Plays never leave the
device: the designer keeps a working copy in the browser and saves to files the
coach chooses, on their own disk or drive.

    chalk site --out site
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import zlib
from typing import Optional

from . import build

APP_NAME = "chalktalk"
APP_BG = "#0c0f0d"            # the designer's graphite, oklch(0.165 0.006 160)
FIELD = (0x22, 0x50, 0x3a)    # the turf theme's field
CHALK = (0xf4, 0xf1, 0xe8)    # the offense's chalk
GOLD = (0xfb, 0xbf, 0x24)     # the ball's ring

ICONS = {
    # name: (size, full bleed, content scale)
    "icon-192.png": (192, False, 0.80),
    "icon-512.png": (512, False, 0.80),
    "icon-maskable-512.png": (512, True, 0.62),   # content inside the safe zone
    "apple-touch-icon.png": (180, True, 0.80),    # iOS rounds the corners itself
}

_HEAD = """<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="{bg}">
<link rel="icon" type="image/png" sizes="192x192" href="icon-192.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{name}">
<meta name="description" content="Draw football plays, build playbooks, print call sheets and wristbands. Works offline; your files stay on your device.">
"""

_REGISTER = ('<script>if ("serviceWorker" in navigator) '
             'navigator.serviceWorker.register("sw.js").catch(function () {});</script>\n')

_SW = """// chalktalk offline cache, written by chalktalk.designer.site.build_site.
// It caches the app. Plays live in the browser's storage and in the files the
// coach saves; none of it passes through here.
const CACHE = "chalktalk-{version}";
const FILES = {files};

self.addEventListener("install", event => {{
  event.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
}});

self.addEventListener("activate", event => {{
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k.startsWith("chalktalk-") && k !== CACHE)
                                    .map(k => caches.delete(k))))
      .then(() => self.clients.claim()));
}});

// Cache first, so the sideline with no signal still opens the app. A new
// version installs in the background and is used from the next launch.
self.addEventListener("fetch", event => {{
  const req = event.request;
  if (req.method !== "GET" || new URL(req.url).origin !== self.location.origin) return;
  // Offline, a page load falls back to the app; anything else fails honestly.
  event.respondWith(
    caches.match(req, {{ignoreSearch: true}})
      .then(hit => hit || fetch(req).catch(() =>
        req.mode === "navigate" ? caches.match("index.html") : Response.error())));
}});
"""


# ── icons ─────────────────────────────────────────────────────────────────────

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


def draw_icon(size: int, full_bleed: bool, content: float) -> bytes:
    """
    The mark: a chalk circle for the player and a gold route with an arrowhead,
    on the turf. Drawn with distance fields so the edges are smooth at any size.
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
            # background, with rounded corners unless the platform masks it
            if full_bleed:
                alpha = 1.0
            else:
                qx = abs(u - 0.5) - (0.5 - radius)
                qy = abs(v - 0.5) - (0.5 - radius)
                d = (math.hypot(max(qx, 0.0), max(qy, 0.0))
                     + min(max(qx, qy), 0.0) - radius)
                alpha = max(0.0, min(1.0, 0.5 - d * size))
            r, g, b = FIELD
            # the drawing, scaled into the safe area
            # (shifted so the ring and the arrow balance around the centre)
            x = (u - 0.5) / content + 0.5 - 0.05
            y = (v - 0.5) / content + 0.5 + 0.02
            px = 1.0 / (size * content)      # one pixel, in drawing units
            if 0.1 < x < 0.9 and 0.1 < y < 0.9:
                d = min(_segment(x, y, *s) for s in segs)
                cov = max(0.0, min(1.0, (route_w / 2 - d) / px + 0.5))
                if cov:
                    r = r + (GOLD[0] - r) * cov
                    g = g + (GOLD[1] - g) * cov
                    b = b + (GOLD[2] - b) * cov
                dc = math.hypot(x - ring_c[0], y - ring_c[1])
                inside = max(0.0, min(1.0, (ring_r - ring_w / 2 - dc) / px + 0.5))
                if inside:                   # the circle is open: turf inside it
                    r = r + (FIELD[0] - r) * inside
                    g = g + (FIELD[1] - g) * inside
                    b = b + (FIELD[2] - b) * inside
                cov = max(0.0, min(1.0, (ring_w / 2 - abs(dc - ring_r)) / px + 0.5))
                if cov:
                    r = r + (CHALK[0] - r) * cov
                    g = g + (CHALK[1] - g) * cov
                    b = b + (CHALK[2] - b) * cov
            row += bytes((int(r + 0.5), int(g + 0.5), int(b + 0.5), int(alpha * 255 + 0.5)))
        rows.append(bytes(row))
    return _png(size, size, rows)


# ── the site ──────────────────────────────────────────────────────────────────

def manifest() -> dict:
    return {
        "name": APP_NAME,
        "short_name": APP_NAME,
        "description": ("Draw football plays, build playbooks, print call sheets and "
                        "wristbands. Works offline; your files stay on your device."),
        "id": "./",
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "background_color": APP_BG,
        "theme_color": APP_BG,
        "categories": ["sports", "productivity", "education"],
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png",
             "purpose": "maskable"},
        ],
    }


def site_index(level: str = "nfl", theme: str = "turf") -> str:
    """The designer with the manifest, icons and service worker attached."""
    html = build(level=level, theme=theme)
    marker = "</title>\n"
    assert html.count(marker) == 1, "the designer template lost its <title>"
    html = html.replace(marker, marker + _HEAD.format(bg=APP_BG, name=APP_NAME), 1)
    assert html.rstrip().endswith("</html>")
    cut = html.rindex("</body>")
    return html[:cut] + _REGISTER + html[cut:]


def build_site(out: str, level: str = "nfl", theme: str = "turf",
               icons: Optional[dict[str, bytes]] = None) -> str:
    """Write the installable site to `out` and return its absolute path."""
    out = os.path.abspath(out)
    os.makedirs(out, exist_ok=True)
    files: dict[str, bytes] = {
        "index.html": site_index(level=level, theme=theme).encode("utf-8"),
        "manifest.webmanifest": (json.dumps(manifest(), indent=2) + "\n").encode("utf-8"),
    }
    if icons is None:
        icons = {name: draw_icon(*spec) for name, spec in ICONS.items()}
    files.update(icons)

    # The cache name moves with the content, so a new build replaces the old one.
    digest = hashlib.sha256(_SW.encode("utf-8"))
    for name in sorted(files):
        digest.update(name.encode() + b"\0" + files[name])
    cached = ["./"] + sorted(files)
    files["sw.js"] = _SW.format(version=digest.hexdigest()[:12],
                                files=json.dumps(cached)).encode("utf-8")

    for name, data in files.items():
        with open(os.path.join(out, name), "wb") as fh:
            fh.write(data)
    return out


__all__ = ["build_site", "site_index", "manifest", "draw_icon", "ICONS", "APP_BG"]
