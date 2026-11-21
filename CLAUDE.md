# YouTube automation project

This repo turns an approved script into a voiced, captioned video and uploads it to YouTube as a private, scheduled video.

## How it works
- `channel/bible.md` - the channel's audience, tone and rules. Read it before writing ideas or scripts.
- `ideas.md` - running list of ranked video ideas.
- `scripts/pending/*.md` - scripts waiting to be made. Front matter + narration.
- `scripts/done/` - scripts already uploaded.
- `assets/common/` and `assets/<folder>/` - images and clips used as visuals. `assets/music/` - background music.
- `run.py` - the pipeline: voice (edge-tts) -> thumbnail (Pillow) -> video (FFmpeg) -> upload (YouTube Data API).
- `config.yaml` - voice, video and YouTube settings.

## Script file format
```
---
title: "Video title, under 100 characters"
description: |
  Description with chapters (00:00 Intro ...) and sources.
tags: [tag one, tag two]
thumbnail_text: "4 WORDS MAX"
publish_at: 2026-11-28T18:00:00+05:00   # optional, must be in the future
synthetic_media: false                   # true only if visuals or voice look like real people or events
assets: common                           # folder inside assets/
approved: false                          # ONLY the human sets this to true
---
Narration text here. Lines starting with # and anything in [square brackets] are not spoken.
```

## Rules for Claude
1. Never set `approved: true`. The channel owner reviews and approves every script.
2. Never change uploads to public, and never remove `privacyStatus: private` from `pipeline/upload.py`.
3. Never commit `client_secret.json`, `token.json` or `.env`.
4. Follow `channel/bible.md`. Every script must differ in structure and examples from recent ones in `scripts/done/`.
5. Put a source for every fact in a "Sources" list at the end of the script, inside [square brackets] so it is not spoken.
6. Leave a `[MY TAKE: ...]` placeholder where the owner should add their own opinion or story.
7. When a command fails, read the error, fix the code, and explain the fix in one or two lines.

## Commands
- `pip install -r requirements.txt`
- `python run.py --no-upload` - build videos without uploading (for testing)
- `python run.py` - build and upload every approved script
- `python run.py --voices ur` - list Urdu voices
