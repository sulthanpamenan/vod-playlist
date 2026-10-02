import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse, urlunparse
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= CONFIGURASI DENS.TV =================
USER_ID_TARGET = "wnctpm5uf2j"
TMDB_API_KEY = "f5b601ec011f9760c7fb6752670714cf"
HEADERS_SUFFIX = "|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36&Origin=https://www.dens.tv&Referer=https://www.dens.tv/"

CATEGORIES = [
    {"name": "New Production", "id": "5544", "slug": "new-production"},
    {"name": "New Release", "id": "5551", "slug": "new-release"},
    {"name": "Exclusive", "id": "3774", "slug": "exclusive"},
    {"name": "Drama", "id": "5", "slug": "drama"},
    {"name": "Horror & Thriller", "id": "7", "slug": "horror-thriller"},
    {"name": "Comedy", "id": "56", "slug": "comedy"},
    {"name": "Cerita Indonesia", "id": "5501", "slug": "cerita-indonesia"},
    {"name": "Food & Cooking", "id": "4570", "slug": "food"},
    {"name": "Lifestyle & Travels", "id": "5764", "slug": "lifestyle-travels"},
    {"name": "Music", "id": "5756", "slug": "music"},
    {"name": "Variety Show", "id": "4712", "slug": "variety-show"},
    {"name": "Sports & Hobbies", "id": "1118", "slug": "sports-and-hobbies"},
]

SESSION_DENSTV = requests.Session()
SESSION_DENSTV.verify = False
adapter_dens = HTTPAdapter(pool_connections=20, pool_maxsize=20)
SESSION_DENSTV.mount("https://", adapter_dens)
SESSION_DENSTV.mount("http://", adapter_dens)

SESSION_DENSTV.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "Referer": "https://www.dens.tv/",
    "Accept": "*/*"
})

# ================= CONFIGURASI FREELIVESPORTS =================
FLS_BASE_URL = "https://api.gizmott.com"
FLS_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "channelid": "516",
    "country_code": "ID",
    "dev_id": "5d01d64ac5b0026957052f0330129fc6",
    "device_type": "web",
    "pubid": "50183",
    "origin": "https://freelivesports.tv",
    "referer": "https://freelivesports.tv/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
}

def create_fls_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.headers.update(FLS_HEADERS)
    return session

def fls_authenticate(session):
    url = f"{FLS_BASE_URL}/api/v1/account/authenticate"
    headers = {"uid": "7938114"}
    response = session.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("token")
    else:
        raise Exception(f"FLS authentication failed: {response.text}")

def fls_get_home_data(session, token):
    url = f"{FLS_BASE_URL}/api/v2/home"
    headers = {"access-token": token, "uid": "7938114"}
    response = session.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"    [!] Failed to retrieve FLS home data: {response.text}")
        return {}

def process_fls_show(session, access_token, show):
    show_id = show.get("show_id")
    show_name = show.get("show_name") or show.get("title") or "Unknown"
    vanity_url = show.get("vanity_url") or show.get("show_name")
    logo = show.get("logo") or show.get("thumbnail") or ""

    try:
        details_url = f"{FLS_BASE_URL}/api/v2/video/details/{requests.utils.quote(str(vanity_url))}?show_id={show_id}"
        headers = {"access-token": access_token, "uid": "7938114"}
        
        res_details = session.get(details_url, headers=headers, timeout=10)
        if res_details.status_code != 200:
            return None
            
        details = res_details.json().get("data", {})
        
        categories = details.get("categories", [])
        primary_category = categories[0].get("category_name", "Free Live Sports VOD") if categories else "Free Live Sports VOD"
        
        show_type = "movie"
        if "season" in details or details.get("single_video") == 0:
            show_type = "series"

        resolutions = details.get("resolutions", [])
        playlist_url = next((r.get("url") for r in resolutions if r.get("type") == "auto"), None)
        if not playlist_url and resolutions:
            playlist_url = resolutions[0].get("url")
            
        if not playlist_url:
            return None

        token_url = f"{FLS_BASE_URL}/api/v1/playlistV2/generateToken?id={requests.utils.quote(playlist_url, safe='')}"
        res_token = session.get(token_url, headers=headers, timeout=10)
        if res_token.status_code != 200:
            return None
            
        stream_token = res_token.json().get("data")
        if not stream_token:
            return None
            
        final_m3u8_url = f"{FLS_BASE_URL}/api/v1/playlistV2/playlist.m3u8?id={playlist_url}&token={stream_token}&type=video&pubid=50183"
        
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
        ref = "https://freelivesports.tv/"
        stream_url_with_headers = f"{final_m3u8_url}|User-Agent={ua}&Referer={ref}"
        
        entry = {
            "id": str(show_id),
            "title": show_name,
            "poster": logo,
            "genre": primary_category,
            "type": show_type,
            "stream": stream_url_with_headers
        }
        print(f"    [FLS ✓] {show_name} [{primary_category}]")
        return entry
        
    except Exception as e:
        print(f"    [FLS ✗] Failed to process {show_name}: {e}")
        return None

