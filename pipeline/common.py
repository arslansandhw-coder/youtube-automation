"""Shared helpers: config, script parsing, paths."""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
ASSETS = ROOT / "assets"


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text[:60] or "video"


@dataclass
class Script:
    path: Path
    title: str
    description: str
    narration: str
    tags: list[str] = field(default_factory=list)
    publish_at: str | None = None
    synthetic_media: bool = False
    approved: bool = False
    voice: str | None = None
    thumbnail_text: str | None = None
    assets: str | None = None
    category_id: str = "27"

    @property
    def slug(self) -> str:
        return slugify(self.path.stem)

    @property
    def out_dir(self) -> Path:
        d = OUTPUT / self.slug
        d.mkdir(parents=True, exist_ok=True)
        return d


FRONT = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.S)


def clean_narration(body: str) -> str:
    """Keep only the words to be spoken.

    Removed: markdown headings, [visual notes in brackets], HTML comments,
    bullet markers and emphasis characters.
    """
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"\[[^\]]*\]", "", body, flags=re.S)   # [notes], also across several lines
    lines = []
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            lines.append("")
            continue
        s = re.sub(r"\[[^\]]*\]", "", s)          # [B-roll: ...] notes
        s = re.sub(r"^[-*]\s+", "", s)             # bullets
        s = s.replace("**", "").replace("__", "").replace("*", "")
        lines.append(s.strip())
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_script(path: Path) -> Script:
    raw = path.read_text(encoding="utf-8")
    m = FRONT.match(raw)
    if not m:
        raise ValueError(f"{path.name}: missing the --- front matter block at the top")
    meta = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)
    for key in ("title", "description"):
        if not meta.get(key):
            raise ValueError(f"{path.name}: front matter needs '{key}'")
    narration = clean_narration(body)
    if len(narration.split()) < 30:
        raise ValueError(f"{path.name}: narration is too short ({len(narration.split())} words)")
    publish_at = meta.get("publish_at")
    if isinstance(publish_at, datetime):
        publish_at = publish_at.isoformat()
    return Script(
        path=path,
        title=str(meta["title"]).strip(),
        description=str(meta["description"]).strip(),
        narration=narration,
        tags=[str(t) for t in (meta.get("tags") or [])],
        publish_at=str(publish_at) if publish_at else None,
        synthetic_media=bool(meta.get("synthetic_media", False)),
        approved=bool(meta.get("approved", False)),
        voice=meta.get("voice"),
        thumbnail_text=meta.get("thumbnail_text"),
        assets=meta.get("assets"),
        category_id=str(meta.get("category_id", "27")),
    )


def to_utc_iso(value: str) -> str:
    """'2026-11-25T18:00:00+05:00' -> '2026-11-25T13:00:00Z' (YouTube wants UTC)."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError(f"publish_at '{value}' needs a timezone, e.g. +05:00")
    if dt <= datetime.now(timezone.utc):
        raise ValueError(f"publish_at '{value}' is in the past")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def need(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise SystemExit(f"'{tool}' is not installed or not on PATH. See README step 2.")
    return path


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        raise RuntimeError(f"Command failed: {' '.join(cmd[:3])} ...\n{tail}")


def media_duration(path: Path) -> float:
    need("ffprobe")
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())
