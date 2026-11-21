"""Build the final MP4 with FFmpeg: visuals + voice + optional music + burned captions.

Visuals come from assets/<script assets folder>/ (or assets/common/):
images (.jpg .png .webp) get a slow zoom, videos (.mp4 .mov .webm) are trimmed.
With no assets, a plain coloured background with the title is used.
"""
from __future__ import annotations

import random
from pathlib import Path

from .common import ASSETS, Script, media_duration, need, run

IMG = {".jpg", ".jpeg", ".png", ".webp"}
VID = {".mp4", ".mov", ".webm", ".mkv"}
AUD = {".mp3", ".wav", ".m4a"}


def _media(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMG | VID)


def _ff_path(p: Path) -> str:
    """Path escaped for use inside an FFmpeg filter (Windows-safe)."""
    s = p.resolve().as_posix()
    return s.replace(":", r"\:").replace("'", r"\'")


def _segment(src: Path, seconds: float, dst: Path, w: int, h: int, fps: int) -> None:
    fit = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"
    if src.suffix.lower() in IMG:
        frames = max(1, int(seconds * fps))
        zoom = (f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
                f"zoompan=z='min(zoom+0.0007,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d={frames}:s={w}x{h}:fps={fps},setsar=1")
        cmd = ["ffmpeg", "-y", "-loop", "1", "-t", f"{seconds:.3f}", "-i", str(src),
               "-vf", zoom, "-frames:v", str(frames)]
    else:
        cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-t", f"{seconds:.3f}", "-i", str(src),
               "-vf", f"{fit},fps={fps}", "-an"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-crf", "20", str(dst)]
    run(cmd)


def assemble(script: Script, voice: Path, captions: Path | None, cfg: dict) -> Path:
    need("ffmpeg")
    vcfg = cfg.get("video", {})
    w, h, fps = int(vcfg.get("width", 1920)), int(vcfg.get("height", 1080)), int(vcfg.get("fps", 30))
    seg_len = float(vcfg.get("seconds_per_visual", 6))
    out = script.out_dir
    duration = media_duration(voice) + 0.6

    folder = ASSETS / (script.assets or "common")
    media = _media(folder) or _media(ASSETS / "common")
    parts: list[Path] = []
    if media:
        rnd = random.Random(script.slug)
        order = media[:]
        rnd.shuffle(order)
        t, i = 0.0, 0
        while t < duration - 0.05:
            length = min(seg_len, duration - t)
            src = order[i % len(order)]
            dst = out / f"part_{i:03d}.mp4"
            _segment(src, length, dst, w, h, fps)
            parts.append(dst)
            t += length
            i += 1
        print(f"  video: {len(parts)} clips from {len(media)} assets")
        listfile = out / "parts.txt"
        listfile.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts), encoding="utf-8")
        visuals = out / "visuals.mp4"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy", str(visuals)])
    else:
        print("  video: no assets found, using a plain background")
        visuals = out / "visuals.mp4"
        bg = vcfg.get("background_color", "0x0e3f3d")
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={bg}:s={w}x{h}:r={fps}:d={duration:.3f}",
             "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(visuals)])

    # audio: voice + optional quiet background music
    inputs = ["-i", str(visuals), "-i", str(voice)]
    music_dir = ASSETS / "music"
    tracks = sorted(p for p in music_dir.iterdir() if p.suffix.lower() in AUD) if music_dir.is_dir() else []
    vf = []
    if captions and vcfg.get("captions", True):
        style = vcfg.get("caption_style",
                         "FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                         "BorderStyle=1,Outline=2,Shadow=0,MarginV=60")
        vf = ["-vf", f"subtitles='{_ff_path(captions)}':force_style='{style}'"]
    if tracks:
        music = random.Random(script.slug).choice(tracks)
        vol = float(vcfg.get("music_volume", 0.08))
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        audio = ["-filter_complex", f"[2:a]volume={vol}[m];[1:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
                 "-map", "0:v", "-map", "[a]"]
    else:
        audio = ["-map", "0:v", "-map", "1:a"]

    final = out / "video.mp4"
    run(["ffmpeg", "-y", *inputs, *audio, *vf, "-t", f"{duration:.3f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final)])
    for p in parts:
        p.unlink(missing_ok=True)
    print(f"  video: {final.relative_to(out.parent.parent)} ({duration:.0f}s)")
    return final