# ================= DENS.TV FUNCTIONS =================
def fetch_tmdb_id(title, media_type="tv"):
    if not TMDB_API_KEY or TMDB_API_KEY == "f5b601ec011f9760c7fb6752670714cf":
        return ""
    try:
        clean_title = re.sub(r'\s*\(.*?\)', '', title).strip()
        url = f"https://api.themoviedb.org/3/search/{media_type}"
        params = {"api_key": TMDB_API_KEY, "query": clean_title}
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            results = res.json().get("results", [])
            if results:
                return str(results[0].get("id", ""))
    except Exception:
        pass
    return ""

def format_stream_url(raw_url, content_id):
    if not raw_url:
        return ""
    parsed = urlparse(raw_url)
    path = re.sub(r"/S\d+/[^/]+\.m3u8", "/index5.m3u8", parsed.path)
    path = re.sub(r"/mnf\.m3u8", "/index5.m3u8", path)
    path = re.sub(r"/index\d+\.m3u8", "/index5.m3u8", path)

    query_dict = parse_qs(parsed.query)
    query_dict["app_type"] = ["web"]
    query_dict["userid"] = [USER_ID_TARGET]
    if content_id:
        query_dict["movieid"] = [str(content_id)]

    return urlunparse(parsed._replace(path=path, query=urlencode(query_dict, doseq=True)))

def get_series_by_category(cat_id, cat_slug):
    all_series = []
    page = 1
    while True:
        url = f"https://www.dens.tv/movie/related/{cat_id}/{cat_slug}?page={page}&limit=50&json=true"
        try:
            res = SESSION_DENSTV.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json().get("data", {})
                series = data.get("movies", []) or data.get("series", [])
                if not series:
                    break
                all_series.extend(series)
                page += 1
            else:
                break
        except Exception as e:
            print(f"    [!] Failed to fetch page {page} Dens.tv category {cat_slug}: {e}")
            break
    return all_series

def get_episodes_by_series(series_id, series_slug):
    all_episodes = []
    page = 1
    while True:
        url = f"https://www.dens.tv/movie/series/{series_id}/{series_slug}?page={page}&limit=50&json=true"
        try:
            res = SESSION_DENSTV.get(url, timeout=10)
            if res.status_code == 200:
                episodes = res.json().get("data", {}).get("movies", [])
                if not episodes:
                    break
                all_episodes.extend(episodes)
                page += 1
            else:
                break
        except Exception as e:
            print(f"    [!] Failed to retrieve episodes page {page} series Dens.tv {series_id}: {e}")
            break
    return all_episodes

