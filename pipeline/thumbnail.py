"""1280x720 thumbnail: background image (or colour) + big outlined text."""
from __future__ import annotations

import platform
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from .common import ASSETS, ROOT, Script

FONT_CANDIDATES = [
    "assets/fonts/thumbnail.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/impact.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _font(size: int, cfg: dict) -> ImageFont.FreeTypeFont:
    custom = cfg.get("thumbnail", {}).get("font")
    for cand in ([custom] if custom else []) + FONT_CANDIDATES:
        p = Path(cand)
        if not p.is_absolute():
            p = ROOT / p
        if p.exists():
            return ImageFont.truetype(str(p), size)
    print(f"  thumbnail: no bold font found on {platform.system()}, using default font")
    return ImageFont.load_default(size)


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        test = f"{cur} {wd}".strip()
        if draw.textlength(test, font=font) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def make_thumbnail(script: Script, cfg: dict) -> Path:
    W, H = 1280, 720
    tcfg = cfg.get("thumbnail", {})
    dst = script.out_dir / "thumbnail.png"
    manual = script.out_dir / "thumbnail_custom.png"
    if manual.exists():
        Image.open(manual).convert("RGB").resize((W, H)).save(dst)
        print("  thumbnail: using thumbnail_custom.png")
        return dst

    folder = ASSETS / (script.assets or "common")
    imgs = [p for p in sorted(folder.glob("*")) if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}] if folder.is_dir() else []
    if imgs:
        bg = ImageOps.fit(Image.open(imgs[0]).convert("RGB"), (W, H))
        bg = bg.filter(ImageFilter.GaussianBlur(1.5))
        shade = Image.new("RGB", (W, H), (0, 0, 0))
        bg = Image.blend(bg, shade, 0.35)
    else:
        bg = Image.new("RGB", (W, H), tuple(tcfg.get("background_rgb", [14, 63, 61])))

    text = (script.thumbnail_text or script.title).upper()
    draw = ImageDraw.Draw(bg)
    size = 150
    while size > 50:
        font = _font(size, cfg)
        lines = _wrap(draw, text, font, W - 140)
        if len(lines) <= 3:
            break
        size -= 10
    line_h = int(size * 1.08)
    y = (H - line_h * len(lines)) // 2
    fill = tuple(tcfg.get("text_rgb", [255, 210, 63]))
    for line in lines:
        draw.text((70, y), line, font=font, fill=fill, stroke_width=max(4, size // 14), stroke_fill=(0, 0, 0))
        y += line_h
    bg.save(dst, optimize=True)
    print(f"  thumbnail: {dst.name}")
    return dst
