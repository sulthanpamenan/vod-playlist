import streamlink

vod_items = [
    {"title": "Mohon Doa Restu (2023)", "id": "x9qtlim", "logo": "https://upload.wikimedia.org/wikipedia/id/thumb/c/c6/Poster_MDR.jpg/220px-Poster_MDR.jpg"},
    {"title": "Laura (2024)", "id": "x9f73iq", "logo": "https://media.themoviedb.org/t/p/w500/zVZIcXVMFdbzTTHOThrZX7o2DO7.jpg"},
    {"title": "7 Hari Untuk Keshia (2025)", "id": "x9d736m", "logo": "https://posters.cdn.klikfilm.net/380_543/7_hari_untuk_keshia_600_857.jpg"},
    {"title": "Lovely Man (2011)", "id": "x917hi4", "logo": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRUBXR9-yD1E0adBmO8IOz4LApUYVhPMTmPjw&s"},
    {"title": "Rumah Dinas Bapak (2024)", "id": "x9icyxk", "logo": "https://www.bantennow.com/assets/2024/07/Rumah-Dinas-Bapak-2024.webp"}
]

def main():
    m3u = ["#EXTM3U"]
    session = streamlink.Streamlink()
    session.set_option("http-headers", {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.dailymotion.com/"
    })

    for item in vod_items:
        try:
            streams = session.streams(f"https://www.dailymotion.com/video/{item['id']}")
            if "best" in streams:
                # Menggunakan URL stream .m3u8 hasil ekstraksi Python Streamlink
                url = streams['best'].url
                m3u.append(f'#EXTINF:-1 tvg-logo="{item["logo"]}" group-title="Indonesian Movies",{item["title"]}')
                m3u.append(url)
                print(f"[SUCCESS] {item['title']}")
        except Exception as e:
            print(f"[ERROR] {item['title']}: {e}")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

if __name__ == "__main__":
    main()