# ================= MAIN =================
def main():
    print("==================================================")
    print("[UNIFIED VOD SCRAPER] Dens.tv & FreeLiveSports...")
    print("==================================================")

    header_content = [
        "#EXTM3U",
        "", "<html>", "<body>", '<meta charset="utf-8">',
        '<meta http-equiv="X-UA-Compatible" content="IE=edge">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<script language=\"javascript\">",
        'window.location.replace("https://sulthanpamenan.github.io/vod-playlist/");',
        "</script>", "</body></html>", "",
        "<================== PLAYLIST AUTOGENERATED BY SUTAN PAMENAN ==================>",
        "<================== IF YOU FIND THIS PLAYLIST, PLEASE DO NOT SELL OR DISTRIBUTE FOR PERSONAL GAIN ==================>",
        ""
    ]

    with open("series.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(header_content) + "\n\n")

    unique_episodes = {}
    tmdb_cache = {}
    series_cache = {}

    # 1. Retrieve DENS.TV Data
    print("\n--- [1/2] Retrieving Data from Dens.tv ---")
    for cat in CATEGORIES:
        print(f"[*] Dens.tv Category Fetching: {cat['name']}...")
        series_list = get_series_by_category(cat["id"], cat["slug"])
        print(f"    Found {len(series_list)} items in category {cat['name']}")
        
        uncached_series = [s for s in series_list if s.get("movie_id") and s.get("movie_id") not in series_cache]
        
        if uncached_series:
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_parent = {
                    executor.submit(get_episodes_by_series, s["movie_id"], s.get("slug", "")): s["movie_id"] 
                    for s in uncached_series if s.get("movie_id")
                }
                for future in as_completed(future_to_parent):
                    s_id = future_to_parent[future]
                    try:
                        res = future.result()
                        series_cache[s_id] = res if res else []
                    except Exception:
                        series_cache[s_id] = []

        for parent in series_list:
            p_id = parent.get("movie_id")
            p_title = parent.get("title", "")
            if not p_id:
                continue

            if p_title not in tmdb_cache:
                tmdb_cache[p_title] = fetch_tmdb_id(p_title, "tv")
            parent_tmdb_id = tmdb_cache[p_title]

            episodes = series_cache.get(p_id, [])
            if not episodes:
                episodes = [parent]

            for idx, ep in enumerate(episodes, start=1):
                ep_id = ep.get("movie_id")
                if ep_id and ep_id not in unique_episodes:
                    raw_stream = ep.get("extra", {}).get("stream", {}).get("play_url", "")
                    if not raw_stream:
                        raw_stream = ep.get("file", "")

                    formatted_stream = format_stream_url(raw_stream, ep_id)
                    
                    poster = ep.get("url_handle", {}).get("img_port_large", "")
                    if not poster:
                        poster = ep.get("image", "")

                    ep_title = ep.get("title", p_title)
                    season_num = str(ep.get("season", 1)) if ep.get("season") else "1"
                    episode_num = str(ep.get("episode", idx)) if ep.get("episode") else str(idx)

                    if formatted_stream:
                        unique_episodes[ep_id] = {
                            "id": str(ep_id),
                            "title": ep_title,
                            "serie_title": p_title,
                            "tmdb_id": parent_tmdb_id,
                            "poster": poster,
                            "genre": cat["name"],
                            "type": "series",
                            "season": season_num,
                            "episode": episode_num,
                            "stream": formatted_stream + HEADERS_SUFFIX
                        }

    print(f"[✓] Dens.tv completed: {len(unique_episodes)} items collected.")

    # 2. Retrieve FreeLiveSports Data
    print("\n--- [2/2] Retrieving Data from FreeLiveSports ---")
    fls_session = create_fls_session()
    try:
        print("[*] Performing FLS authentication...")
        fls_token = fls_authenticate(fls_session)
        print("[*] Retrieving the VOD list from the FLS homepage...")
        fls_home_data = fls_get_home_data(fls_session, fls_token)
        
        fls_shows = []
        def extract_fls_shows(obj):
            if isinstance(obj, dict):
                if "show_id" in obj and ("vanity_url" in obj or "show_name" in obj):
                    fls_shows.append(obj)
                for k, v in obj.items():
                    extract_fls_shows(v)
            elif isinstance(obj, list):
                for item in obj:
                    extract_fls_shows(item)
                    
        extract_fls_shows(fls_home_data)
        fls_unique_shows = list({s["show_id"]: s for s in fls_shows}.values())
        print(f"    Found {len(fls_unique_shows)} unique FLS VODs. Processing in parallel...")

        fls_count = 0
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(process_fls_show, fls_session, fls_token, show) for show in fls_unique_shows]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    item_key = f"fls_{result['id']}"
                    if item_key not in unique_episodes:
                        unique_episodes[item_key] = result
                        fls_count += 1
        print(f"[✓] FreeLiveSports complete: {fls_count} items successfully added.")
    except Exception as e:
        print(f"[!] Failed to process FreeLiveSports: {e}")

    # 3. Write to M3U file
    print("\n==================================================")
    print(f"Writing a total of {len(unique_episodes)} items to series.m3u...")
    print("==================================================")

    count = 0
    with open("series.m3u", "a", encoding="utf-8") as f:
        for item_key, data in unique_episodes.items():
            if data.get("type") == "series":
                formatted_line_title = f"{data['serie_title']} S0{data['season']}E0{ep_num} - {data['title']}" if len(ep_num) == 1 else f"{data['serie_title']} S0{data['season']}E{ep_num} - {data['title']}"
                f.write(f'#EXTINF:-1 vod="1" type="series" content-type="series" tvg-tmdb="{data.get("tmdb_id", "")}" serie-title="{data.get("serie_title", data["title"])}" tvg-season="{data.get("season", "1")}" tvg-episode="{ep_num}" tvg-logo="{data["poster"]}" group-title="{data["genre"]}",{formatted_line_title}\n')
            else:
                f.write(f'#EXTINF:-1 vod="1" type="{data.get("type", "movie")}" content-type="{data.get("type", "movie")}" tvg-logo="{data["poster"]}" group-title="{data["genre"]}",{data["title"]}\n')
            
            f.write(f'{data["stream"]}\n\n')
            count += 1

    print("==================================================")
    print(f"[COMPLETED] A total of {count} items were successfully saved to series.m3u")
    print("==================================================")

if __name__ == "__main__":
    main()
