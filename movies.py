import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
import requests
import streamlink
import urllib3
from requests.adapters import HTTPAdapter

from utils import (
    fetch_tmdb_id, 
    format_stream_url, 
    save_tmdb_cache, 
    create_fls_session, 
    fls_authenticate, 
    fls_get_home_data, 
    FLS_BASE_URL, 
    FLS_HEADERS,
    is_fls_movie
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= CONFIGURASI =================
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

DENS_MOVIE = [
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

SL_SESSION = streamlink.Streamlink()
SL_SESSION.set_option("http-headers", {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.dailymotion.com/"
})

def process_dailymotion_item(item):
    try:
        streams = SL_SESSION.streams(f"https://www.dailymotion.com/video/{item['id']}")
        if "best" in streams:
            url = streams['best'].url
            tmdb_id = fetch_tmdb_id(item["title"], TMDB_API_KEY, "movie")
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
            res = SESSION_DENSTV.get(url, timeout=10)
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

def process_fls_movie(session, access_token, show):
    show_id = show.get("show_id")
    show_name = show.get("show_name") or show.get("title") or "Unknown"
    vanity_url = show.get("vanity_url") or show_name
    logo = show.get("logo") or show.get("thumbnail") or ""
    if logo:
        logo = quote(logo, safe=":/%")

    try:
        details_url = f"{FLS_BASE_URL}/api/v2/show/details/{requests.utils.quote(str(vanity_url))}"
        headers = {"access-token": access_token, "uid": "7938114", "channelid": "516", "pubid": "50183"}
        
        res_details = session.get(details_url, headers=headers, timeout=10)
        if res_details.status_code != 200:
            return None
            
        details = res_details.json().get("data", {})
        
        if not is_fls_movie(details):
            return None

        description = details.get("synopsis") or details.get("description", "")
        year = str(details.get("year", ""))
        director = details.get("director", "") or ""
        cast = details.get("show_cast", "") or details.get("cast", "") or ""

        categories = details.get("categories", [])
        genres_list = [cat.get("category_name") for cat in categories if cat.get("category_name")]
        genre = genres_list[0] if genres_list else "Sports"

        videos_list = details.get("videos", [])
        if not videos_list:
            return None
            
        video_item = videos_list[0]
        video_vanity = video_item.get("vanity_url") or vanity_url
        
        vid_details_url = f"{FLS_BASE_URL}/api/v2/video/details/{requests.utils.quote(str(video_vanity))}?show_id={show_id}"
        res_vid = session.get(vid_details_url, headers=headers, timeout=10)
        if res_vid.status_code != 200:
            return None
            
        vid_data = res_vid.json().get("data", {})
        resolutions = vid_data.get("resolutions", [])
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
        ua = FLS_HEADERS["user-agent"]
        ref = FLS_HEADERS["referer"]
        stream_url_with_headers = f"{final_m3u8_`url`}|User-Agent={ua}&Referer={ref}"
        
        tmdb_id = fetch_tmdb_id(show_name, TMDB_API_KEY, "movie", year)
        
        return {
            "id": str(show_id),
            "title": show_name,
            "tmdb_id": tmdb_id,
            "poster": logo,
            "genre": genre,
            "description": description.replace("\n", " ").strip(),
            "cast": cast,
            "director": director,
            "year": year,
            "stream": stream_url_with_headers
        }
    except Exception:
        return None

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
        future_to_genre = {executor.submit(get_movies_by_genre, g): g for g in DENS_MOVIE}
        for future in as_completed(future_to_genre):
            genre = future_to_genre[future]
            try:
                movies = future.result()
                print(f"[*] Fetched Genre: {genre['name']} ({len(movies)} items)")
                for m in movies:
                    m["_default_genre"] = genre["name"]
                    raw_movies_list.append(m)
            except Exception as e:
                print(f"    [!] Error processing genre {genre['name']}: {e}")

    unique_movies = {}
    
    def process_single_movie(m):
        default_genre = m.get("_default_genre", "Movie")
        m_id = m.get("movie_id")
        title = m.get("title", "")
        movie_type = str(m.get("movie_type", "")).upper()
        year = str(m.get("year", ""))
        
        if movie_type == "SERIES" or any(kw in title.lower() for kw in ["episode", "episodes", "eps"]):
            return None
            
        if m.get("season") is not None:
            return None
        
        if m_id and m_id not in unique_movies:
            raw_stream = m.get("extra", {}).get("stream", {}).get("play_url", "") or m.get("file", "")
            formatted_stream = format_stream_url(raw_stream, m_id, USER_ID_TARGET)
            
            poster = (m.get("url_handle", {}).get("img_port_large", "") or 
                      m.get("url_handle", {}).get("img_land_large", "") or 
                      m.get("image", ""))
            if poster:
                poster = quote(poster, safe=":/%")
            
            if formatted_stream:
                tmdb_id = fetch_tmdb_id(title, TMDB_API_KEY, "movie", year)
                return {
                    "id": m_id,
                    "title": title,
                    "tmdb_id": tmdb_id,
                    "poster": poster,
                    "genre": default_genre,
                    "description": m.get("description", "").replace("\n", " ").strip(),
                    "cast": m.get("cast", "").strip(),
                    "director": m.get("director", "").strip(),
                    "year": year,
                    "stream": formatted_stream + HEADERS_SUFFIX
                }
            return None

    print("\n[*] Processing Dens.tv metadata and TMDB mapping...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_single_movie, item) for item in raw_movies_list]
        for future in as_completed(futures):
            try:
                res = future.result()
                if res and res["id"] not in unique_movies:
                    unique_movies[res["id"]] = res
            except Exception as e:
                print(f"    [!] Error in metadata thread: {e}")

    print("\n--- Processing FreeLiveSports Movies ---")
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

        if isinstance(fls_home_data, dict):
            extract_fls_shows(fls_home_data.get("data", fls_home_data))
        elif isinstance(fls_home_data, list):
            extract_fls_shows(fls_home_data)

        fls_unique_shows = list({s["show_id"]: s for s in fls_shows if isinstance(s, dict) and "show_id" in s}.values())
        
        fls_movie_count = 0
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_fls_movie, fls_session, fls_token, show) for show in fls_unique_shows]
            for future in as_completed(futures):
                res = future.result()
                if res:
                    item_key = f"fls_m_{res['id']}"
                    if item_key not in unique_movies:
                        unique_movies[item_key] = res
                        fls_movie_count += 1
        print(f"[✓] FreeLiveSports movies added: {fls_movie_count}")
    except Exception as e:
        print(f"[!] Failed to process FreeLiveSports movies: {e}")

    save_tmdb_cache()

    print(f"\n[✓] Total {len(unique_movies)} movies collected!")
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
