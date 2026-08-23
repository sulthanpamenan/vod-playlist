import re
import requests
import streamlink
import yt_dlp
from concurrent.futures import ThreadPoolExecutor

# =========================================================================
# CONFIGURATION
# =========================================================================
WORKER_PROXY = "https://qazaqstan-playlist.sulthan-pamenan.workers.dev/?url="

DAILYMOTION_ITEMS = [
    {"title": "Mohon Doa Restu", "id": "x9qtlim", "genres": "Comedy", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/4q8Q0GQS9v2ZeMJnNiq0Its8SE7.jpg"},
    {"title": "Laura", "id": "x9f73iq", "genres": "Drama", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/zVZIcXVMFdbzTTHOThrZX7o2DO7.jpg"},
    {"title": "Tujuh Hari Untuk Keshia", "id": "x9d736m", "genres": "Drama", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/GnCJef0y75lyvI6AVRbRCaqWSi.jpg"},
    {"title": "Lovely Man", "id": "x917hi4", "genres": "Drama", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/2DpL6GyMRJEf6bgGvyWoyQeYlzu.jpg"},
    {"title": "Father's Haunted House", "id": "x9icyxk", "genres": "Comedy", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/qwfVe3no1A2sWtvP2tjYnsEe52i.jpg"},
    {"title": "Merindu Cahaya De Amstel", "id": "x9a27nu", "genres": "Romance", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/uxD1hucihvTToMEoK9HCKkEQiq4.jpg"},
    {"title": "Pasutri Gaje", "id": "x9kg0yi", "genres": "Comedy", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/lY6Y2wNzOgSyLJrE8rzf8QmKZpG.jpg"}
]

# Tambahkan URL Playlist/Channel Resmi Qazaqstan dari YouTube di sini
YOUTUBE_SOURCES = [
    {"group": "Qazaqstan Serials", "url": "https://www.youtube.com/@qazaqstan_serials/videos", "genre": "Drama"},
    {"group": "Qazaqstan Shows", "url": "https://www.youtube.com/@QazaqstanTV/videos", "genre": "Entertainment"}
]

SL_SESSION = streamlink.Streamlink()
SL_SESSION.set_option("http-headers", {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.dailymotion.com/"
})

# =========================================================================
# DAILYMOTION EXTRACTOR
# =========================================================================
def process_dailymotion_item(item):
    try:
        streams = SL_SESSION.streams(f"https://www.dailymotion.com/video/{item['id']}")
        if "best" in streams:
            url = streams['best'].url
            meta = f'#EXTINF:-1 vod="1" type="{item.get("type", "movie")}" content-type="{item.get("type", "movie")}" tvg-logo="{item["logo"]}" group-title="{item.get("genres", "Comedy")}",{item["title"]}'
            return meta, url
    except Exception as e:
        print(f"[ERROR DM] {item['title']}: {e}")
    return None

# =========================================================================
# YOUTUBE QAZAQSTAN EXTRACTOR
# =========================================================================
def fetch_youtube_source(source):
    entries = []
    group = source["group"]
    url = source["url"]
    genre = source["genre"]

    ydl_opts = {
        'extract_flat': True,
        'playlistend': 15,  # Mengambil 15 video terbaru per channel
        'quiet': True,
        'no_warnings': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                for entry in info['entries']:
                    title = entry.get('title')
                    video_id = entry.get('id')
                    thumbnail = entry.get('thumbnail', 'https://qazaqstan.tv/assets/images/logo.png')
                    
                    if not title or not video_id:
                        continue

                    # URL video YouTube yang dapat diputar
                    yt_video_url = f"https://www.youtube.com/watch?v={video_id}"
                    
                    meta = f'#EXTINF:-1 vod="1" type="series" content-type="series" tvg-logo="{thumbnail}" group-title="{genre}",{title}'
                    entries.append(meta)
                    entries.append(yt_video_url)
                    print(f"[SUCCESS YT] {title}")

    except Exception as e:
        print(f"[ERROR YT] Source [{group}]: {e}")

    return entries

# =========================================================================
# MAIN GENERATOR
# =========================================================================
def generate_vod_playlist():
    print("[*] Starting VOD Playlist Generation...")

    m3u = [
        "<!--more-->", "<html>", "<head>", '<meta charset="utf-8">',
        '<meta http-equiv="X-UA-Compatible" content="IE=edge">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<script language=\"javascript\">",
        'window.location.replace("https://sulthanpamenan.github.io/vod-playlist/");',
        "</script>", "</head></html>", "",
        "<================== PLAYLIST AUTOGENERATED BY SUTAN PAMENAN ==================>",
        "<================== IF YOU FIND THIS PLAYLIST, PLEASE DO NOT SELL OR DISTRIBUTE IT FOR PERSONAL GAIN ==================>",
        "", "#EXTM3U", ""
    ]

    print("\n--- Processing Dailymotion VOD ---")
    with ThreadPoolExecutor(max_workers=4) as executor:
        for res in executor.map(process_dailymotion_item, DAILYMOTION_ITEMS):
            if res:
                m3u.append(res[0])
                m3u.append(res[1])

    print("\n--- Processing YouTube Qazaqstan VOD ---")
    with ThreadPoolExecutor(max_workers=2) as executor:
        for res_list in executor.map(fetch_youtube_source, YOUTUBE_SOURCES):
            m3u.extend(res_list)

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print("\n[SUCCESS] `playlist.m3u` updated successfully!")

if __name__ == "__main__":
    generate_vod_playlist()
