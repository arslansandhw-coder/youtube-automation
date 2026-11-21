"""Build the final MP4 with FFmpeg.

Layers, bottom to top:
1. backgrounds: your images/clips from assets/ (slow pan, darkened), or branded
   backgrounds made here, a different colour per section
2. channel logo (top corner) and a progress bar along the bottom
3. text drawn by libass (handles Urdu correctly): intro title, a title card at
   the start of each section, captions, and a subscribe outro
"""
from __future__ import annotations

import math
import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .common import ASSETS, ROOT, Script, media_duration, need, run

IMG = {".jpg", ".jpeg", ".png", ".webp"}
VID = {".mp4", ".mov", ".webm", ".mkv"}
AUD = {".mp3", ".wav", ".m4a"}

# brand palette: (top colour, bottom colour) per background variant
PALETTE = [((14, 63, 61), (6, 30, 30)), ((24, 44, 80), (8, 18, 36)), ((70, 32, 52), (28, 10, 22)),
           ((40, 60, 30), (14, 26, 10)), ((80, 52, 20), (34, 20, 6))]


def _media(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMG | VID)


def _ff_path(p: Path) -> str:
    """Path escaped for use inside an FFmpeg filter (Windows-safe)."""
    s = p.resolve().as_posix()
    return s.replace(":", r"\:").replace("'", r"\'")


# ---------- backgrounds ----------
def _brand_background(path: Path, w: int, h: int, variant: int) -> Path:
    """Gradient + soft glow + row of arches + stars. No text (text is drawn by libass)."""
    W, H = int(w * 1.12), int(h * 1.12)
    top, bot = PALETTE[variant % len(PALETTE)]
    im = Image.new("RGB", (W, H))
    px = ImageDraw.Draw(im)
    for y in range(H):
        f = y / (H - 1)
        px.line([(0, y), (W, y)], fill=tuple(int(top[i] * (1 - f) + bot[i] * f) for i in range(3)))
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([W * 0.25, H * 0.05, W * 0.75, H * 0.75], fill=90)
    im.paste((255, 210, 63), mask=glow.filter(ImageFilter.GaussianBlur(W // 8)).point(lambda v: v // 3))
    d = ImageDraw.Draw(im, "RGBA")
    rnd = random.Random(variant)
    for _ in range(int(W * H / 9000)):
        x, y, r = rnd.randrange(W), rnd.randrange(int(H * 0.7)), rnd.choice([1, 1, 2, 2, 3])
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 236, 170, rnd.randrange(50, 150)))
    aw, ah = W / 11, H * 0.32
    for i in range(12):
        cx, base, spring = i * aw + aw / 2, H, H - ah * 0.55
        rr = aw * 0.75
        left = cx - aw * 0.42
        pts = []
        for k in range(0, 91):
            a = math.radians(180 - k)
            x = left + rr * 0.56 + rr * 0.56 * math.cos(a)
            if x > cx:
                break
            pts.append((x, spring - rr * 0.56 * math.sin(a)))
        right = [(2 * cx - x, y) for x, y in reversed(pts)]
        d.line([(left, base), (left, spring)] + pts + right + [(2 * cx - left, spring), (2 * cx - left, base)],
               fill=(255, 210, 63, 60), width=max(2, w // 480))
    im.save(path, quality=92)
    return path


def _pan_clip(src: Path, seconds: float, dst: Path, w: int, h: int, fps: int, variant: int, darken: float) -> None:
    """Still image -> slow pan (cheap Ken Burns) with optional darkening."""
    W, H = int(w * 1.12), int(h * 1.12)
    dx, dy = (W - w), (H - h)
    sx, ex = ((0, dx), (dx, 0))[variant % 2]
    sy, ey = ((0, dy), (dy, 0))[(variant // 2) % 2]
    T = max(seconds, 0.1)
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"crop={w}:{h}:x='{sx}+({ex}-{sx})*t/{T:.3f}':y='{sy}+({ey}-{sy})*t/{T:.3f}',setsar=1,fps={fps}")
    if darken > 0:
        vf += f",drawbox=x=0:y=0:w=iw:h=ih:color=black@{darken}:t=fill"
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(fps), "-t", f"{seconds:.3f}", "-i", str(src),
         "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-crf", "21", str(dst)])


def _video_clip(src: Path, seconds: float, dst: Path, w: int, h: int, fps: int, darken: float) -> None:
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps}"
    if darken > 0:
        vf += f",drawbox=x=0:y=0:w=iw:h=ih:color=black@{darken}:t=fill"
    run(["ffmpeg", "-y", "-stream_loop", "-1", "-t", f"{seconds:.3f}", "-i", str(src), "-vf", vf, "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-crf", "21", str(dst)])


# ---------- timing ----------
def _section_times(script: Script, timings: list[dict] | None, duration: float) -> list[tuple[int, float, float]]:
    """(section index, start, end) for every section with words, covering the whole video."""
    spoken = [i for i, s in enumerate(script.sections) if s.text.strip()] or [0]
    if timings:
        out = [(t["section"], float(t["start"]), float(t["end"])) for t in timings]
    else:  # own recording: share the time out by word count
        words = [max(1, len(script.sections[i].text.split())) if script.sections else 1 for i in spoken]
        total, t, out = sum(words), 0.0, []
        for i, wc in zip(spoken, words):
            d = duration * wc / total
            out.append((i, t, t + d))
            t += d
    # stretch so sections touch and the last one reaches the end
    fixed = []
    for k, (i, a, b) in enumerate(out):
        a = 0.0 if k == 0 else fixed[-1][2]
        b = duration if k == len(out) - 1 else out[k + 1][1]
        fixed.append((i, a, b))
    return fixed


# ---------- text overlay (ASS) ----------
def _ass_time(t: float) -> str:
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def _ass_text(s: str) -> str:
    s = s.replace("\\", "/").replace("{", "(").replace("}", ")")
    return re.sub(r"\s*\n\s*", r"\\N", s.strip())


def _read_srt(path: Path) -> list[tuple[float, float, str]]:
    cues = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip()):
        lines = block.strip().splitlines()
        if len(lines) < 2 or "-->" not in lines[1]:
            continue
        def sec(x):
            h, m, rest = x.strip().split(":")
            s, ms = rest.replace(".", ",").split(",")
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        a, b = lines[1].split("-->")
        cues.append((sec(a), sec(b), " ".join(lines[2:])))
    return cues


