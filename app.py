"""
Minimal YouTube download web app powered by yt-dlp.

Endpoints:
  GET  /                -> UI
  GET  /api/info        -> metadata + available formats for a URL
  GET  /api/download    -> streams the chosen file back as an attachment

Modes: video (muxed w/ audio), background (video only, no audio),
       audio (extracted audio), thumbnail.
"""

import os
import re
import glob
import shutil
import tempfile
from urllib.request import urlopen, Request

# Ensure standard bin directories are in PATH (for ffmpeg on macOS)
for bin_dir in ("/opt/homebrew/bin", "/usr/local/bin"):
    if os.path.isdir(bin_dir) and bin_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{bin_dir}:{os.environ.get('PATH', '')}"

# Ensure SSL certificates are verified correctly
try:
    import certifi
    if "SSL_CERT_FILE" not in os.environ:
        os.environ["SSL_CERT_FILE"] = certifi.where()
except ImportError:
    pass

# pyrefly: ignore[missing-import]
from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    send_file,
    after_this_request,
)
import yt_dlp

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

YDL_BASE = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
}


def _human_size(num):
    if not num:
        return None
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024:
            return f"{num:.0f} {unit}" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


def _human_duration(seconds):
    if not seconds:
        return None
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def extract_info(url):
    with yt_dlp.YoutubeDL(YDL_BASE) as ydl:
        return ydl.extract_info(url, download=False)


def build_format_lists(info):
    """Group yt-dlp formats into resolution buckets the UI can show."""
    video_res, audio_opts = {}, []

    for f in info.get("formats", []):
        vcodec = f.get("vcodec") or "none"
        acodec = f.get("acodec") or "none"
        height = f.get("height")

        if vcodec != "none" and height:
            fps_str = ""
            if f.get("fps"):
                try:
                    fps_str = f" {int(float(f['fps']))}fps"
                except (ValueError, TypeError):
                    pass
            # One entry per resolution; keep the biggest known filesize.
            size = f.get("filesize") or f.get("filesize_approx")
            prev = video_res.get(height)
            if not prev or (size and (not prev["_size"] or size > prev["_size"])):
                video_res[height] = {
                    "height": height,
                    "label": f"{height}p{fps_str}",
                    "ext": "mp4",
                    "filesize": _human_size(size),
                    "_size": size,
                }
        elif vcodec == "none" and acodec != "none":
            size = f.get("filesize") or f.get("filesize_approx")
            abr = f.get("abr")
            abr_int = None
            if abr:
                try:
                    abr_int = int(float(abr))
                except (ValueError, TypeError):
                    pass
            audio_opts.append(
                {
                    "format_id": f.get("format_id"),
                    "label": (f"{abr_int} kbps" if abr_int else f.get("format_note") or "audio")
                    + f" · {f.get('ext')}",
                    "abr": abr_int or 0,
                    "ext": f.get("ext"),
                    "filesize": _human_size(size),
                }
            )

    videos = sorted(video_res.values(), key=lambda x: x["height"], reverse=True)
    for v in videos:
        v.pop("_size", None)
    audio_opts.sort(key=lambda x: x["abr"], reverse=True)

    return videos, audios_dedupe(audio_opts)


def audios_dedupe(audio_opts):
    seen, out = set(), []
    for a in audio_opts:
        abr_val = 0
        try:
            abr_val = round(float(a.get("abr") or 0))
        except (ValueError, TypeError):
            pass
        key = (abr_val, a.get("ext"))
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out[:6]


def safe_filename(name):
    name = re.sub(r"[^\w\s.\-()]", "", name or "download").strip()
    return re.sub(r"\s+", " ", name)[:120] or "download"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info")
def api_info():
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "Please provide a YouTube URL."}), 400
    try:
        info = extract_info(url)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Could not read that video. {exc}"}), 400

    videos, audios = build_format_lists(info)
    return jsonify(
        {
            "title": info.get("title"),
            "uploader": info.get("uploader") or info.get("channel"),
            "duration": _human_duration(info.get("duration")),
            "thumbnail": info.get("thumbnail"),
            "video_resolutions": videos,
            "audio_options": audios,
            "has_thumbnail": bool(info.get("thumbnail")),
        }
    )


@app.route("/api/download")
def api_download():
    url = request.args.get("url", "").strip()
    mode = request.args.get("mode", "video")
    quality = request.args.get("quality")  # height for video/background; format_id for audio

    if not url:
        return jsonify({"error": "Missing URL."}), 400

    # Thumbnail: proxy the image bytes straight through.
    if mode == "thumbnail":
        try:
            info = extract_info(url)
            thumb_url = info.get("thumbnail")
            if not thumb_url:
                return jsonify({"error": "No thumbnail available."}), 404
            req = Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
            data = urlopen(req).read()  # noqa: S310
            tmpdir = tempfile.mkdtemp()
            ext = ".jpg" if ".webp" not in thumb_url else ".webp"
            path = os.path.join(tmpdir, safe_filename(info.get("title")) + ext)
            with open(path, "wb") as fh:
                fh.write(data)

            @after_this_request
            def _cleanup(resp, _d=tmpdir):  # noqa: ANN001
                shutil.rmtree(_d, ignore_errors=True)
                return resp

            return send_file(path, as_attachment=True, download_name=os.path.basename(path))
        except Exception as exc:  # noqa: BLE001
            return jsonify({"error": f"Thumbnail download failed. {exc}"}), 400

    # Build a yt-dlp format selector per mode.
    opts = dict(YDL_BASE)
    tmpdir = tempfile.mkdtemp()
    opts["outtmpl"] = os.path.join(tmpdir, "%(title)s.%(ext)s")

    if mode == "video":
        h = quality or "1080"
        opts["format"] = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
        opts["merge_output_format"] = "mp4"
    elif mode == "background":
        h = quality or "1080"
        opts["format"] = f"bestvideo[height<={h}]/best[height<={h}]"
    elif mode == "audio":
        opts["format"] = quality or "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
    else:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": "Unknown download mode."}), 400

    @after_this_request
    def _cleanup(resp, _d=tmpdir):  # noqa: ANN001
        shutil.rmtree(_d, ignore_errors=True)
        return resp

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Download failed. {exc}"}), 400

    files = [
        p for p in glob.glob(os.path.join(tmpdir, "*"))
        if os.path.isfile(p) and not p.endswith((".part", ".ytdl", ".temp"))
    ]
    if not files:
        return jsonify({"error": "No file was produced."}), 500
    path = max(files, key=os.path.getsize)
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    version_str = getattr(getattr(yt_dlp, "version", None), "__version__", "unknown")
    print(f"Starting Yoink on http://127.0.0.1:{port} (yt-dlp version: {version_str})")
    app.run(host="127.0.0.1", port=port, debug=True)