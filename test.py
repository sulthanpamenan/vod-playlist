import requests
import json
import concurrent.futures

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

def authenticate():
    url = f"{BASE_URL}/api/v1/account/authenticate"
    headers = HEADERS.copy()
    headers["uid"] = "7938114"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("token")
    else:
        raise Exception(f"Gagal autentikasi: {response.text}")

def get_home_data(token):
    url = f"{BASE_URL}/api/v2/home"
    headers = HEADERS.copy()
    headers["access-token"] = token
    headers["uid"] = "7938114"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Gagal mengambil data beranda: {response.text}")
        return {}

def process_show(access_token, show):
    show_id = show.get("show_id")
    show_name = show.get("show_name") or show.get("title") or "Unknown"
    vanity_url = show.get("vanity_url") or show.get("show_name")
    logo = show.get("logo") or show.get("thumbnail") or ""
    
    # Tentukan tipe berdasarkan data show jika tersedia (default: movie)
    show_type = "movie"
    if show.get("type") == "SHOW" or "series" in show_name.lower():
        show_type = "series"

    try:
        # Get video details
        details_url = f"{BASE_URL}/api/v2/video/details/{requests.utils.quote(str(vanity_url))}?show_id={show_id}"
        headers = HEADERS.copy()
        headers["access-token"] = access_token
        headers["uid"] = "7938114"
        
        res_details = requests.get(details_url, headers=headers, timeout=10)
        if res_details.status_code != 200:
            return None
            
        details = res_details.json().get("data", {})
        resolutions = details.get("resolutions", [])
        playlist_url = next((r.get("url") for r in resolutions if r.get("type") == "auto"), None)
        if not playlist_url and resolutions:
            playlist_url = resolutions[0].get("url")
            
        if not playlist_url:
            return None

        # Generate Token
        token_url = f"{BASE_URL}/api/v1/playlistV2/generateToken?id={requests.utils.quote(playlist_url, safe='')}"
        res_token = requests.get(token_url, headers=headers, timeout=10)
        if res_token.status_code != 200:
            return None
            
        stream_token = res_token.json().get("data")
        if not stream_token:
            return None
            
        final_m3u8_url = f"{BASE_URL}/api/v1/playlistV2/playlist.m3u8?id={playlist_url}&token={stream_token}&type=video&pubid=50183"
        
        # Format M3U Line sesuai permintaan
        m3u_entry = (
            f'#EXTINF:-1 vod="1" type="{show_type}" content-type="{show_type}" '
            f'tvg-logo="{logo}" group-title="Free Live Sports VOD",{show_name}\n'
            f'{final_m3u8_url}'
        )
        print(f"Berhasil diproses: {show_name}")
        return m3u_entry
        
    except Exception as e:
        print(f"Gagal memproses {show_name}: {e}")
        return None

def main():
    print("1. Melakukan autentikasi...")
    access_token = authenticate()
    
    print("2. Mengambil daftar VOD dari beranda...")
    home_data = get_home_data(access_token)
    
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
    
    print("3. Memproses VOD secara paralel (Multithreading)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(process_show, access_token, show) for show in unique_shows]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                m3u_lines.append(result)
                
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
        
    print(f"\nSelesai! File playlist.m3u berhasil diperbarui dengan {len(m3u_lines) - 1} tautan VOD.")

if __name__ == "__main__":
    main()
