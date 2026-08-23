import re
import requests
import streamlink
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor

# =========================================================================
# CONFIGURATION & CONSTANTS
# =========================================================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
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

# API Endpoint Internal Qazaqstan
QAZAQSTAN_CATEGORIES = [
    {"group": "Qazaqstan Serials", "api": "https://qazaqstan.tv/api/v1/videos?type=serials", "default_genre": "Drama", "default_type": "series"},
    {"group": "Qazaqstan Shows", "api": "https://qazaqstan.tv/api/v1/videos?type=projects", "default_genre": "Entertainment", "default_type": "series"},
    {"group": "Qazaqstan Documentaries", "api": "https://qazaqstan.tv/api/v1/videos?type=documentaries", "default_genre": "Documentary", "default_type": "movie"}
]

HTTP_SESSION = requests.Session()
HTTP_SESSION.headers.update(HEADERS)

SL_SESSION = streamlink.Streamlink()
SL_SESSION.set_option("http-headers", {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.dailymotion.com/"
})

GENRE_PATTERNS = [
    (re.compile(r'balapan|мульт|балалар|детский|animation|kids|anime', re.I), "Kids", "anime"),
    (re.compile(r'serial|телехикая|сериал|series|episode', re.I), "Drama", "series"),
    (re.compile(r'фильм|кино|драма|movie|cinema', re.I), "Drama", "movie"),
    (re.compile(r'show|шоу|жоба|проекты|проектами|бағдарлама|tv show|entertainment', re.I), "Entertainment", "series"),
    (re.compile(r'doc|дерек|документальный|история|тарих|documentary', re.I), "Documentary", "movie"),
    (re.compile(r'news|жаңалық|спорт|sport|хабар|ақпарат|новости', re.I), "News & Sports", "movie"),
    (re.compile(r'comed|комед|әзіл|юмор', re.I), "Comedy", "movie"),
    (re.compile(r'romanc|махаббат|мелодрам', re.I), "Romance", "movie")
]

def detect_meta(title, default_g="General", default_t="movie"):
    for pattern, genre, c_type in GENRE_PATTERNS:
        if pattern.search(title):
            return genre, c_type
    return default_g, default_t

# =========================================================================
# 1. DAILYMOTION PROCESSOR
# =========================================================================
def process_dailymotion_item(item):
    try:
        streams = SL_SESSION.streams(f"https://www.dailymotion.com/video/{item['id']}")
        if "best" in streams:
            url = streams['best'].url
            c_type = item.get("type", "movie")
            genre = item.get("genres", "Comedy")
            meta = f'#EXTINF:-1 vod="1" type="{c_type}" content-type="{c_type}" tvg-logo="{item["logo"]}" group-title="{genre}",{item["title"]}'
            print(f"[SUCCESS DM] {item['title']}")
            return meta, url
    except Exception as e:
        print(f"[ERROR DM] {item['title']}: {e}")
    return None

def fetch_all_dailymotion():
    m3u_entries = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(process_dailymotion_item, DAILYMOTION_ITEMS)
    for res in results:
        if res:
            m3u_entries.append(res[0])
            m3u_entries.append(res[1])
    return m3u_entries

# =========================================================================
# 2. QAZAQSTAN VOD PROCESSOR (VIA API JSON)
# =========================================================================
def fetch_single_qazaqstan_cat(category):
    group_name = category["group"]
    api_endpoint = category["api"]
    def_genre = category.get("default_genre", "General")
    def_type = category.get("default_type", "movie")
    entries = []

    proxied_api_url = f"{WORKER_PROXY}{quote(api_endpoint, safe='')}"

    try:
        res = HTTP_SESSION.get(proxied_api_url, timeout=12)
        if res.status_code == 200:
            json_response = res.json()
            items = json_response.get('data', []) if isinstance(json_response, dict) else json_response

            for item in items:
                title = item.get('title') or item.get('name')
                logo = item.get('poster') or item.get('image') or "https://qazaqstan.tv/assets/images/logo.png"
                
                # Mengambil URL video langsung jika tersedia di API, atau membuat URL detail halaman
                video_url = item.get('file_url') or item.get('video_url') or item.get('url')
                if not video_url:
                    item_id = item.get('id')
                    if item_id:
                        video_url = f"https://qazaqstan.tv/videos/{item_id}"

                if not title or not video_url:
                    continue

                genre, c_type = detect_meta(title, def_genre, def_type)

                stream_url = f"{WORKER_PROXY}{quote(video_url, safe='')}"
                meta = f'#EXTINF:-1 vod="1" type="{c_type}" content-type="{c_type}" tvg-logo="{logo}" group-title="{genre}",{title}'
                
                entries.append(meta)
                entries.append(stream_url)
                print(f"[SUCCESS QZ API] {title}")

    except Exception as e:
        print(f"[ERROR QZ] Category [{group_name}]: {e}")

    return entries

def fetch_all_qazaqstan():
    m3u_entries = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = executor.map(fetch_single_qazaqstan_cat, QAZAQSTAN_CATEGORIES)
    for res_list in results:
        m3u_entries.extend(res_list)
    return m3u_entries

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
    dm_entries = fetch_all_dailymotion()
    m3u.extend(dm_entries)

    print("\n--- Processing Qazaqstan VOD ---")
    qz_entries = fetch_all_qazaqstan()
    m3u.extend(qz_entries)

    output_filename = "playlist.m3u"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print(f"\n[SUCCESS] Combined VOD `{output_filename}` updated successfully!")

if __name__ == "__main__":
    generate_vod_playlist()
