import json
import os
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from difflib import SequenceMatcher
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TMDB_CACHE = {}
TMDB_CACHE_FILE = "tmdb_cache.json"

if os.path.exists(TMDB_CACHE_FILE):
    try:
        with open(TMDB_CACHE_FILE, "r", encoding="utf-8") as f:
            TMDB_CACHE = json.load(f)
    except Exception:
        TMDB_CACHE = {}

def save_tmdb_cache():
    try:
        with open(TMDB_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(TMDB_CACHE, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

def clean_title(raw_title):
    cleaned = re.sub(r'\s*\|\s*(Not Rated|Rated.*$)', '', raw_title, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*\(\d+\s*Episodes?\)', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*-\s*\d+\s*Episodes?', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*\(\d{4}\)', '', cleaned)
    cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
    return ' '.join(cleaned.split())

def clean_episode_title(ep_title, parent_title):
    cleaned_ep = ep_title
    base_parent_words = parent_title.split("(")[0].strip()
    pattern_prefix = r'^' + re.escape(base_parent_words) + r'[\s\:\-\–\b]+(Eps\.?\s*\d+[\s\:\-\–\b]*)?'
    cleaned_ep = re.sub(pattern_prefix, '', cleaned_ep, flags=re.IGNORECASE)
    cleaned_ep = re.sub(r'^Eps\.?\s*\d+\s*[:\-–]\s*', '', cleaned_ep, flags=re.IGNORECASE)
    cleaned_ep = re.sub(r'\s*\|\s*(Not Rated|Rated.*$)', '', cleaned_ep, flags=re.IGNORECASE)
    return cleaned_ep.strip() if cleaned_ep.strip() else ep_title.strip()

def is_title_similar(a, b, threshold=0.4):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold

def fetch_tmdb_id(title, tmdb_api_key, media_type="movie", year=None):
    if not tmdb_api_key:
        return ""
    
    extracted_year = str(year) if year else None
    match_year = re.search(r'\((\d{4})\)', title)
    if match_year and not extracted_year:
        extracted_year = match_year.group(1)

    clean_t = clean_title(title)
    if not clean_t:
        return ""
    
    cache_key = f"{clean_t}_{extracted_year}" if extracted_year else clean_t
    if cache_key in TMDB_CACHE and TMDB_CACHE[cache_key] != "":
        return TMDB_CACHE[cache_key]
        
    if clean_t in TMDB_CACHE and TMDB_CACHE[clean_t] != "":
        return TMDB_CACHE[clean_t]

    url = f"https://api.themoviedb.org/3/search/{media_type}"
    try:
        params = {"api_key": tmdb_api_key, "query": clean_t}
        res = requests.get(url, params=params, timeout=5)
        
        if res.status_code == 200:
            results = res.json().get("results", [])
            if results:
                best_match_id = ""
                highest_score = 0.0
                
                for item in results:
                    item_title = item.get("title") or item.get("name") or ""
                    date_str = item.get("release_date") or item.get("first_air_date") or ""
                    item_year = date_str.split("-")[0] if date_str else ""
                    
                    score = SequenceMatcher(None, clean_t.lower(), item_title.lower()).ratio()
                    
                    if extracted_year and item_year:
                        if item_year == extracted_year:
                            score += 0.3
                        elif abs(int(item_year) - int(extracted_year)) <= 2:
                            score += 0.15

                    clean_t_lower = clean_t.lower()
                    item_title_lower = item_title.lower()
                    
                    if clean_t_lower == item_title_lower:
                        score += 0.4
                    elif clean_t_lower in item_title_lower:
                        if not item_title_lower.startswith(clean_t_lower):
                            score -= 0.25

                    if score > highest_score:
                        highest_score = score
                        best_match_id = str(item.get("id", ""))

                if best_match_id and highest_score >= 0.5:
                    TMDB_CACHE[cache_key] = best_match_id
                    print(f"[TMDB] Matched '{clean_t}' (Score: {highest_score:.2f}) -> ID: {best_match_id}")
                    return best_match_id

                tmdb_id = str(results[0].get("id", ""))
                TMDB_CACHE[cache_key] = tmdb_id
                print(f"[TMDB] Fallback top result for '{clean_t}' -> ID: {tmdb_id}")
                return tmdb_id
                
    except Exception as e:
        print(f"[TMDB] Error fetching ID: {e}")
        pass
        
    TMDB_CACHE[cache_key] = ""
    print(f"[TMDB] No results found for '{clean_t}'")
    return ""

def format_stream_url(raw_url, content_id, user_id_target):
    if not raw_url:
        return ""
    parsed = urlparse(raw_url)
    path = re.sub(r"/S\d+/[^/]+\.m3u8", "/index5.m3u8", parsed.path)
    path = re.sub(r"/mnf\.m3u8", "/index5.m3u8", path)
    path = re.sub(r"/index\d+\.m3u8", "/index5.m3u8", path)

    query_dict = parse_qs(parsed.query)
    query_dict["app_type"] = ["web"]
    query_dict["userid"] = [user_id_target]
    if content_id:
        query_dict["movieid"] = [str(content_id)]

    return urlunparse(parsed._replace(path=path, query=urlencode(query_dict, doseq=True)))

# --- FLS Shared Configuration ---
FLS_BASE_URL = "https://api.gizmott.com"
FLS_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "id,en-US;q=0.9,en;q=0.8",
    "access-control-allow-origin": "true",
    "channelid": "516",
    "country_code": "ID",
    "crossorigin": "true",
    "dev_id": "a390d35935634d6173bf7148665a1a0e",
    "device_type": "web",
    "ip": "223.255.224.124",
    "origin": "https://freelivesports.tv",
    "pubid": "50183",
    "referer": "https://freelivesports.tv/",
    "uid": "7938114",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"
}

def create_fls_session():
    session = requests.Session()
    session.verify = False
    retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.headers.update(FLS_HEADERS)
    return session

def fls_authenticate(session):
    url = f"{FLS_BASE_URL}/api/v1/account/authenticate"
    try:
        res = session.get(url, timeout=10)
        if res.status_code == 200:
            return res.json().get("token")
    except Exception:
        pass
    return None

def fls_get_home_data(session, token):
    url = f"{FLS_BASE_URL}/api/v2/home"
    headers = {"access-token": token, "uid": "7938114"} if token else {"uid": "7938114"}
    try:
        response = session.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {}

def is_valid_movie(item):
    movie_type = str(item.get("movie_type", "")).upper()
    title = item.get("title", "").lower()
    
    if movie_type == "SERIES" or any(kw in title for kw in ["episode", "episodes", "eps", "s0", "season"]):
        return False
        
    if "season" in item and item.get("season") is not None:
        return False
        
    return True

def is_valid_series(item):
    movie_type = str(item.get("movie_type", "")).upper()
    
    if movie_type == "MOVIE":
        return False
        
    return True

def is_fls_movie(details):
    if details.get("single_video") == 1:
        return True
    if details.get("single_video") == 0:
        return False
    if details.get("season") is not None:
        return False
    videos = details.get("videos", [])
    if isinstance(videos, list) and len(videos) <= 1 and not details.get("up_next"):
        return True
    return False

def is_fls_series(details):
    if details.get("single_video") == 1:
        return False
    if details.get("single_video") == 0:
        return True
    if details.get("season") is not None or details.get("videos") or details.get("up_next"):
        return True
    return False

def extract_fls_shows_from_data(home_data):
    fls_shows = []
    def recursive_extract(obj):
        if isinstance(obj, dict):
            if "show_id" in obj and ("vanity_url" in obj or "show_name" in obj):
                fls_shows.append(obj)
            for k, v in obj.items():
                recursive_extract(v)
        elif isinstance(obj, list):
            for item in obj:
                recursive_extract(item)

    if isinstance(home_data, dict):
        recursive_extract(home_data.get("data", home_data))
    elif isinstance(home_data, list):
        recursive_extract(home_data)

    seen = set()
    unique_shows = []
    for s in fls_shows:
        if isinstance(s, dict) and "show_id" in s:
            s_id = s["show_id"]
            if s_id not in seen:
                seen.add(s_id)
                unique_shows.append(s)
    return unique_shows
