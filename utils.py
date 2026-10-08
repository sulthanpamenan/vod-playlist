import json
import os
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
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

def fetch_tmdb_id(title, tmdb_api_key, media_type="movie", year=None):
    if not tmdb_api_key:
        return ""
    clean_t = clean_title(title)
    if not clean_t:
        return ""
        
    cache_key = f"{clean_t}_{year}" if year else clean_t
    if cache_key in TMDB_CACHE:
        return TMDB_CACHE[cache_key]

    url = f"https://api.themoviedb.org/3/search/{media_type}"
    try:
        if year and year.isdigit():
            params = {"api_key": tmdb_api_key, "query": f"{clean_t} y:{year}"}
            res = requests.get(url, params=params, timeout=5)
            if res.status_code == 200 and res.json().get("results"):
                tmdb_id = str(res.json().get("results")[0].get("id", ""))
                TMDB_CACHE[cache_key] = tmdb_id
                return tmdb_id

        params = {"api_key": tmdb_api_key, "query": clean_t}
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200 and res.json().get("results"):
            tmdb_id = str(res.json().get("results")[0].get("id", ""))
            TMDB_CACHE[cache_key] = tmdb_id
            return tmdb_id
    except Exception:
        pass
        
    TMDB_CACHE[cache_key] = ""
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
