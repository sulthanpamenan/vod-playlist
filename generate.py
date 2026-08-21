import streamlink

vod_items = [
    {"title": "Mohon Doa Restu", "id": "x9qtlim", "logo": "https://image.tmdb.org/t/p/original/4q8Q0GQS9v2ZeMJnNiq0Its8SE7.jpg"},
    {"title": "Laura", "id": "x9f73iq", "logo": "https://image.tmdb.org/t/p/original/zVZIcXVMFdbzTTHOThrZX7o2DO7.jpg"},
    {"title": "Tujuh Hari Untuk Keshia", "id": "x9d736m", "logo": "https://image.tmdb.org/t/p/original/GnCJef0y75lyvI6AVRbRCaqWSi.jpg"},
    {"title": "Lovely Man", "id": "x917hi4", "logo": "https://image.tmdb.org/t/p/original/2DpL6GyMRJEf6bgGvyWoyQeYlzu.jpg"},
    {"title": "Father's Haunted House", "id": "x9icyxk", "logo": "https://image.tmdb.org/t/p/original/qwfVe3no1A2sWtvP2tjYnsEe52i.jpg"},
    {"title": "Merindu Cahaya De Amstel", "id": "x9a27nu", "logo": "https://image.tmdb.org/t/p/original/uxD1hucihvTToMEoK9HCKkEQiq4.jpg"},
    {"title": "Pasutri Gaje", "id": "x9kg0yi", "logo": "https://image.tmdb.org/t/p/original/lY6Y2wNzOgSyLJrE8rzf8QmKZpG.jpg"}
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
                url = streams['best'].url
                m3u.append(f'#EXTINF:-1 content-type="movie" tvg-logo="{item["logo"]}" group-title="Movies (VOD)",{item["title"]}')
                m3u.append(url)
                print(f"[SUCCESS] {item['title']}")
        except Exception as e:
            print(f"[ERROR] {item['title']}: {e}")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

if __name__ == "__main__":
    main()
