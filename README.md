# YouTube Automation (Claude Code + GitHub)

Approved script se voice, captions, thumbnail aur video khud banti hai, aur YouTube par **private** (scheduled) upload ho jati hai. Claude Code ideas dhoondta hai aur scripts likhta hai. Aap review karte hain, approve karte hain, aur video public hone se pehle dekhte hain.

```
/ideas  ->  /script  ->  aap review + approved: true  ->  python run.py  ->  YouTube Studio mein dekhein  ->  live
```

---

## Sab se aasaan tareeqa (Windows): 3 files, double-click

| File | Kya karti hai |
| --- | --- |
| `1-setup.bat` | Python, FFmpeg aur packages khud install karti hai (sirf pehli dafa) |
| `2-test-video.bat` | Pehli script ki namoona video banati hai. Upload nahi karti, approval ki zaroorat nahi |
| `3-upload-videos.bat` | Har `approved: true` script ki video bana kar YouTube par **private** upload karti hai |

Neeche wale steps wahi kaam haath se karne ka tareeqa hain (Mac ke liye bhi).

## Hissa 1: Computer tayyar karna (sirf ek dafa)

**Step 1. Python install karein**
python.org/downloads se Python 3.11 ya naya version. Windows par install karte waqt **"Add Python to PATH"** zaroor tick karein.

**Step 2. FFmpeg install karein** (video banane ka tool)
- Windows: Command Prompt mein `winget install Gyan.FFmpeg` likhein, phir Command Prompt band kar ke dobara kholein.
- Mac: `brew install ffmpeg`
- Check karein: `ffmpeg -version` likhne par version nazar aana chahiye.

**Step 3. Repo download karein aur packages install karein**
```
git clone https://github.com/arslansandhw-coder/youtube-automation.git
cd youtube-automation
pip install -r requirements.txt
```
(Git nahi hai to GitHub par repo kholein -> **Code** -> **Download ZIP**.)

**Step 4. YouTube se jorna (Google Cloud)**
1. console.cloud.google.com par jayein -> naya project banayein, naam `yt-automation`.
2. **APIs & Services -> Library** -> "YouTube Data API v3" -> **Enable**.
3. **OAuth consent screen** -> User type **External** -> app ka naam aur apna email -> **Test users** mein apna Gmail add karein.
4. **Credentials -> Create credentials -> OAuth client ID** -> Application type **Desktop app** -> Create -> **Download JSON**.
5. Is file ka naam `client_secret.json` rakh kar project folder mein rakhein. **Yeh file kabhi GitHub par upload na karein** (`.gitignore` isay rokta hai).

**Step 5. Test video banayein (upload ke baghair)**
`assets/common/` folder mein 3 se 5 tasveerein (jpg/png) daalein, jaise Pexels.com se free photos. Phir:
```
python run.py --no-upload
```
`output/2026-12-01-sample-test-video/video.mp4` khol kar dekhein.

**Step 6. Pehla upload**
```
python run.py
```
Pehli dafa browser khulega: apne channel wale Gmail se login karein aur **Allow** dabayein. Video YouTube Studio mein **private** pohanch jayegi.

---

## Hissa 2: Claude Code ke saath roz ka kaam

Claude Code **apne computer par** chalayein (Claude desktop app ka Code tab, ya terminal mein `claude`), aur yeh folder kholein. Is repo ki `CLAUDE.md` file Claude ko poora system samjha deti hai.

| Command | Kya karta hai |
| --- | --- |
| `/ideas` | Web se research kar ke 10 naye ideas `ideas.md` mein likhta hai |
| `/script <topic>` | Poori script `scripts/pending/` mein likhta hai (sources ke saath) |
| `/make-video` | Approved scripts se video banata hai, errors theek karta hai, upload se pehle poochta hai |
| `/review-week <analytics>` | Hafte ke analytics dekh kar batata hai kya chala aur kya badlein |

**Har video ka tareeqa:**
1. `/script` se script likhwayein.
2. Script khud parhein, `[MY TAKE: ...]` ki jagah apni raye likhein, facts check karein.
3. Front matter mein `approved: true` aur `publish_at` (maslan `2026-12-05T18:00:00+05:00`) likhein.
4. `/make-video` chalayein.
5. YouTube Studio mein video dekhein. Theek ho to publish_at ke waqt khud live ho jayegi.

**claude.ai/code (cloud) se bhi:** phone ya browser se `/ideas` aur `/script` chala sakte hain. Claude scripts repo mein push kar dega. Lekin `python run.py` (video aur upload) **apne computer par** chalayein, kyunke upload ke liye aapka Google login aur `client_secret.json` wahin hain.

---

## Shorts
Script ke front matter mein `format: short` likhein. Pipeline khari (1080x1920) video banati hai, title mein #Shorts lagati hai, aur 60 second se lambi ho to warning deti hai. Claude Code se: `/script short: <topic>`

## Urdu videos
`config.yaml` mein:
```yaml
voice:
  name: ur-PK-AsadNeural   # ya ur-PK-UzmaNeural
youtube:
  language: ur
```
Saari Urdu voices dekhne ke liye: `python run.py --voices ur`

## Apni awaaz
Script ka video banane se pehle apni recording `output/<script-ka-naam>/voice.mp3` mein rakh dein. Pipeline AI voice ki jagah usay use karegi (captions tab nahi banenge).

---

## Zaroori qawaid (channel ki kamai bachane ke liye)
- Har script mein apni raye, tajurba ya research shamil karein. Ek jaisi template wali videos YouTube monetize nahi karta.
- Har video upload ke baad **khud dekhein**. Pipeline hamesha private upload karti hai.
- Agar visuals ya awaaz asli insaan ya asli waqia jaisi lagti hai to `synthetic_media: true` likhein.
- Sirf free/licensed tasveerein aur music use karein.
- Custom thumbnail ke liye channel phone se verify hona chahiye (youtube.com/verify).

## Masle (Troubleshooting)
| Error | Hal |
| --- | --- |
| `'ffmpeg' is not installed` | Step 2 dobara karein, terminal band kar ke kholein |
| `client_secret.json not found` | Step 4 ki file project folder mein rakhein |
| `access_denied` login par | Consent screen mein apna Gmail **Test users** mein add karein |
| `publish_at ... is in the past` | Aane wali tareekh likhein, timezone ke saath (+05:00) |
| `quotaExceeded` | Aaj ki API limit khatam, kal dobara chalayein |

Koi aur error aaye to Claude Code ko error paste kar ke kahein: "isay theek karo".