def _build_ass(script: Script, cfg: dict, w: int, h: int, sections, captions: Path | None,
               duration: float, path: Path) -> None:
    short = script.is_short
    channel = cfg.get("channel", {})
    name = channel.get("name", "")
    handle = channel.get("handle", "")
    font = cfg.get("video", {}).get("font", "Arial")
    cap_size, title_size, label_size = (72, 92, 50) if short else (58, 104, 44)
    cap_margin, label_margin = (430, 300) if short else (90, 40)
    gold, white, black = "&H003FD2FF", "&H00FFFFFF", "&H00000000"
    box = "&H50103E3D"      # semi-transparent dark teal (AABBGGRR)
    capbox = "&H70000000"   # semi-transparent black behind captions
    styles = [
        f"Style: Caption,{font},{cap_size},{white},{white},{capbox},{capbox},0,0,0,0,100,100,0,0,3,12,0,2,110,110,{cap_margin},1",
        f"Style: Card,{font},{title_size},{gold},{gold},{box},{box},1,0,0,0,100,100,0,0,3,30,0,5,120,120,0,1",
        f"Style: Label,{font},{label_size},{gold},{gold},{black},{black},1,0,0,0,100,100,0,0,1,3,1,8,120,120,{label_margin},1",
        f"Style: Big,{font},{title_size - 8},{white},{white},{box},{box},1,0,0,0,100,100,0,0,3,28,0,5,130,130,0,1",
        f"Style: Small,{font},{int(cap_size * 0.85)},{gold},{gold},{black},{black},1,0,0,0,100,100,0,0,1,3,0,5,80,80,0,1",
    ]
    ev = []
    intro_end = min(3.6, duration * 0.4)
    if not short:
        ev.append(("Big", 0.0, intro_end, r"{\fad(250,350)}" + _ass_text(script.title.split("|")[0])))
        ev.append(("Small", 0.0, intro_end, r"{\fad(250,350)\pos(%d,%d)}" % (w // 2, int(h * 0.78)) + _ass_text(name)))
    for k, (i, a, b) in enumerate(sections):
        card = script.sections[i].card if script.sections else None
        if not card and short and k == 0:
            card = script.thumbnail_text or script.title.split("|")[0]
        if not card:
            continue
        start = max(a + 0.15, intro_end + 0.1 if k == 0 and not short else a + 0.15)
        end = min(b - 0.1, start + (2.8 if short else 3.4))
        if end - start > 1.0:
            ev.append(("Card", start, end, r"{\fad(300,250)}" + _ass_text(card)))
            if b - end > 2.0:   # small label at the top for the rest of the section
                ev.append(("Label", end, b - 0.05, r"{\fad(250,200)}" + _ass_text(card)))
    if captions and captions.exists() and cfg.get("video", {}).get("captions", True):
        for a, b, txt in _read_srt(captions):
            ev.append(("Caption", a, b, _ass_text(txt)))
    outro = 4.5 if not short else 2.5
    if duration > outro + 5:
        a = duration - outro
        ev.append(("Big", a, duration, r"{\fad(300,0)}" + _ass_text(f"Subscribe: {name}")))
        if handle:
            ev.append(("Small", a, duration, r"{\fad(300,0)\pos(%d,%d)}" % (w // 2, int(h * 0.62)) + _ass_text(handle)))
    body = "\n".join(f"Dialogue: {1 if st in ('Caption', 'Label') else 2},{_ass_time(a)},{_ass_time(b)},{st},,0,0,0,,{t}"
                     for st, a, b, t in ev)
    path.write_text(
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {w}\nPlayResY: {h}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
        "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n" + "\n".join(styles) +
        "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" + body + "\n",
        encoding="utf-8")


# ---------- main ----------
def assemble(script: Script, voice: Path, captions: Path | None, cfg: dict, timings: list[dict] | None = None) -> Path:
    need("ffmpeg")
    vcfg = cfg.get("video", {})
    fps = int(vcfg.get("fps", 30))
    out = script.out_dir
    duration = media_duration(voice) + 0.6
    if script.is_short:
        scfg = cfg.get("shorts", {})
        w, h = 1080, 1920
        seg_len = float(scfg.get("seconds_per_visual", 3))
        limit = float(scfg.get("max_seconds", 60))
        if duration > 180:
            raise ValueError(f"voice is {duration:.0f}s; YouTube Shorts can be at most 3 minutes. Shorten the script.")
        if duration > limit:
            print(f"  WARNING: short is {duration:.0f}s (target {limit:.0f}s). Shorter Shorts usually do better.")
    else:
        w, h = int(vcfg.get("width", 1920)), int(vcfg.get("height", 1080))
        seg_len = float(vcfg.get("seconds_per_visual", 6))

    sections = _section_times(script, timings, duration)
    media = _media(ASSETS / (script.assets or "common")) or _media(ASSETS / "common")
    darken = float(vcfg.get("darken_images", 0.35))
    rnd = random.Random(script.slug)
    order = media[:]
    rnd.shuffle(order)

    parts: list[Path] = []
    n = 0
    for k, (_, a, b) in enumerate(sections):
        if media:
            t = a
            while t < b - 0.05:
                length = min(seg_len, b - t)
                src = order[n % len(order)]
                dst = out / f"_part_{n:03d}.mp4"
                if src.suffix.lower() in IMG:
                    _pan_clip(src, length, dst, w, h, fps, n, darken)
                else:
                    _video_clip(src, length, dst, w, h, fps, darken)
                parts.append(dst)
                t += length
                n += 1
        else:
            bg = _brand_background(out / f"_bg_{k:02d}.jpg", w, h, k)
            dst = out / f"_part_{n:03d}.mp4"
            _pan_clip(bg, b - a, dst, w, h, fps, k, 0)
            parts.append(dst)
            n += 1
    print(f"  video: {len(parts)} background clips" + (f" from {len(media)} assets" if media else " (branded, no assets found)"))

    listfile = out / "_parts.txt"
    listfile.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts), encoding="utf-8")
    visuals = out / "_visuals.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy", str(visuals)])

    ass = out / "overlay.ass"
    _build_ass(script, cfg, w, h, sections, captions, duration, ass)

    logo = ROOT / cfg.get("channel", {}).get("logo", "channel/brand/profile-800.png")
    music_dir = ASSETS / "music"
    tracks = sorted(p for p in music_dir.iterdir() if p.suffix.lower() in AUD) if music_dir.is_dir() else []

    inputs = ["-i", str(visuals), "-i", str(voice),
              "-f", "lavfi", "-i", f"color=c=0xFFD23F:s={w}x{max(6, h // 160)}:r={fps}"]
    fc = []
    v = "[0:v]"
    nxt = 3
    if logo.exists():
        inputs += ["-loop", "1", "-i", str(logo)]
        lw = (w // 13) if not script.is_short else (w // 8)
        fc.append(f"[{nxt}:v]scale={lw}:-1,format=rgba,colorchannelmixer=aa=0.9[lg]")
        fc.append(f"{v}[lg]overlay=W-w-{w // 50}:{w // 50}:shortest=1[v1]")
        v = "[v1]"
        nxt += 1
    fc.append(f"{v}[2:v]overlay=x='-W+W*t/{duration:.3f}':y=H-h:shortest=1[v2]")
    fc.append(f"[v2]ass='{_ff_path(ass)}'[v]")
    if tracks:
        music = random.Random(script.slug).choice(tracks)
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        vol = float(vcfg.get("music_volume", 0.08))
        fc.append(f"[{nxt}:a]volume={vol}[m];[1:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]")
        amap = ["-map", "[a]"]
    else:
        amap = ["-map", "1:a"]

    final = out / "video.mp4"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[v]", *amap,
         "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final)])
    for p in parts + [visuals, listfile] + list(out.glob("_bg_*.jpg")):
        p.unlink(missing_ok=True)
    print(f"  video: {final.relative_to(out.parent.parent)} ({duration:.0f}s)")
    return final
