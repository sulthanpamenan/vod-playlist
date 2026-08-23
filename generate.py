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

# 1. DAILYMOTION VOD ITEMS
DAILYMOTION_ITEMS = [
    {"title": "Mohon Doa Restu", "id": "x9qtlim", "genres": "Comedy", "logo": "https://image.tmdb.org/t/p/original/4q8Q0GQS9v2ZeMJnNiq0Its8SE7.jpg"},
    {"title": "Laura", "id": "x9f73iq", "genres": "Drama", "logo": "https://image.tmdb.org/t/p/original/zVZIcXVMFdbzTTHOThrZX7o2DO7.jpg"},
    {"title": "Tujuh Hari Untuk Keshia", "id": "x9d736m", "genres": "Drama", "logo": "https://image.tmdb.org/t/p/original/GnCJef0y75lyvI6AVRbRCaqWSi.jpg"},
    {"title": "Lovely Man", "id": "x917hi4", "genres": "Drama", "logo": "https://image.tmdb.org/t/p/original/2DpL6GyMRJEf6bgGvyWoyQeYlzu.jpg"},
    {"title": "Father's Haunted House", "id": "x9icyxk", "genres": "Comedy", "logo": "https://image.tmdb.org/t/p/original/qwfVe3no1A2sWtvP2tjYnsEe52i.jpg"},
    {"title": "Merindu Cahaya De Amstel", "id": "x9a27nu", "genres": "Romance", "logo": "https://image.tmdb.org/t/p/original/uxD1hucihvTToMEoK9HCKkEQiq4.jpg"},
    {"title": "Pasutri Gaje", "id": "x9kg0yi", "genres": "Comedy", "logo": "https://image.tmdb.org/t/p/original/lY6Y2wNzOgSyLJrE8rzf8QmKZpG.jpg"}
]

# 2. QAZAQSTAN VOD TARGET CATEGORIES
QAZAQSTAN_CATEGORIES = [
    {"group": "Qazaqstan Serials", "url": "https://qazaqstan.tv/serials"},
    {"group": "Qazaqstan Shows", "url": "https://qazaqstan.tv/projects"},
    {"group": "Qazaqstan Documentaries", "url": "https://qazaqstan.tv/documentaries"}
]

HTTP_SESSION = requests.Session()
HTTP_SESSION.headers.update(HEADERS)

# =========================================================================
# 1. DAILYMOTION PROCESSOR
# =========================================================================
def process_dailymotion_item(item):
    session = streamlink.Streamlink()
    session.set_option("http-headers", {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.dailymotion.com/"
    })
    
    try:
        streams = session.streams(f"https://www.dailymotion.com/video/{item['id']}")
        if "best" in streams:
            url = streams['best'].url
            meta = f'#EXTINF:-1 vod="1" type="movie" content-type="movie" tvg-logo="{item["logo"]}" group-title="{item["genres"]}",{item["title"]}'
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
            meta, url = res
            m3u_entries.append(meta)
            m3u_entries.append(url)
    return m3u_entries

# =========================================================================
# 2. QAZAQSTAN VOD PROCESSOR
# =========================================================================
def fetch_single_qazaqstan_cat(category):
    group_name = category["group"]
    target_url = category["url"]
    entries = []

    proxied_url = f"{WORKER_PROXY}{quote(target_url, safe='')}"

    try:
        res = HTTP_SESSION.get(proxied_url, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            cards = soup.find_all(['a', 'div'], class_=re.compile(r'card|item|video|project|serial', re.I))

            visited_links = set()
            for card in cards:
                href = card.get('href') or (card.find('a').get('href') if card.find('a') else "")
                if not href or href in visited_links or href == "#": 
                    continue

                full_page_url = href if href.startswith('http') else urljoin("https://qazaqstan.tv", href)
                visited_links.add(href)

                title_elem = card.find(['h3', 'h4', 'span', 'p', 'div'], class_=re.compile(r'title|name|label', re.I))
                title = title_elem.get_text(strip=True) if title_elem else card.get_text(strip=True)
                title = re.sub(r'\s+', ' ', title).strip()
                if not title or len(title) < 3 or title.lower() in ['barlyq', 'все', 'more']: 
                    continue

                img_elem = card.find('img')
                logo = img_elem.get('src', '') if img_elem else ""
                if logo and not logo.startswith('http'):
                    logo = urljoin("https://qazaqstan.tv", logo)

                # Ekstraksi URL Stream .m3u8 asli di dalam halaman detail
                try:
                    detail_res = HTTP_SESSION.get(full_page_url, timeout=8)
                    if detail_res.status_code == 200:
                        m3u8_match = re.search(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', detail_res.text)
                        if m3u8_match:
                            raw_m3u8 = m3u8_match.group(0)
                            stream_url = f"{WORKER_PROXY}{quote(raw_m3u8, safe='')}"
                            meta = f'#EXTINF:-1 vod="1" tvg-logo="{logo}" group-title="{group_name}",{title}'
                            entries.append(meta)
                            entries.append(stream_url)
                            print(f"[SUCCESS QZ STREAM] {title}")
                except Exception as err:
                    print(f"[SKIP QZ] Gagal mengambil m3u8 untuk {title}: {err}")

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
        "<!--more-->",
        "<html>",
        "<head>",
        '<meta charset="utf-8">',
        '<meta http-equiv="X-UA-Compatible" content="IE=edge">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<script language=\"javascript\">",
        'window.location.replace("https://sulthanpamenan.github.io/vod-playlist/");',
        "</script>",
        "</head></html>",
        "",
        "<================== PLAYLIST AUTOGENERATED BY SUTAN PAMENAN ==================>",
        "<================== IF YOU FIND THIS PLAYLIST, PLEASE DO NOT SELL OR DISTRIBUTE IT FOR PERSONAL GAIN ==================>",
        "",
        "#EXTM3U",
        ""
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
