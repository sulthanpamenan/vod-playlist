import requests
import json
import concurrent.futures
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://api.gizmott.com"
HEADERS = {
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

def create_session():
    """Membuat session dengan mekanisme retry otomatis untuk mencegah kegagalan jaringan."""
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.headers.update(HEADERS)
    return session

def authenticate(session):
    url = f"{BASE_URL}/api/v1/account/authenticate"
    headers = {"uid": "7938114"}
    
    response = session.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("token")
    else:
        raise Exception(f"Gagal autentikasi: {response.text}")

def get_home_data(session, token):
    url = f"{BASE_URL}/api/v2/home"
    headers = {"access-token": token, "uid": "7938114"}
    
    response = session.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Gagal mengambil data beranda: {response.text}")
        return {}

def process_show(session, access_token, show):
    show_id = show.get("show_id")
    show_name = show.get("show_name") or show.get("title") or "Unknown"
    vanity_url = show.get("vanity_url") or show.get("show_name")
    logo = show.get("logo") or show.get("thumbnail") or ""

    try:
        details_url = f"{BASE_URL}/api/v2/video/details/{requests.utils.quote(str(vanity_url))}?show_id={show_id}"
        headers = {"access-token": access_token, "uid": "7938114"}
        
        res_details = session.get(details_url, headers=headers, timeout=10)
        if res_details.status_code != 200:
            return None
            
        details = res_details.json().get("data", {})
        
        # Ambil kategori asli untuk group-title
        categories = details.get("categories", [])
        primary_category = categories[0].get("category_name", "Free Live Sports VOD") if categories else "Free Live Sports VOD"
        
        # Penentuan Tipe
        show_type = "movie"
        if "season" in details or details.get("single_video") == 0:
            show_type = "series"

        resolutions = details.get("resolutions", [])
        playlist_url = next((r.get("url") for r in resolutions if r.get("type") == "auto"), None)
        if not playlist_url and resolutions:
            playlist_url = resolutions[0].get("url")
            
        if not playlist_url:
            return None

        token_url = f"{BASE_URL}/api/v1/playlistV2/generateToken?id={requests.utils.quote(playlist_url, safe='')}"
        res_token = session.get(token_url, headers=headers, timeout=10)
        if res_token.status_code != 200:
            return None
            
        stream_token = res_token.json().get("data")
        if not stream_token:
            return None
            
        final_m3u8_url = f"{BASE_URL}/api/v1/playlistV2/playlist.m3u8?id={playlist_url}&token={stream_token}&type=video&pubid=50183"
        
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
        ref = "https://freelivesports.tv/"
        stream_url_with_headers = f"{final_m3u8_url}|User-Agent={ua}&Referer={ref}"
        
        m3u_entry = (
            f'#EXTINF:-1 vod="1" type="{show_type}" content-type="{show_type}" '
            f'tvg-logo="{logo}" group-title="{primary_category}",{show_name}\n'
            f'{stream_url_with_headers}'
        )
        print(f"Berhasil diproses: {show_name} [{primary_category}]")
        return m3u_entry
        
    except Exception as e:
        print(f"Gagal memproses {show_name}: {e}")
        return None

def main():
    session = create_session()
    
    print("1. Melakukan autentikasi...")
    access_token = authenticate(session)
    
    print("2. Mengambil daftar VOD dari beranda...")
    home_data = get_home_data(session, access_token)
    
    shows = []
    def extract_shows(obj):
        if isinstance(obj, dict):
            if "show_id" in obj and ("vanity_url" in obj or "show_name" in obj):
                shows.append(obj)
            for k, v in obj.items():
                extract_shows(v)
        elif isinstance(obj, list):
            for item in obj:
                extract_shows(item)
                
    extract_shows(home_data)
    unique_shows = list({s["show_id"]: s for s in shows}.values())
    print(f"Ditemukan {len(unique_shows)} VOD unik di beranda.")
    
    m3u_lines = ["#EXTM3U"]
    
    print("3. Memproses VOD secara paralel (Multithreading dengan Session)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(process_show, session, access_token, show) for show in unique_shows]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                m3u_lines.append(result)
                
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
        
    print(f"\nSelesai! File playlist.m3u berhasil diperbarui dengan {len(m3u_lines) - 1} tautan VOD.")

if __name__ == "__main__":
    main()
