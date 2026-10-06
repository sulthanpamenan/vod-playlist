import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse
import requests
import streamlink
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USER_ID_TARGET = "wnctpm5uf2j"
TMDB_API_KEY = "f5b601ec011f9760c7fb6752670714cf"
HEADERS_SUFFIX = "|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36&Origin=https://www.dens.tv&Referer=https://www.dens.tv/"

DAILYMOTION_ITEMS = [
    {"title": "Mohon Doa Restu (2023)", "id": "x9qtlim", "genres": "Comedy", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/4q8Q0GQS9v2ZeMJnNiq0Its8SE7.jpg"},
    {"title": "Laura (2024)", "id": "x9f73iq", "genres": "Drama", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/zVZIcXVMFdbzTTHOThrZX7o2DO7.jpg"},
    {"title": "Lovely Man (2011)", "id": "x917hi4", "genres": "Drama", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/2DpL6GyMRJEf6bgGvyWoyQeYlzu.jpg"},
    {"title": "Rumah Dinas Bapak (2024)", "id": "x9icyxk", "genres": "Comedy", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/qwfVe3no1A2sWtvP2tjYnsEe52i.jpg"},
    {"title": "Merindu Cahaya De Amstel (2022)", "id": "x9a27nu", "genres": "Romance", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/uxD1hucihvTToMEoK9HCKkEQiq4.jpg"}
]

GENRES_MOVIE = [
    {"name": "Action", "id": "8", "slug": "action"},
    {"name": "Action Adventure", "id": "2896", "slug": "action-adventure"},
    {"name": "Action Crime", "id": "3492", "slug": "action-crime"},
    {"name": "Action Thriller", "id": "3484", "slug": "action-thriller"},
    {"name": "Comedy", "id": "56", "slug": "comedy"},
    {"name": "Comedy Adventure", "id": "3486", "slug": "comedy-adventure"},
    {"name": "Comedy Crime", "id": "3487", "slug": "comedy-crime"},
    {"name": "Romantic Comedy", "id": "3482", "slug": "romantic-comedy"},
    {"name": "Drama", "id": "5", "slug": "drama"},
    {"name": "Drama Comedy", "id": "3474", "slug": "drama-comedy"},
    {"name": "Drama Mystery", "id": "2599", "slug": "drama-mystery"},
    {"name": "Drama Thriller", "id": "2600", "slug": "drama-thriller"},
    {"name": "Drama War", "id": "3490", "slug": "drama-war"},
    {"name": "Romance", "id": "3481", "slug": "romance"},
    {"name": "Horror & Thriller", "id": "7", "slug": "horror-thriller"},
    {"name": "Thriller", "id": "3477", "slug": "thriller"},
    {"name": "Cerita Indonesia", "id": "5501", "slug": "cerita-indonesia"},
    {"name": "My Cinema Europe", "id": "1908", "slug": "my-cinema-europe-ondemand"},
    {"name": "New Release", "id": "5551", "slug": "new-release"},
    {"name": "Exclusive", "id": "3774", "slug": "exclusive"},
    {"name": "Free Content", "id": "3772", "slug": "free-content"},
]

SESSION = requests.Session()
SESSION.verify = False
adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
SESSION.mount("https://", adapter)
SESSION.mount("http://", adapter)

SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "Referer": "https://www.dens.tv/",
    "Accept": "*/*"
})

SL_SESSION = streamlink.Streamlink()
SL_SESSION.set_option("http-headers", {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.dailymotion.com/"
})

def clean_movie_title(raw_title):
    cleaned = re.sub(r'\s*\|\s*(Not Rated|Rated.*$)', '', raw_title, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*\(\d{4}\)', '', cleaned)
    cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
    return ' '.join(cleaned.split())

TMDB_CACHE = {}
TMDB_CACHE_FILE = "tmdb_cache.json"

if os.path.exists(TMDB_CACHE_FILE):
    try:
        with open(TMDB_CACHE_FILE, "r", encoding="utf-8") as f:
            TMDB_CACHE = json.load(f)
    except Exception:
        TMDB_CACHE = {}
else:
    TMDB_CACHE = {}

def save_tmdb_cache():
    try:
        with open(TMDB_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(TMDB_CACHE, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

def fetch_tmdb_id(title, media_type="movie", year=None):
    if not TMDB_API_KEY:
        return ""
    clean_t = clean_movie_title(title)
    if not clean_t:
        return ""
        
    cache_key = f"{clean_t}_{year}" if year else clean_t
    
    if cache_key in TMDB_CACHE:
        return TMDB_CACHE[cache_key]

    url = f"https://api.themoviedb.org/3/search/{media_type}"

    try:
        # Layer 1: Use the filter format "y:year"
        if year and year.isdigit():
            query_with_year_filter = f"{clean_t} y:{year}"
            params = {"api_key": TMDB_API_KEY, "query": query_with_year_filter}
            res = requests.get(url, params=params, timeout=5)
            if res.status_code == 200:
                results = res.json().get("results", [])
                if results:
                    tmdb_id = str(results[0].get("id", ""))
                    TMDB_CACHE[cache_key] = tmdb_id
                    save_tmdb_cache()
                    return tmdb_id

        # Layer 2: Clean title search (backup)
        params = {"api_key": TMDB_API_KEY, "query": clean_t}
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            results = res.json().get("results", [])
            if results:
                tmdb_id = str(results[0].get("id", ""))
                TMDB_CACHE[cache_key] = tmdb_id
                save_tmdb_cache()
                return tmdb_id
    except Exception:
        pass
    
    TMDB_CACHE[cache_key] = ""
    save_tmdb_cache()
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

def process_dailymotion_item(item):
    try:
        streams = SL_SESSION.streams(f"https://www.dailymotion.com/video/{item['id']}")
        if "best" in streams:
            url = streams['best'].url
            tmdb_id = fetch_tmdb_id(item["title"], "movie")
            meta = f'#EXTINF:-1 vod="1" type="movie" content-type="movie" tvg-tmdb="{tmdb_id}" tvg-logo="{item["logo"]}" group-title="{item.get("genres", "Comedy")}",{item["title"]}'
            return f"{meta}\n{url}"
    except Exception as e:
        print(f"[ERROR DM] {item['title']}: {e}")
    return None

def get_movies_by_genre(genre_info):
    genre_id = genre_info["id"]
    genre_slug = genre_info["slug"]
    genre_name = genre_info["name"]
    
    all_movies = []
    page = 1
    while True:
        url = f"https://www.dens.tv/movie/related/{genre_id}/{genre_slug}?page={page}&limit=50&json=true"
        try:
            res = SESSION.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json().get("data", {})
                movies = data.get("movies", []) or data.get("series", [])
                if not movies:
                    break
                for m in movies:
                    m["_genre_name"] = genre_name
                all_movies.extend(movies)
                page += 1
            else:
                break
        except Exception:
            break
    return all_movies

def main():
    print("==================================================")
    print("[PURE MOVIE GENERATOR API] Starting Ultimate Extraction...")
    print("==================================================")

    header_content = [
        "<!--more-->", "<html>", "<head>", '<meta charset="utf-8">',
        '<meta http-equiv="X-UA-Compatible" content="IE=edge">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<script language=\"javascript\">",
        'window.location.replace("https://sulthanpamenan.github.io/vod-playlist/");',
        "</script>", "</head></html>", "",
        "<================== PLAYLIST AUTOGENERATED BY SUTAN PAMENAN ==================>",
        "<================== IF YOU FIND THIS PLAYLIST, PLEASE DO NOT SELL OR DISTRIBUTE IT FOR PERSONAL GAIN ==================>",
        "", "#EXTM3U"
    ]

    with open("movies.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(header_content) + "\n\n")

    print("--- Processing Dailymotion Movies ---")
    dm_results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        for res in executor.map(process_dailymotion_item, DAILYMOTION_ITEMS):
            if res:
                dm_results.append(res)

    with open("movies.m3u", "a", encoding="utf-8") as f:
        for entry in dm_results:
            f.write(entry + "\n\n")

    print("\n--- Processing Dens.tv Movies ---")
    raw_movies_list = []

    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_genre = {executor.submit(get_movies_by_genre, g): g for g in GENRES_MOVIE}
        
        for future in as_completed(future_to_genre):
            genre = future_to_genre[future]
            try:
                movies = future.result()
                print(f"[*] Fetched Genre: {genre['name']} ({len(movies)} items)")
                for m in movies:
                    raw_movies_list.append((m, genre["name"]))
            except Exception as e:
                print(f"    [!] Error processing genre {genre['name']}: {e}")

    unique_movies = {}

    def process_single_movie(item_tuple):
        m, default_genre = item_tuple
        m_id = m.get("movie_id")
        title = m.get("title", "")
        movie_type = m.get("movie_type", "").upper()
        year = str(m.get("year", ""))
        description = m.get("description", "").replace("\n", " ").strip()
        cast = m.get("cast", "").strip()
        director = m.get("director", "").strip()
        
        keywords = m.get("keywords", [])
        primary_genre = default_genre
        for kw in keywords:
            if kw.get("keyword_type", "").upper() == "GEN":
                primary_genre = kw.get("keyword_name", "").strip()
                break

        if movie_type == "SERIES" or any(kw in title.lower() for kw in ["episode", "episodes", "eps"]):
            return None

        if m_id and m_id not in unique_movies:
            raw_stream = m.get("extra", {}).get("stream", {}).get("play_url", "") or m.get("file", "")
            formatted_stream = format_stream_url(raw_stream, m_id)
            
            poster = (m.get("url_handle", {}).get("img_port_large", "") or 
                      m.get("url_handle", {}).get("img_land_large", "") or 
                      m.get("image", ""))
            if poster:
                poster = quote(poster, safe=":/%")

            if formatted_stream:
                tmdb_id = fetch_tmdb_id(title, "movie", year)
                
                return {
                    "id": m_id,
                    "title": title,
                    "tmdb_id": tmdb_id,
                    "poster": poster,
                    "genre": primary_genre,
                    "description": description,
                    "cast": cast,
                    "director": director,
                    "year": year,
                    "stream": formatted_stream + HEADERS_SUFFIX
                }
        return None

    print("\n[*] Processing metadata and TMDB mapping...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_single_movie, item) for item in raw_movies_list]
        for future in as_completed(futures):
            try:
                res = future.result()
                if res and res["id"] not in unique_movies:
                    unique_movies[res["id"]] = res
            except Exception as e:
                print(f"    [!] Error in metadata thread: {e}")

    print(f"\n[✓] A total of {len(unique_movies)} Dens.tv movies successfully extracted!")
    print("==================================================")

    count = 0
    with open("movies.m3u", "a", encoding="utf-8") as f:
        for m_id, data in unique_movies.items():
            desc_attr = f' tvg-description="{data["description"]}"' if data["description"] else ''
            director_attr = f' director="{data["director"]}"' if data["director"] and data["director"] != "-" else ''
            cast_attr = f' cast="{data["cast"]}"' if data["cast"] and data["cast"] != "-" else ''
            
            f.write(f'#EXTINF:-1 vod="1" type="movie" content-type="movie" tvg-tmdb="{data["tmdb_id"]}"{desc_attr}{director_attr}{cast_attr} tvg-logo="{data["poster"]}" group-title="{data["genre"]}",{data["title"]}\n')
            f.write(f'{data["stream"]}\n\n')
            count += 1
            print(f"[{count}/{len(unique_movies)}] [✓ SUCCESS] [{data['genre']}] {data['title']}")

    print("\n==================================================")
    print(f"[COMPLETED] movies.m3u Successfully Updated!")
    print("==================================================")

if __name__ == "__main__":
    main()
