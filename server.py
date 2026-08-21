from flask import Flask, redirect, Response
import streamlink

app = Flask(__name__)

session = streamlink.Streamlink()
session.set_option("http-headers", {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.dailymotion.com/"
})

@app.route('/play/<dm_id>')
def play_vod(dm_id):
    dm_url = f"https://www.dailymotion.com/video/{dm_id}"
    try:
        streams = session.streams(dm_url)
        if "best" in streams:
            real_m3u8 = streams["best"].url
            return redirect(real_m3u8, code=302)
    except Exception as e:
        print(f"[!] Error fetching {dm_id}: {e}")
    
    return Response("Stream not available or blocked", status=404)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
