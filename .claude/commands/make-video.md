---
description: Build (and upload as private) every approved script, fixing errors along the way
---
1. Check that `ffmpeg` and the Python packages in `requirements.txt` are installed; install what is missing.
2. List the scripts in `scripts/pending/` and say which are approved and which are not.
3. Run `python run.py --no-upload` first. $ARGUMENTS
4. If anything fails, read the error, fix the code, and run again.
5. When the build works, ask me before running `python run.py` to upload. Uploads are always private.
6. After uploading, add each published title to "Topics already covered" in `channel/bible.md` and give me the YouTube Studio links.
