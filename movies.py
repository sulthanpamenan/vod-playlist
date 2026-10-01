import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse, urlunparse
import requests
import streamlink
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USER_ID_TARGET = "wnctpm5uf2j"
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
    {"name": "Food & Cooking", "id": "4570", "slug": "food"},
    {"name": "Lifestyle & Travels", "id": "5764", "slug": "lifestyle-travels"},
    {"name": "Music", "id": "5756", "slug": "music"},
    {"name": "Variety Show", "id": "4712", "slug": "variety-show"},
    {"name": "Sports", "id": "4713", "slug": "sports"},
    {"name": "Motorvision TV", "id": "1766", "slug": "motorvision-tv-ondemand"},
    {"name": "My Cinema Europe", "id": "1908", "slug": "my-cinema-europe-ondemand"},
    {"name": "New Release", "id": "5551", "slug": "new-release"},
    {"name": "New Production", "id": "5544", "slug": "new-production"},
    {"name": "Exclusive", "id": "3774", "slug": "exclusive"},
    {"name": "Free Content", "id": "3772", "slug": "free-content"},
    {"name": "Others", "id": "4559", "slug": "others"},
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

def format_stream_url(raw_url, content_id):
    """Format the m3u8 URL to use the target token/userid and index5.m3u8"""
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
            meta = f'#EXTINF:-1 vod="1" type="{item.get("type", "movie")}" content-type="{item.get("type", "movie")}" tvg-logo="{item["logo"]}" group-title="{item.get("genres", "Comedy")}",{item["title"]}'
            return f"{meta}\n{url}"
    except Exception as e:
        print(f"[ERROR DM] {item['title']}: {e}")
    return None

def get_movies_by_genre(genre_info):
    """Retrieve all movies from a genre with automatic pagination and multi-key fallback"""
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
            print(f"    [!] Failed to fetch page {page} for genre {genre_slug}: {e}")
            break
    return all_movies

def main():
    print("==================================================")
    print("[PURE MOVIE GENERATOR API] Starting Ultimate Extraction...")
    print("==================================================")

    header_content = [
        "#EXTM3U",
        "", "<html>", "<head>", '<meta charset="utf-8">',
        '<meta http-equiv="X-UA-Compatible" content="IE=edge">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<script language=\"javascript\">",
        'window.location.replace("https://sulthanpamenan.github.io/vod-playlist/");',
        "</script>", "</head></html>", "",
        "<================== PLAYLIST AUTOGENERATED BY SUTAN PAMENAN ==================>",
        "<================== IF YOU FIND THIS PLAYLIST, PLEASE DO NOT SELL OR DISTRIBUTE IT FOR PERSONAL GAIN ==================>",
        ""
    ]

    with open("movies.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(header_content) + "\n\n")

    print("--- Processing Dailymotion Movies ---")
    dm_results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        for res in executor.map(process_dailymotion_item, DAILYMOTION_ITEMS):
            if res:
                dm_results.append(res)

    with open("movies.m3u", "a", encoding="utf-8") as f:
        for entry in dm_results:
            f.write(entry + "\n\n")

    print("\n--- Processing Dens.tv Movies via API (Parallel) ---")
    unique_movies = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_genre = {executor.submit(get_movies_by_genre, g): g for g in GENRES_MOVIE}
        
        for future in as_completed(future_to_genre):
            genre = future_to_genre[future]
            try:
                movies = future.result()
                print(f"[*] Fetched Genre: {genre['name']} ({len(movies)} items)")
                
                for m in movies:
                    m_id = m.get("movie_id")
                    if m_id and m_id not in unique_movies:
                        raw_stream = m.get("extra", {}).get("stream", {}).get("play_url", "")
                        if not raw_stream:
                            raw_stream = m.get("file", "")

                        formatted_stream = format_stream_url(raw_stream, m_id)
                        
                        poster = m.get("url_handle", {}).get("img_port_large", "")
                        if not poster:
                            poster = m.get("image", "")

                        if formatted_stream:
                            unique_movies[m_id] = {
                                "id": m_id,
                                "title": m.get("title", ""),
                                "poster": poster,
                                "genre": m.get("_genre_name", genre["name"]),
                                "stream": formatted_stream + HEADERS_SUFFIX
                            }
            except Exception as e:
                print(f"    [!] Error processing genre {genre['name']}: {e}")

    print(f"\n[✓] A total of {len(unique_movies)} Dens.tv movies successfully extracted!")
    print("==================================================")

    count = 0
    with open("movies.m3u", "a", encoding="utf-8") as f:
        for m_id, data in unique_movies.items():
            f.write(f'#EXTINF:-1 vod="1" type="movie" content-type="movie" tvg-id="{data["id"]}" tvg-name="{data["title"]}" tvg-logo="{data["poster"]}" group-title="{data["genre"]}",{data["title"]}\n')
            f.write(f'{data["stream"]}\n\n')
            count += 1
            print(f"[{count}/{len(unique_movies)}] [✓ SUCCESS] [{data['genre']}] {data['title']}")

    print("\n==================================================")
    print(f"[COMPLETED] movies.m3u Successfully Updated!")
    print("==================================================")

if __name__ == "__main__":
    main()
