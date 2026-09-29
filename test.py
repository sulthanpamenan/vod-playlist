import requests
import json
import time

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

def get_video_details(token, show_id, video_slug):
    url = f"{BASE_URL}/api/v2/video/details/{requests.utils.quote(str(video_slug))}?show_id={show_id}"
    headers = HEADERS.copy()
    headers["access-token"] = token
    headers["uid"] = "7938114"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("data", {})
    return {}

def generate_playlist_token(token, playlist_url):
    url = f"{BASE_URL}/api/v1/playlistV2/generateToken?id={requests.utils.quote(playlist_url, safe='')}"
    headers = HEADERS.copy()
    headers["access-token"] = token
    headers["uid"] = "7938114"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("data")
    return None

def main():
    print("1. Melakukan autentikasi...")
    access_token = authenticate()
    
    print("2. Mengambil daftar VOD dari beranda...")
    home_data = get_home_data(access_token)
    
    # Ekstraksi semua show / video secara rekursif dari JSON beranda
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
    
    # Hapus duplikat berdasarkan show_id
    unique_shows = {s["show_id"]: s for s in shows}.values()
    print(f"Ditemukan {len(unique_shows)} VOD unik di beranda.")
    
    m3u_lines = ["#EXTM3U"]
    
    for show in unique_shows:
        show_id = show.get("show_id")
        show_name = show.get("show_name") or show.get("title") or "Unknown"
        vanity_url = show.get("vanity_url") or show.get("show_name")
        logo = show.get("logo") or show.get("thumbnail") or ""
        
        print(f"Memproses: {show_name}...")
        details = get_video_details(access_token, show_id, vanity_url)
        
        resolutions = details.get("resolutions", [])
        playlist_url = next((res.get("url") for res in resolutions if res.get("type") == "auto"), None)
        if not playlist_url and resolutions:
            playlist_url = resolutions[0].get("url")
            
        if playlist_url:
            stream_token = generate_playlist_token(access_token, playlist_url)
            if stream_token:
                final_m3u8_url = f"{BASE_URL}/api/v1/playlistV2/playlist.m3u8?id={playlist_url}&token={stream_token}&type=video&pubid=50183"
                m3u_lines.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="Free Live Sports VOD",{show_name}')
                m3u_lines.append(final_m3u8_url)
        
        time.sleep(0.3) # Jeda kecil agar tidak membebani server API
        
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
        
    print("\nSelesai! File playlist.m3u berhasil diperbarui dengan seluruh daftar VOD.")

if __name__ == "__main__":
    main()
