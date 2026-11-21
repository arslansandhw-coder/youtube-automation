"""Narration -> voice.mp3 + captions.srt using free Microsoft Edge voices (edge-tts).

Each section (markdown heading) is voiced separately, so the video knows exactly
when each section starts. timings.json records those start/end times.

If output/<slug>/voice.mp3 already exists (for example your own recording),
it is kept. Sections are then timed by word count, and captions are only
used if captions.srt also exists.
"""
from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from pathlib import Path

import edge_tts

from .common import Script, media_duration, need, run

GAP = 0.35  # seconds of silence between sections


def _srt_time(sec: float) -> str:
    td = timedelta(seconds=max(0.0, sec))
    total = int(td.total_seconds())
    ms = int(round((td.total_seconds() - total) * 1000))
    if ms == 1000:
        total, ms = total + 1, 0
    return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d},{ms:03d}"


async def _speak(text: str, voice: str, rate: str, mp3: Path) -> list[tuple[float, float, str]]:
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="SentenceBoundary")
    cues = []
    with open(mp3, "wb") as fh:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                start = chunk["offset"] / 1e7
                cues.append((start, start + chunk["duration"] / 1e7, chunk["text"]))
    return cues


def make_voice(script: Script, cfg: dict) -> tuple[Path, Path | None, list[dict] | None]:
    out = script.out_dir
    mp3, srt, tjson = out / "voice.mp3", out / "captions.srt", out / "timings.json"
    if mp3.exists() and mp3.stat().st_size > 0:
        print(f"  voice: using existing {mp3.name}")
        timings = json.loads(tjson.read_text(encoding="utf-8")) if tjson.exists() else None
        return mp3, (srt if srt.exists() else None), timings

    need("ffmpeg")
    vcfg = cfg.get("voice", {})
    voice = script.voice or vcfg.get("name", "en-US-AndrewMultilingualNeural")
    rate = vcfg.get("rate", "+0%")
    print(f"  voice: generating with {voice}")

    sections = [(i, s) for i, s in enumerate(script.sections) if s.text.strip()]
    if not sections:
        raise ValueError("script has no spoken text")
    silence = out / "_gap.mp3"
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(GAP),
         "-c:a", "libmp3lame", "-b:a", "48k", str(silence)])

    files, cues_all, timings, t = [], [], [], 0.0
    for n, (idx, sec) in enumerate(sections):
        part = out / f"_voice_{n:02d}.mp3"
        cues = asyncio.run(_speak(sec.text, voice, rate, part))
        dur = media_duration(part)
        timings.append({"section": idx, "start": round(t, 3), "end": round(t + dur, 3)})
        cues_all += [(t + a, t + b, txt) for a, b, txt in cues]
        files.append(part)
        t += dur
        if n < len(sections) - 1:
            files.append(silence)
            t += GAP
        print(f"  voice: section {n + 1}/{len(sections)} ({dur:.0f}s)")

    listfile = out / "_voice_list.txt"
    listfile.write_text("".join(f"file '{f.resolve().as_posix()}'\n" for f in files), encoding="utf-8")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
         "-c:a", "libmp3lame", "-b:a", "128k", str(mp3)])
    srt.write_text("".join(f"{k}\n{_srt_time(a)} --> {_srt_time(b)}\n{txt}\n\n"
                           for k, (a, b, txt) in enumerate(cues_all, 1)), encoding="utf-8")
    tjson.write_text(json.dumps(timings, indent=1), encoding="utf-8")
    for f in files + [listfile]:
        Path(f).unlink(missing_ok=True)
    return mp3, srt, timings


def list_voices(lang_prefix: str = "") -> None:
    voices = asyncio.run(edge_tts.list_voices())
    for v in voices:
        if v["ShortName"].lower().startswith(lang_prefix.lower()):
            print(f'{v["ShortName"]:40} {v["Gender"]}')
