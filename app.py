from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
import requests

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"
history = []
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def get_format(quality):
    if quality == "720":
        return "bestvideo[height<=720]+bestaudio/best"
    elif quality == "audio":
        return "bestaudio"
    return "bestvideo+bestaudio/best"

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", history=history)

@app.route("/preview", methods=["POST"])
def preview():
    url = request.json.get("url")
    ydl_opts = {"quiet": True, "noplaylist": True, "http_headers": {"User-Agent": "Mozilla/5.0"}}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return jsonify({"title": info.get("title"), "thumbnail": info.get("thumbnail")})
    except Exception:
        return jsonify({"error": "Preview failed"}), 400

@app.route("/download", methods=["POST"])
def download():
    url = request.form["url"]
    quality = request.form["quality"]

    try:
        cobalt_res = requests.post(
            "https://api.cobalt.tools/",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json={
                "url": url,
                "videoQuality": "720" if quality == "720" else "max",
                "downloadMode": "audio" if quality == "audio" else "auto",
            },
            timeout=30
        )
        data = cobalt_res.json()

        if data.get("status") in ["tunnel", "redirect"]:
            download_url = data.get("url")
            ext = "mp3" if quality == "audio" else "mp4"
            filename = f"{DOWNLOAD_FOLDER}/video.{ext}"
            file_res = requests.get(download_url, stream=True, timeout=60)
            with open(filename, "wb") as f:
                for chunk in file_res.iter_content(chunk_size=8192):
                    f.write(chunk)
            history.insert(0, url)
            return send_file(filename, as_attachment=True)
    except Exception as e:
        print(f"Cobalt failed: {e}")

    ydl_opts = {
        "format": get_format(quality),
        "merge_output_format": "mp4",
        "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
        "quiet": False,
        "noplaylist": True,
        "http_headers": {"User-Agent": "Mozilla/5.0"},
        "extractor_args": {"youtube": {"player_client": ["android"]}}
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        history.insert(0, info.get("title"))
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return f"Download failed: {str(e)}"

if __name__ == "__main__":
    app.run(debug=True)