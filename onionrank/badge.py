"""Rank badges that domain owners can embed on their own sites.

PNG is the default because Tor Browser's "Safest" level blocks SVG images;
SVG is offered as a sharper alternative.
"""
import io
from functools import lru_cache
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

BG = (6, 10, 9)
LINE = (31, 74, 63)
GREEN = (62, 230, 160)
GOLD = (255, 162, 58)
MUTE = (95, 130, 120)
W, H = 220, 44


def label(rank):
    return f"#{rank:02d}" if rank else "listed"


@lru_cache(maxsize=4)
def _font(size):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def png(rank, scale=2):
    """Render the badge as PNG bytes (drawn at 2x, so it stays crisp)."""
    s = scale
    img = Image.new("RGB", (W * s, H * s), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W * s - 1, H * s - 1], outline=LINE, width=s)
    d.rectangle([0, 0, 3 * s, H * s], fill=GREEN)
    d.text((14 * s, 8 * s), "ONIONRANK", font=_font(10 * s), fill=MUTE)
    d.text((14 * s, 21 * s), "ranked on tor", font=_font(10 * s), fill=GREEN)
    big = label(rank)
    f = _font(20 * s)
    tw = d.textlength(big, font=f)
    d.text((W * s - 12 * s - tw, 11 * s), big, font=f, fill=GOLD if rank and rank <= 3 else GREEN)
    out = io.BytesIO()
    img.save(out, "PNG", optimize=True)
    return out.getvalue()


def svg(rank):
    big = escape(label(rank))
    color = "#ffa23a" if rank and rank <= 3 else "#3ee6a0"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="OnionRANK {big}">
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" fill="#060a09" stroke="#1f4a3f"/>
<rect width="3" height="{H}" fill="#3ee6a0"/>
<g font-family="DejaVu Sans Mono,Menlo,Consolas,monospace" font-weight="bold">
<text x="14" y="17" font-size="10" fill="#5f8278">ONIONRANK</text>
<text x="14" y="31" font-size="10" fill="#3ee6a0">ranked on tor</text>
<text x="{W - 12}" y="29" font-size="20" fill="{color}" text-anchor="end">{big}</text>
</g></svg>"""
