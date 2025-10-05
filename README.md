# gridiii.py — Kahoot Report → Grades → TTS → Lip‑Sync Pipeline

This repo contains **`gridiii.py`**, an end‑to‑end automation that:

1) signs in to Kahoot and downloads the latest report,  
2) parses the Excel file and computes letter/numeric grades,  
3) generates a narrated MP3 from the results using a TTS service, and  
4) lip‑syncs a provided video to that narration using Everypixel’s Lipsync API.

> ⚠️ **Heads‑up / Caution**  
> During the flow, your browser or OS **may show a confirmation dialog** (e.g., _“Allow automatic downloads?”_, _“This site is trying to download multiple files”_, or security prompts from Chrome/Chromedriver/ffmpeg). **Choose “Yes/Allow/Keep/Trust”** if prompted so downloads and automation can proceed.

---

## Table of Contents

- [How it works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Configuration](#configuration)
- [Running](#running)
- [Output](#output)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)
- [Limitations](#limitations)
- [License](#license)

---

## How it works

**High‑level steps performed by `gridiii.py`:**

1. **Automated login to Kahoot (Selenium/Chrome):**
   - Navigates to the Kahoot login page.
   - Enters username & password (currently hard‑coded in the script — see **Security Notes**).
   - Moves to the **Reports** page and opens the **Action menu → Download report**.

2. **Download & parse the Excel report (Pandas):**
   - Grabs the **most recently downloaded** `.xlsx` file.
   - Reads a report sheet (uses `sheet_name=1` and `header=2`) and expects columns like:
     - `Rank`, `Player`, `Total Score (points)`, `Correct Answers`.
   - Computes **letter grades** and a **numeric grade** from the score/answers.  
     The default letter mapping is:
     - `>= 92 → "10"`  
     - `>= 82 → "9"`  
     - `>= 72 → "8"`  
     - `>= 63 → "7"`  
     - `>= 57 → "6"`  
     - `>= 50 → "5"`  
     - `< 50 → "4"`

3. **Text‑to‑Speech (TTS):**
   - Builds a text summary of results.
   - Calls a **Neura TTS** task endpoint, polls for completion, and downloads an **MP3** (e.g., `grades_speech.mp3`).

4. **Lip‑sync the video (Everypixel):**
   - Converts the MP3 → WAV via **ffmpeg**.
   - Sends `{audio, input_video.mp4}` to **Everypixel Lipsync** (`/v1/lipsync/create`), polls job status, then downloads the **final lip‑synced video** (e.g., `lip_synced_video.mp4`).

---

## Prerequisites

- **Python 3.9+**
- **Google Chrome** (stable)  
- **ChromeDriver** matching your Chrome version **on PATH**
  - Tip: print your versions: `chrome --version` and `chromedriver --version`
- **ffmpeg** on PATH (for audio conversion): <https://ffmpeg.org/>
- Python packages:
  ```bash
  pip install selenium pandas requests openpyxl
  ```
  > `openpyxl` is required by pandas to read `.xlsx` files.

- **API credentials**
  - **Everypixel Lipsync**: `EVERYPIXEL_CLIENT_ID` and `EVERYPIXEL_CLIENT_SECRET`
  - **Neura TTS** (or your chosen TTS provider): API key/secret; endpoint used by the script

---

## Setup

1. **Clone & move into your project**  
   ```bash
   git clone <your-repo-url>.git
   cd <your-repo-folder>
   ```

2. **Install deps**  
   ```bash
   python -m venv .venv && source .venv/bin/activate   # macOS/Linux
   # or: .venv\Scripts\activate                       # Windows (PowerShell)
   pip install -r requirements.txt || pip install selenium pandas requests openpyxl
   ```

3. **Install ChromeDriver & ffmpeg**  
   - Put both on your **PATH** or set explicit paths in the script if you prefer.

4. **Create a `.env` file (recommended)**  
   Store secrets here instead of hard‑coding them:
   ```dotenv
   KAHOOT_USERNAME=your@email.com
   KAHOOT_PASSWORD=your-strong-password
   EVERYPIXEL_CLIENT_ID=your-everypixel-client-id
   EVERYPIXEL_CLIENT_SECRET=your-everypixel-client-secret
   NEURA_API_KEY=your-neura-api-key
   DOWNLOAD_DIR=/absolute/path/for/downloads
   INPUT_VIDEO=/absolute/path/to/input_video.mp4
   ```

5. **Place your input video**  
   Put the video you want to lip‑sync at the path in `INPUT_VIDEO` (default in the script is `input_video.mp4`).

> **Note:** The script currently sets a user‑specific `download_path` and **hard‑codes credentials**. Before committing:
> - Switch to **environment variables** (see below).
> - Consider making these options **configurable** (CLI args or a config file).

---

## Configuration

You can adapt `gridiii.py` to read environment variables like so:

```python
import os

KAHOOT_USERNAME = os.getenv("KAHOOT_USERNAME")
KAHOOT_PASSWORD = os.getenv("KAHOOT_PASSWORD")
EVERYPIXEL_CLIENT_ID = os.getenv("EVERYPIXEL_CLIENT_ID")
EVERYPIXEL_CLIENT_SECRET = os.getenv("EVERYPIXEL_CLIENT_SECRET")
NEURA_API_KEY = os.getenv("NEURA_API_KEY")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", str(Path.cwd()))
INPUT_VIDEO = os.getenv("INPUT_VIDEO", "input_video.mp4")
```

And for Chrome downloads:

```python
from selenium import webdriver

options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "safebrowsing.enabled": True
}
options.add_experimental_option("prefs", prefs)
driver = webdriver.Chrome(options=options)
```

---

## Running

Activate your venv, set environment variables, and run:

```bash
python gridiii.py
```

What you’ll see:

- A Chrome window opens, logs into Kahoot, navigates to **Reports**, and triggers **Download report**.
- Pandas parses the latest `.xlsx` file and computes grades.
- The script requests a **TTS** MP3 and converts it to WAV via **ffmpeg**.
- The audio+video are sent to **Everypixel**; the script polls until the job is **finished**.
- The final video is saved (by default) as **`lip_synced_video.mp4`**.

---

## Output

- `grades_speech.mp3` — downloaded TTS narration  
- `grades_speech.wav` — intermediate WAV for lipsync  
- `lip_synced_video.mp4` — final video with lip‑sync applied  
- The original Kahoot report Excel in your **download directory**

---

## Troubleshooting

- **Chrome prompts**:  
  If you see popups like *“Allow automatic downloads?”*, *“This site is trying to download multiple files”*, or security prompts for Chrome/Chromedriver/ffmpeg, **click “Yes/Allow/Keep/Trust”** so the automation can continue.

- **Changed Kahoot UI / selectors**:  
  The site may alter element attributes. Update the XPaths/CSS selectors in the script if the click steps stop working.

- **2FA / SSO**:  
  If your Kahoot account uses SSO or MFA, the scripted login may require additional handling.

- **ChromeDriver mismatch**:  
  Ensure the Chrome and ChromeDriver versions match. Otherwise you’ll see session errors on startup.

- **`ffmpeg` not found**:  
  Install ffmpeg and ensure it’s on your PATH. Test via `ffmpeg -version`.

- **Excel parse errors**:  
  The script expects specific headers (sheet index 1, header row 2). Adjust `sheet_name`/`header` or rename columns if your report format differs.

- **API failures** (Neura / Everypixel):  
  Check your credentials, rate limits, and job status responses returned by each API. The script polls until `finished`; if it reports `failed`, inspect the payloads it prints.

---

## Security Notes

- **Do NOT commit secrets** (passwords, API keys) to Git.  
  Use environment variables or a local `.env` and add it to `.gitignore`:

  ```gitignore
  .env
  .venv/
  *.mp3
  *.wav
  *.mp4
  */Downloads/*
  ```

- Consider using a **secret manager** (1Password, macOS Keychain, Windows Credential Manager, or cloud KMS) for production use.

- Be mindful of the **Kahoot Terms of Service** and any applicable **privacy policies** when automating downloads or processing user data.

---

## Limitations

- Built for the **Kahoot report schema** used at the time of writing; UI/format changes may break automation.
- Hard‑coded paths and credentials should be replaced by environment variables or a config file.
- No CLI arguments yet; consider adding `argparse` to make it more flexible.

---

## License

MIT

---

### Credits

- Selenium, Pandas, Requests
- ffmpeg
- Neura TTS (or your TTS provider)
- Everypixel Lipsync API
