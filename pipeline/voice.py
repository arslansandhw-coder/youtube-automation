"""Narration -> voice.mp3 + captions.srt using free Microsoft Edge voices (edge-tts).

If output/<slug>/voice.mp3 already exists (for example your own recording),
it is kept and only captions are skipped unless captions.srt also exists.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

from .common import Script


async def _speak(text: str, voice: str, rate: str, mp3: Path, srt: Path) -> None:
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="SentenceBoundary")
    subs = edge_tts.SubMaker()
    with open(mp3, "wb") as fh:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                subs.feed(chunk)
    srt.write_text(subs.get_srt(), encoding="utf-8")


def make_voice(script: Script, cfg: dict) -> tuple[Path, Path | None]:
    mp3 = script.out_dir / "voice.mp3"
    srt = script.out_dir / "captions.srt"
    if mp3.exists() and mp3.stat().st_size > 0:
        print(f"  voice: using existing {mp3.name}")
        return mp3, (srt if srt.exists() else None)
    vcfg = cfg.get("voice", {})
    voice = script.voice or vcfg.get("name", "en-US-AndrewMultilingualNeural")
    rate = vcfg.get("rate", "+0%")
    print(f"  voice: generating with {voice}")
    asyncio.run(_speak(script.narration, voice, rate, mp3, srt))
    return mp3, srt


def list_voices(lang_prefix: str = "") -> None:
    voices = asyncio.run(edge_tts.list_voices())
    for v in voices:
        if v["ShortName"].lower().startswith(lang_prefix.lower()):
            print(f'{v["ShortName"]:40} {v["Gender"]}')
