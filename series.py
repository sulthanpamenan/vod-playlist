import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
import requests
import urllib3
from requests.adapters import HTTPAdapter

from utils import (
    fetch_tmdb_id, 
    format_stream_url, 
    clean_title, 
    clean_episode_title, 
    save_tmdb_cache, 
    create_fls_session, 
    fls_authenticate, 
    fls_get_home_data, 
    FLS_BASE_URL,
    is_fls_series
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    {"name": "Motorvision TV", "id": "1766", "slug": "motorvision-tv-ondemand"},
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

def process_fls_show(session, access_token, show):
    show_id = show.get("show_id")
    show_name = show.get("show_name") or show.get("title") or "Unknown"
    vanity_url = show.get("vanity_url") or show_name
    logo = show.get("logo") or show.get("thumbnail") or ""
    if logo:
        logo = quote(logo, safe=":/%")

    try:
        details_url = f"{FLS_BASE_URL}/api/v2/show/details/{requests.utils.quote(str(vanity_url))}"
        headers = {
            "access-token": access_token, 
            "uid": "7938114",
            "channelid": "516",
            "pubid": "50183",
            "device_type": "web"
        }
        
        res_details = session.get(details_url, headers=headers, timeout=10)
        if res_details.status_code != 200:
            return None
            
        details = res_details.json().get("data", {})
        if not isinstance(details, dict):
            details = {}

        if details.get("single_video") == 1:
            return None

        description = details.get("synopsis") or details.get("video_description") or details.get("description", "")
        director = details.get("director", "") or ""
        cast = details.get("show_cast", "") or ""
        
        categories = details.get("categories", [])
        genres_list = [cat.get("category_name") for cat in categories if isinstance(cat, dict) and cat.get("category_name")]
        genre = genres_list[0] if genres_list else clean_title(show_name)
        clean_show_name = clean_title(show_name)

        videos_data = details.get("videos", [])
        target_episodes = []

        if isinstance(videos_data, list):
            for item in videos_data:
                if isinstance(item, dict):
                    s_num = item.get("season_number") or item.get("season") or 1
                    ep_list = item.get("episodes") or item.get("video_list") or [item]
                    if isinstance(ep_list, list):
                        for ep in ep_list:
                            if isinstance(ep, dict):
                                ep["_parsed_season"] = s_num
                                target_episodes.append(ep)
                    else:
                        target_episodes.append(item)
                else:
                    target_episodes.append(details)
        
        if not target_episodes and isinstance(details.get("up_next"), list):
            target_episodes = details.get("up_next")

        if not target_episodes:
            target_episodes = [details]

        entries = []
        for idx, ep in enumerate(target_episodes, start=1):
            if not isinstance(ep, dict):
                continue
                
            season_num = str(ep.get("_parsed_season") or ep.get("season") or details.get("season") or 1)
            ep_vanity = ep.get("vanity_url") or details.get("vanity_url") or vanity_url
            ep_id = ep.get("video_id") or ep.get("show_id") or show_id
            if not ep_id:
                continue
                
            ep_title = ep.get("video_title") or ep.get("title") or ep.get("show_name") or f"{show_name} S{season_num}E{idx:02d}"
            clean_ep_title = clean_episode_title(ep_title, clean_show_name)
            ep_desc = ep.get("video_description") or ep.get("synopsis") or description
            
            vid_details_url = f"{FLS_BASE_URL}/api/v2/video/details/{requests.utils.quote(str(ep_vanity))}?show_id={show_id}"
            res_vid = session.get(vid_details_url, headers=headers, timeout=10)
            if res_vid.status_code != 200:
                continue
                
            vid_data = res_vid.json().get("data", {})
            if not isinstance(vid_data, dict):
                continue
                
            resolutions = vid_data.get("resolutions", [])
            playlist_url = next((r.get("url") for r in resolutions if isinstance(r, dict) and r.get("type") == "auto"), None)
            if not playlist_url and resolutions and isinstance(resolutions[0], dict):
                playlist_url = resolutions[0].get("url")
                
            if not playlist_url:
                continue

            token_url = f"{FLS_BASE_URL}/api/v1/playlistV2/generateToken?id={requests.utils.quote(str(playlist_url), safe='')}"
            res_token = session.get(token_url, headers=headers, timeout=10)
            if res_token.status_code != 200:
                continue
                
            stream_token = res_token.json().get("data")
            if not stream_token:
                continue
                
            final_m3u8_url = f"{FLS_BASE_URL}/api/v1/playlistV2/playlist.m3u8?id={playlist_url}&token={stream_token}&type=video&pubid=50183"
            
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"
            ref = "https://freelivesports.tv/"
            stream_url_with_headers = f"{final_m3u8_url}|User-Agent={ua}&Referer={ref}"
            
            ep_order = str(ep.get("video_order") or idx)
            
            entry = {
                "id": str(ep_id),
                "title": clean_ep_title,
                "serie_title": clean_show_name,
                "tmdb_id": "",
                "poster": logo,
                "genre": genre,
                "description": str(ep_desc).replace("\n", " ").strip(),
                "cast": cast,
                "director": director,
                "type": "series",
                "season": str(season_num).zfill(2),
                "episode": str(ep_order).zfill(2),
                "stream": stream_url_with_headers
            }
            entries.append(entry)
            
        return entries if entries else None
    except Exception:
        return None

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
        except Exception:
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
        except Exception:
            break
    return all_episodes

def main():
    print("==================================================")
    print("[UNIFIED VOD SCRAPER] Dens.tv & FreeLiveSports (Series)...")
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

    with open("series.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(header_content) + "\n\n")

    unique_episodes = {}
    series_cache = {}

    print("\n--- [1/2] Retrieving Series Data from Dens.tv ---")
    for cat in CATEGORIES:
        print(f"[*] Dens.tv Category Fetching: {cat['name']}...")
        series_list = get_series_by_category(cat["id"], cat["slug"])
        
        uncached_series = [s for s in series_list if s.get("movie_id") and s.get("movie_id") not in series_cache]
        
        if uncached_series:
            with ThreadPoolExecutor(max_workers=20) as executor:
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
            movie_type = str(parent.get("movie_type", "")).upper()
            
            if movie_type == "MOVIE":
                continue
            if not p_id:
                continue

            episodes = series_cache.get(p_id, [])
            if not episodes and parent.get("season") is None and movie_type != "SERIES":
                continue
            
            if not episodes:
                episodes = [parent]
                
            clean_p_title = clean_title(p_title)
            year = str(parent.get("year", ""))
            
            keywords = parent.get("keywords", [])
            primary_genre = cat["name"]
            for kw in keywords:
                if kw.get("keyword_type", "").upper() == "GEN":
                    primary_genre = kw.get("keyword_name", "").strip()
                    break

            tmdb_id = ""
            skip_tmdb_keywords = ["office hour", "sinema hits", "ngopi cantik", "kosan mbg", "petaka", "jelajah halal"]
            if len(clean_p_title) > 4 and not any(kw in clean_p_title.lower() for kw in skip_tmdb_keywords):
                tmdb_id = fetch_tmdb_id(p_title, TMDB_API_KEY, "tv", year)

            for idx, ep in enumerate(episodes, start=1):
                ep_id = ep.get("movie_id")
                if ep_id and ep_id not in unique_episodes:
                    raw_stream = ep.get("extra", {}).get("stream", {}).get("play_url", "") or ep.get("file", "")
                    formatted_stream = format_stream_url(raw_stream, ep_id, USER_ID_TARGET)
                    
                    poster = (ep.get("url_handle", {}).get("img_port_large", "") or 
                              ep.get("url_handle", {}).get("img_land_large", "") or 
                              ep.get("image", ""))
                    if poster:
                        poster = quote(poster, safe=":/%")

                    raw_ep_title = ep.get("title", p_title)
                    clean_ep_title = clean_episode_title(raw_ep_title, clean_p_title)
                    description = ep.get("description", "").replace("\n", " ").strip()
                    cast = ep.get("cast", "").strip()
                    director = ep.get("director", "").strip()
                    season_num = str(ep.get("season", 1)) if ep.get("season") else "1"
                    episode_num = str(ep.get("episode", idx)) if ep.get("episode") else str(idx)

                    if formatted_stream:
                        unique_episodes[ep_id] = {
                            "id": str(ep_id),
                            "title": clean_ep_title,
                            "serie_title": clean_p_title,
                            "tmdb_id": tmdb_id,
                            "poster": poster,
                            "genre": primary_genre,
                            "description": description,
                            "cast": cast,
                            "director": director,
                            "type": "series",
                            "season": season_num.zfill(2),
                            "episode": episode_num.zfill(2),
                            "stream": formatted_stream + HEADERS_SUFFIX
                        }

    print(f"[✓] Dens.tv series completed.")

    print("\n--- [2/2] Retrieving Series Data from FreeLiveSports ---")
    fls_session = create_fls_session()
    try:
        fls_token = fls_authenticate(fls_session)
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

        fls_unique_shows = []
        seen_show_ids = set()
        for s in fls_shows:
            if isinstance(s, dict) and "show_id" in s:
                s_id = s["show_id"]
                if s_id not in seen_show_ids:
                    seen_show_ids.add(s_id)
                    fls_unique_shows.append(s)

        fls_count = 0
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(process_fls_show, fls_session, fls_token, show) for show in fls_unique_shows]
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result and isinstance(result, list):
                        for res_item in result:
                            if isinstance(res_item, dict) and "id" in res_item:
                                item_key = f"fls_{res_item['id']}"
                                if item_key not in unique_episodes:
                                    unique_episodes[item_key] = res_item
                                    fls_count += 1
                except Exception as ex:
                    print(f"    [!] Error parsing FLS future result: {ex}")

        print(f"[✓] FreeLiveSports series complete: {fls_count} items added.")
    except Exception as e:
        print(f"[!] Failed to process FreeLiveSports series: {e}")

    save_tmdb_cache()

    print("\n==================================================")
    print(f"Writing a total of {len(unique_episodes)} items to series.m3u...")
    print("==================================================")

    count = 0
    with open("series.m3u", "a", encoding="utf-8") as f:
        for item_key, data in unique_episodes.items():
            desc_attr = f' tvg-description="{data["description"]}"' if data["description"] else ''
            director_attr = f' director="{data["director"]}"' if data["director"] and data["director"] != "-" else ''
            cast_attr = f' cast="{data["cast"]}"' if data["cast"] and data["cast"] != "-" else ''

            if data.get("type") == "series" and data.get("episode"):
                ep_num = str(data['episode']).zfill(2)
                season_num = str(data.get('season', '1')).zfill(2)
                formatted_line_title = f"S{season_num}E{ep_num} - {data['title']}"
                
                folder_group = data["serie_title"]
                
                f.write(f'#EXTINF:-1 vod="1" type="series" content-type="series" tvg-tmdb="{data.get("tmdb_id", "")}"{desc_attr}{director_attr}{cast_attr} serie-title="{data["serie_title"]}" tvg-season="{season_num}" tvg-episode="{ep_num}" tvg-logo="{data["poster"]}" group-title="{folder_group}",{formatted_line_title}\n')
            else:
                item_type = data.get("type", "movie")
                f.write(f'#EXTINF:-1 vod="1" type="{item_type}" content-type="{item_type}" tvg-tmdb="{data.get("tmdb_id", "")}"{desc_attr}{director_attr}{cast_attr} tvg-logo="{data["poster"]}" group-title="{data["genre"]}",{data["title"]}\n')
            
            f.write(f'{data["stream"]}\n\n')
            count += 1

    print("==================================================")
    print(f"[COMPLETED] Total {count} series items successfully saved.")
    print("==================================================")

if __name__ == "__main__":
    main()
