import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse, urlunparse
import requests
import streamlink
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USER_ID_TARGET = "wnctpm5uf2j"
TMDB_API_KEY = "f5b601ec011f9760c7fb6752670714cf"
HEADERS_SUFFIX = "|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36&Origin=https://www.dens.tv&Referer=https://www.dens.tv/"

DAILYMOTION_ITEMS = [
    {"title": "Mohon Doa Restu", "id": "x9qtlim", "genres": "Comedy", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/4q8Q0GQS9v2ZeMJnNiq0Its8SE7.jpg"},
    {"title": "Laura", "id": "x9f73iq", "genres": "Drama", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/zVZIcXVMFdbzTTHOThrZX7o2DO7.jpg"},
    {"title": "Tujuh Hari Untuk Keshia", "id": "x9d736m", "genres": "Drama", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/GnCJef0y75lyvI6AVRbRCaqWSi.jpg"},
    {"title": "Lovely Man", "id": "x917hi4", "genres": "Drama", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/2DpL6GyMRJEf6bgGvyWoyQeYlzu.jpg"},
    {"title": "Father's Haunted House", "id": "x9icyxk", "genres": "Comedy", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/qwfVe3no1A2sWtvP2tjYnsEe52i.jpg"},
    {"title": "Merindu Cahaya De Amstel", "id": "x9a27nu", "genres": "Romance", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/uxD1hucihvTToMEoK9HCKkEQiq4.jpg"},
    {"title": "Pasutri Gaje", "id": "x9kg0yi", "genres": "Comedy", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/lY6Y2wNzOgSyLJrE8rzf8QmKZpG.jpg"}
]

GENRES_MOVIE = [
    {"name": "Action", "id": "8", "slug": "action"},
    {"name": "Comedy", "id": "56", "slug": "comedy"},
    {"name": "Drama", "id": "5", "slug": "drama"},
    {"name": "Romance", "id": "3481", "slug": "romance"},
    {"name": "Horror & Thriller", "id": "7", "slug": "horror-thriller"},
    {"name": "New Release", "id": "5551", "slug": "new-release"},
    {"name": "New Production", "id": "5544", "slug": "new-production"},
    {"name": "Exclusive", "id": "3774", "slug": "exclusive"},
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

def fetch_tmdb_id(title, media_type="movie"):
    """Fungsi otomatis mencari ID TMDB berdasarkan judul"""
    if not TMDB_API_KEY or TMDB_API_KEY == "MASUKKAN_TMDB_API_KEY_ANDA_DISINI":
        return ""
    try:
        clean_title = re.sub(r'\s*\(.*?\)', '', title).strip() # Bersihkan tahun dalam kurung
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
        except Exception as e:
            break
    return all_movies

def main():
    print("==================================================")
    print("[PURE MOVIE GENERATOR API] With Auto-TMDB Mapping")
    print("==================================================")

    header_content = [
        "#EXTM3U", "", "<html>", "<head>", '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<script language=\"javascript\">",
        'window.location.replace("https://sulthanpamenan.github.io/vod-playlist/");',
        "</script>", "</head></html>", "",
        "<================== PLAYLIST AUTOGENERATED BY SUTAN PAMENAN ==================>", ""
    ]

    with open("movies.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(header_content) + "\n\n")

    print("--- Processing Dailymotion Movies ---")
    dm_results = []
    for item in DAILYMOTION_ITEMS:
        res = process_dailymotion_item(item)
        if res:
            dm_results.append(res)

    with open("movies.m3u", "a", encoding="utf-8") as f:
        for entry in dm_results:
            f.write(entry + "\n\n")

    print("\n--- Processing Dens.tv Movies via API ---")
    unique_movies = {}

    for genre in GENRES_MOVIE:
        movies = get_movies_by_genre(genre)
        print(f"[*] Fetched Genre: {genre['name']} ({len(movies)} items)")
        for m in movies:
            m_id = m.get("movie_id")
            if m_id and m_id not in unique_movies:
                raw_stream = m.get("extra", {}).get("stream", {}).get("play_url", "") or m.get("file", "")
                formatted_stream = format_stream_url(raw_stream, m_id)
                poster = m.get("url_handle", {}).get("img_port_large", "") or m.get("image", "")
                title = m.get("title", "")

                if formatted_stream:
                    # Ambil ID TMDB secara otomatis
                    tmdb_id = fetch_tmdb_id(title, "movie")
                    unique_movies[m_id] = {
                        "title": title,
                        "tmdb_id": tmdb_id,
                        "poster": poster,
                        "genre": genre["name"],
                        "stream": formatted_stream + HEADERS_SUFFIX
                    }

    count = 0
    with open("movies.m3u", "a", encoding="utf-8") as f:
        for m_id, data in unique_movies.items():
            f.write(f'#EXTINF:-1 vod="1" type="movie" content-type="movie" tvg-tmdb="{data["tmdb_id"]}" tvg-logo="{data["poster"]}" group-title="{data["genre"]}",{data["title"]}\n')
            f.write(f'{data["stream"]}\n\n')
            count += 1
            print(f"[{count}] [✓] [{data['genre']}] {data['title']} (TMDB: {data['tmdb_id'] or 'Not Found'})")

    print("\n[COMPLETED] movies.m3u Successfully Updated!")

if __name__ == "__main__":
    main()
