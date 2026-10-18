# Yoink — Minimalist YouTube Downloader

A modern, fast web app for pulling **video** (with merged audio), **audio** (MP3), **silent video** (video track only), and **thumbnails** from YouTube links — with selectable resolutions. Powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) running locally on your machine.

---

## Features

| Mode | Output |
| :--- | :--- |
| **Video** | Best video + audio merged into an MP4 at your chosen resolution (1080p, 720p, etc.) |
| **Audio** | Extracted to MP3 @ 192 kbps |
| **Silent video** | Clean video stream without audio (perfect for loops and motion backgrounds) |
| **Thumbnail** | Highest-resolution cover artwork (.jpg / .webp) |

---

## Prerequisites & Requirements

> [!IMPORTANT]
> **Do not use macOS default Python 3.9.**
> Newer releases of `yt-dlp` require **Python 3.10 or newer**. Using Python 3.9 forces pip to install an outdated 2025 release of `yt-dlp`, which causes YouTube's bot-detection error (*"The page needs to be reloaded"*).

### 1. Python 3.10+
Check your Python version before starting:
```bash
python3 --version
```
If your version is less than 3.10 (such as macOS system Python 3.9):
- **macOS (Homebrew)**: `brew install python` (installs modern Python 3)
- **Windows**: Download Python 3.11+ from [python.org](https://www.python.org/) (ensure "Add Python to PATH" is checked)
- **Linux (Ubuntu/Debian)**: `sudo apt update && sudo apt install python3 python3-pip python3-venv`

### 2. FFmpeg
`ffmpeg` is required to merge separate video and audio streams into an MP4 and convert audio into MP3:
- **macOS**: `brew install ffmpeg`
- **Windows**: `winget install Gyan.FFmpeg`
- **Linux**: `sudo apt install ffmpeg`

Verify `ffmpeg` is accessible:
```bash
ffmpeg -version
```

---

## Installation & Setup

1. **Clone or enter the project folder:**
   ```bash
   cd youtube-downloader
   ```

2. **Create a Python virtual environment using Python 3.10+:**
   ```bash
   # macOS / Linux (make sure python3 points to Python 3.10+)
   python3 -m venv .venv
   ```

3. **Activate the virtual environment:**
   - **macOS / Linux:**
     ```bash
     source .venv/bin/activate
     ```
   - **Windows:**
     ```cmd
     .venv\Scripts\activate
     ```

4. **Install the dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Verify your `yt-dlp` installation inside the environment:**
   ```bash
   yt-dlp --version
   ```
   *You should see a modern version (e.g. `2026.x.x` or later).*

---

## Running the App

```bash
python app.py
```

Then open your browser and go to:
👉 **[http://127.0.0.1:5050](http://127.0.0.1:5050)**

> [!NOTE]
> **Why port 5050?**
> Port 5000 is reserved by macOS AirPlay Receiver (`ControlCenter`). Running on port 5050 prevents port conflict errors. You can also customize the port with the `PORT` environment variable (e.g. `PORT=8080 python app.py`).

---

## How to Use

1. Paste any YouTube video URL into the input field.
2. Click **Fetch** (or press Enter).
3. Select your desired mode tab (**Video**, **Audio**, **Silent video**, or **Thumbnail**).
4. Pick your resolution or quality bitrate.
5. Click **Download**. The file is generated and downloaded straight to your browser.

---

## Troubleshooting

- **Error: *"The page needs to be reloaded"* or *"Could not read that video"***
  YouTube constantly updates its video player tokens and bot countermeasures. If YouTube breaks:
  ```bash
  source .venv/bin/activate
  pip install --upgrade yt-dlp
  ```
- **SSL Certificate Verification Error on macOS:**
  The project bundles `certifi` and configures certificate authorities automatically in `app.py`. If running outside `app.py`, run `/Applications/Python\ 3.x/Install\ Certificates.command`.
- **Merge fails or MP3 doesn't produce:**
  Make sure `ffmpeg` is installed and available in your terminal path (`which ffmpeg`).