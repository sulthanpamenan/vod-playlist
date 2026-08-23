import re
import requests
import streamlink
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin
from concurrent.futures import ThreadPoolExecutor

# =========================================================================
# CONFIGURATION & CONSTANTS
# =========================================================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
WORKER_PROXY = "https://qazaqstan-playlist.sulthan-pamenan.workers.dev/?url="

DAILYMOTION_ITEMS = [
    {"title": "Mohon Doa Restu", "id": "x9qtlim", "genres": "Comedy", "logo": "https://image.tmdb.org/t/p/original/4q8Q0GQS9v2ZeMJnNiq0Its8SE7.jpg", "type": "movie"},
    {"title": "Laura", "id": "x9f73iq", "genres": "Drama", "logo": "https://image.tmdb.org/t/p/original/zVZIcXVMFdbzTTHOThrZX7o2DO7.jpg", "type": "movie"},
    {"title": "Tujuh Hari Untuk Keshia", "id": "x9d736m", "genres": "Drama", "logo": "https://image.tmdb.org/t/p/original/GnCJef0y75lyvI6AVRbRCaqWSi.jpg", "type": "movie"},
    {"title": "Lovely Man", "id": "x917hi4", "genres": "Drama", "logo": "https://image.tmdb.org/t/p/original/2DpL6GyMRJEf6bgGvyWoyQeYlzu.jpg", "type": "movie"},
    {"title": "Father's Haunted House", "id": "x9icyxk", "genres": "Comedy", "logo": "https://image.tmdb.org/t/p/original/qwfVe3no1A2sWtvP2tjYnsEe52i.jpg", "type": "movie"},
    {"title": "Merindu Cahaya De Amstel", "id": "x9a27nu", "genres": "Romance", "logo": "https://image.tmdb.org/t/p/original/uxD1hucihvTToMEoK9HCKkEQiq4.jpg", "type": "movie"},
    {"title": "Pasutri Gaje", "id": "x9kg0yi", "genres": "Comedy", "logo": "https://image.tmdb.org/t/p/original/lY6Y2wNzOgSyLJrE8rzf8QmKZpG.jpg", "type": "movie"}
]

QAZAQSTAN_CATEGORIES = [
    {"group": "Qazaqstan Serials", "url": "https://qazaqstan.tv/serials", "default_genre": "Drama", "default_type": "series"},
    {"group": "Qazaqstan Shows", "url": "https://qazaqstan.tv/projects", "default_genre": "Entertainment", "default_type": "series"},
    {"group": "Qazaqstan Documentaries", "url": "https://qazaqstan.tv/documentaries", "default_genre": "Documentary", "default_type": "movie"}
]

HTTP_SESSION = requests.Session()
HTTP_SESSION.headers.update(HEADERS)

SL_SESSION = streamlink.Streamlink()
SL_SESSION.set_option("http-headers", {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.dailymotion.com/"
})

# =========================================================================
# 1. DAILYMOTION PROCESSOR
# =========================================================================
def process_dailymotion_item(item):
    try:
        streams = SL_SESSION.streams(f"https://www.dailymotion.com/video/{item['id']}")
        if "best" in streams:
            url = streams['best'].url
            genre = item.get("genres") or "Movie"
            c_type = item.get("type", "movie")
            
            meta = f'#EXTINF:-1 vod="1" type="{c_type}" content-type="{c_type}" tvg-logo="{item["logo"]}" group-title="{genre}",{item["title"]}'
            print(f"[SUCCESS DM] {item['title']}")
            return meta, url
    except Exception as e:
        print(f"[ERROR DM] {item['title']}: {e}")
    return None

# =========================================================================
# 2. QAZAQSTAN VOD PROCESSOR
# =========================================================================
def fetch_single_qazaqstan_cat(category):
    group_name = category["group"]
    target_url = category["url"]
    default_genre = category.get("default_genre", "Drama")
    default_type = category.get("default_type", "series")
    entries = []

    # Minta halaman kategori lewat Worker Proxy
    proxied_cat_url = f"{WORKER_PROXY}{quote(target_url, safe='')}"

    try:
        res = HTTP_SESSION.get(proxied_cat_url, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Cari semua elemen tautan video/serial
            visited = set()
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                
                # Filter hanya URL detail tayangan (menghindari link menu utama)
                if not any(k in href for k in ['/videos/', '/projects/', '/serials/', '/episode/']):
                    continue
                if href in visited or href in ["/serials", "/projects", "/documentaries"]:
                    continue

                full_page_url = href if href.startswith('http') else urljoin("https://qazaqstan.tv", href)
                visited.add(href)

                # Ambil Judul
                title = a_tag.get_text(strip=True)
                if not title or len(title) < 3:
                    slug = href.rstrip('/').split('/')[-1]
                    title = slug.replace('-', ' ').title()

                clean_title = re.sub(r'\s+', ' ', title).strip()

                # Ambil Gambar Poster
                logo = "https://qazaqstan.tv/assets/images/logo.png"
                img = a_tag.find('img')
                if img and img.get('src'):
                    logo = img['src']
                    if not logo.startswith('http'):
                        logo = urljoin("https://qazaqstan.tv", logo)

                # BUNGKUS URL HALAMAN DENGAN WORKER
                # Worker nanti yang bertugas mengambil .mp4/.m3u8 saat diklik di OTT Navigator
                stream_url = f"{WORKER_PROXY}{quote(full_page_url, safe='')}"

                meta = f'#EXTINF:-1 vod="1" type="{default_type}" content-type="{default_type}" tvg-logo="{logo}" group-title="{default_genre}",{clean_title}'
                entries.append(meta)
                entries.append(stream_url)
                print(f"[SUCCESS QZ] {clean_title}")

    except Exception as e:
        print(f"[ERROR QZ] Category [{group_name}]: {e}")

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

    print("\n--- Processing Qazaqstan VOD ---")
    with ThreadPoolExecutor(max_workers=3) as executor:
        for res_list in executor.map(fetch_single_qazaqstan_cat, QAZAQSTAN_CATEGORIES):
            m3u.extend(res_list)

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print(f"\n[SUCCESS] `playlist.m3u` updated successfully!")

if __name__ == "__main__":
    generate_vod_playlist()
