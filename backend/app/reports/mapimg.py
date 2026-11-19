"""Static location diagram for reports: subject and numbered comps on a
distance grid. Drawn locally (no map tiles), so the report carries no third-party
basemap licensing."""

from __future__ import annotations

import io
import math

from PIL import Image, ImageDraw, ImageFont


def _font(size: int):
    for name in ("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1 ships a scalable default font
    except TypeError:
        return ImageFont.load_default()


def render_map_png(subject: tuple[float, float], comps: list[tuple[float, float]], color: str = "#1F4E79",
                   width: int = 1000, height: int = 560) -> bytes:
    lat0, lon0 = subject
    kx = 69.0 * math.cos(math.radians(lat0))  # miles per degree longitude
    pts = [((lon - lon0) * kx, (lat - lat0) * 69.0) for lat, lon in comps]
    extent = max([0.25] + [max(abs(x), abs(y)) for x, y in pts]) * 1.25
    pad = 40
    scale = min((width - 2 * pad) / (2 * extent), (height - 2 * pad) / (2 * extent))
    cx, cy = width / 2, height / 2

    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    f_small, f_label = _font(15), _font(17)
    # distance rings
    step = 0.25 if extent <= 1 else 0.5
    r = step
    while r <= extent * 1.01:
        rad = r * scale
        d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline="#d0d7de", width=1)
        d.text((cx + rad + 4, cy - 10), f"{r:g} mi", fill="#6e7781", font=f_small)
        r += step
    d.line([pad, cy, width - pad, cy], fill="#eaeef2")
    d.line([cx, pad, cx, height - pad], fill="#eaeef2")
    d.polygon([(width - pad - 7, pad + 4), (width - pad, pad - 12), (width - pad + 7, pad + 4)], fill="#57606a")
    d.text((width - pad - 5, pad - 34), "N", fill="#57606a", font=f_label)
    # comps
    for i, (x, y) in enumerate(pts, 1):
        px, py = cx + x * scale, cy - y * scale
        d.ellipse([px - 13, py - 13, px + 13, py + 13], fill=color, outline="white", width=2)
        tw = d.textlength(str(i), font=f_label)
        d.text((px - tw / 2, py - 10), str(i), fill="white", font=f_label)
    # subject
    s = 16
    star = []
    for k in range(10):
        ang = math.pi / 2 + k * math.pi / 5
        rr = s if k % 2 == 0 else s * 0.45
        star.append((cx + rr * math.cos(ang), cy - rr * math.sin(ang)))
    d.polygon(star, fill="#C62828", outline="white")
    d.text((cx + 18, cy + 8), "Subject", fill="#C62828", font=f_label)
    d.text((pad, height - pad + 8), "Relative positions from county address points. Not to survey accuracy.",
           fill="#6e7781", font=f_small)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
