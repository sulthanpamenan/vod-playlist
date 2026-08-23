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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://qazaqstan.tv/"
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
# DAILYMOTION
# =========================================================================
def process_dailymotion_item(item):
    try:
        streams = SL_SESSION.streams(f"https://www.dailymotion.com/video/{item['id']}")
        if "best" in streams:
            url = streams['best'].url
            c_type = item.get("type", "movie")
            genre = item.get("genres", "Comedy")
            meta = f'#EXTINF:-1 vod="1" type="{c_type}" content-type="{c_type}" tvg-logo="{item["logo"]}" group-title="{genre}",{item["title"]}'
            return meta, url
    except Exception as e:
        print(f"[ERROR DM] {item['title']}: {e}")
    return None

# =========================================================================
# QAZAQSTAN EXTRACTOR
# =========================================================================
def extract_qazaqstan_stream(video_page_url):
    """Mengekstrak URL .mp4 / .m3u8 dari dalam tag script/JSON di halaman detail"""
    try:
        res = HTTP_SESSION.get(video_page_url, timeout=10)
        if res.status_code == 200:
            html = res.text
            # Match 1: Ekstrak URL mp4/m3u8 langsung
            match = re.search(r'(https?://[^\s\'"]+\.(?:mp4|m3u8)[^\s\'"]*)', html, re.I)
            if match:
                return match.group(1).replace('\\', '')

            # Match 2: Cari URL iframe tersembunyi
            iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
            if iframe_match:
                iframe_url = iframe_match.group(1)
                if iframe_url.startswith('//'):
                    iframe_url = 'https:' + iframe_url
                res_iframe = HTTP_SESSION.get(iframe_url, timeout=10)
                match_iframe = re.search(r'(https?://[^\s\'"]+\.(?:mp4|m3u8)[^\s\'"]*)', res_iframe.text, re.I)
                if match_iframe:
                    return match_iframe.group(1).replace('\\', '')
    except Exception as e:
        print(f"[EXTRACT FAILED] {video_page_url}: {e}")
    return None

def fetch_single_qazaqstan_cat(category):
    group_name = category["group"]
    target_url = category["url"]
    def_genre = category.get("default_genre", "General")
    def_type = category.get("default_type", "movie")
    entries = []

    try:
        res = HTTP_SESSION.get(target_url, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            visited_ids = set()

            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if '/videos/' not in href:
                    continue

                video_id_match = re.search(r'/videos/(\d+)', href)
                if not video_id_match:
                    continue
                
                video_id = video_id_match.group(1)
                if video_id in visited_ids:
                    continue
                visited_ids.add(video_id)

                full_page_url = href if href.startswith('http') else urljoin("https://qazaqstan.tv", href)

                # Dapatkan URL media langsung
                direct_media_url = extract_qazaqstan_stream(full_page_url)
                
                # JIKA EXTRACTOR GAGAL: Tetap masukkan URL halaman, tetapi dibungkus Proxy
                if not direct_media_url:
                    stream_url = f"{WORKER_PROXY}{quote(full_page_url, safe='')}"
                else:
                    stream_url = f"{WORKER_PROXY}{quote(direct_media_url, safe='')}"

                title = a_tag.get_text(strip=True)
                if not title or title.lower() in ['онлайн көру', 'толығырақ', '']:
                    parent = a_tag.find_parent(['div', 'article'])
                    if parent:
                        h_tag = parent.find(['h2', 'h3', 'h4'])
                        if h_tag:
                            title = h_tag.get_text(strip=True)

                if not title or title.lower() in ['онлайн көру', 'толығырақ']:
                    title = f"Episode {video_id}"

                clean_title = re.sub(r'\s+', ' ', title).strip()

                img_elem = a_tag.find('img')
                logo = img_elem.get('src', '') if img_elem else ""
                if logo and not logo.startswith('http'):
                    logo = urljoin("https://qazaqstan.tv", logo)
                if not logo:
                    logo = "https://qazaqstan.tv/assets/images/logo.png"

                meta = f'#EXTINF:-1 vod="1" type="{def_type}" content-type="{def_type}" tvg-logo="{logo}" group-title="{def_genre}",{clean_title}'
                
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

    print("\n[SUCCESS] `playlist.m3u` updated successfully!")

if __name__ == "__main__":
    generate_vod_playlist()
