import json
import os
import re
from urllib.parse import parse_qs, urlencode, urlparse
import requests

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
                save_tmdb_cache()
                return tmdb_id

        params = {"api_key": tmdb_api_key, "query": clean_t}
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200 and res.json().get("results"):
            tmdb_id = str(res.json().get("results")[0].get("id", ""))
            TMDB_CACHE[cache_key] = tmdb_id
            save_tmdb_cache()
            return tmdb_id
    except Exception:
        pass
        
    TMDB_CACHE[cache_key] = ""
    save_tmdb_cache()
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
