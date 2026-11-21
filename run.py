"""YouTube automation pipeline.

Usage:
  python run.py                      # every APPROVED script in scripts/pending/
  python run.py scripts/pending/x.md # one script
  python run.py --no-upload          # build voice, thumbnail and video only
  python run.py --voices ur          # list free voices for a language (ur, en, hi, ar ...)

A script is only processed when its front matter says  approved: true
Videos are always uploaded as PRIVATE. You make them public (or let publish_at do it)
after watching them in YouTube Studio.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path

from pipeline.common import ROOT, load_config, parse_script

PENDING = ROOT / "scripts" / "pending"
DONE = ROOT / "scripts" / "done"


def process(path: Path, cfg: dict, do_upload: bool) -> bool:
    from pipeline.assemble import assemble
    from pipeline.thumbnail import make_thumbnail
    from pipeline.voice import make_voice

    print(f"\n=== {path.name}")
    script = parse_script(path)
    if not script.approved:
        print("  skipped: set  approved: true  in the front matter after you have reviewed the script")
        return False
    voice, captions = make_voice(script, cfg)
    thumb = make_thumbnail(script, cfg)
    video = assemble(script, voice, captions, cfg)
    result = {"script": path.name, "video": str(video), "thumbnail": str(thumb),
              "built_at": datetime.now().isoformat(timespec="seconds")}
    if do_upload:
        from pipeline.upload import upload
        result["youtube_id"] = upload(script, video, thumb, cfg)
        DONE.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), DONE / path.name)
        print(f"  moved script to scripts/done/")
    (script.out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scripts", nargs="*", help="script files (default: all in scripts/pending)")
    ap.add_argument("--no-upload", action="store_true", help="build files only, do not upload")
    ap.add_argument("--voices", metavar="LANG", help="list free voices, e.g. --voices ur")
    args = ap.parse_args()

    if args.voices is not None:
        from pipeline.voice import list_voices
        list_voices(args.voices)
        return 0

    cfg = load_config()
    paths = [Path(p) for p in args.scripts] or sorted(PENDING.glob("*.md"))
    if not paths:
        print("No scripts in scripts/pending/. Ask Claude Code: /script <topic>")
        return 0
    ok = failed = 0
    for p in paths:
        try:
            if process(p, cfg, not args.no_upload):
                ok += 1
        except Exception as e:  # keep going with the next script
            failed += 1
            print(f"  ERROR: {e}")
            if "--debug" in sys.argv:
                traceback.print_exc()
    print(f"\nFinished: {ok} built, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
