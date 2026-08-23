import re
import requests
import streamlink
import xml.etree.ElementTree as ET
from urllib.parse import quote
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

# RSS Feed YouTube Resmi
YOUTUBE_CHANNELS = [
    {"group": "Qazaqstan Serials", "channel_id": "UC94a8mS_JvL2A53e-e-Ea3g", "genre": "Drama"},
    {"group": "Qazaqstan Shows", "channel_id": "UC62R3Mv3o1S4_5G-x_L2K-w", "genre": "Entertainment"}
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
# YOUTUBE VIA RSS FEED (100% STABLE & NO BLOCK)
# =========================================================================
def fetch_youtube_rss(channel_info):
    entries = []
    channel_id = channel_info["channel_id"]
    genre = channel_info["genre"]
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    try:
        res = requests.get(rss_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}

            for entry in root.findall('atom:entry', ns):
                title_elem = entry.find('atom:title', ns)
                yt_vid_elem = entry.find('yt:videoId', ns)

                if title_elem is not None and yt_vid_elem is not None:
                    title = title_elem.text
                    video_id = yt_vid_elem.text
                    
                    thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                    yt_url = f"https://www.youtube.com/watch?v={video_id}"
                    stream_url = f"{WORKER_PROXY}{quote(yt_url, safe='')}"

                    meta = f'#EXTINF:-1 vod="1" type="series" content-type="series" tvg-logo="{thumbnail}" group-title="{genre}",{title}'
                    entries.append(meta)
                    entries.append(stream_url)
                    print(f"[SUCCESS RSS] {title}")

    except Exception as e:
        print(f"[ERROR RSS] {channel_id}: {e}")

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

    print("\n--- Processing YouTube Qazaqstan RSS ---")
    with ThreadPoolExecutor(max_workers=2) as executor:
        for res_list in executor.map(fetch_youtube_rss, YOUTUBE_CHANNELS):
            m3u.extend(res_list)

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print("\n[SUCCESS] `playlist.m3u` updated successfully!")

if __name__ == "__main__":
    generate_vod_playlist()
