import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse, urlunparse
import requests
import streamlink
import urllib3
from playwright.async_api import async_playwright

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USER_ID_TARGET = "wnctpm5uf2j"
HEADERS_SUFFIX = "|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36&Origin=https://www.dens.tv&Referer=https://www.dens.tv/"
MAX_CONCURRENT_TASKS = 3

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
    {"name": "Action", "url": "https://www.dens.tv/movie/genre/8/action"},
    {"name": "Action Adventure", "url": "https://www.dens.tv/movie/genre/2896/action-adventure"},
    {"name": "Action Crime", "url": "https://www.dens.tv/movie/genre/3492/action-crime"},
    {"name": "Action Thriller", "url": "https://www.dens.tv/movie/genre/3484/action-thriller"},
    {"name": "Comedy", "url": "https://www.dens.tv/movie/genre/56/comedy"},
    {"name": "Comedy Adventure", "url": "https://www.dens.tv/movie/genre/3486/comedy-adventure"},
    {"name": "Comedy Crime", "url": "https://www.dens.tv/movie/genre/3487/comedy-crime"},
    {"name": "Romantic Comedy", "url": "https://www.dens.tv/movie/genre/3482/romantic-comedy"},
    {"name": "Drama", "url": "https://www.dens.tv/movie/genre/5/drama"},
    {"name": "Drama Comedy", "url": "https://www.dens.tv/movie/genre/3474/drama-comedy"},
    {"name": "Drama Mystery", "url": "https://www.dens.tv/movie/genre/2599/drama-mystery"},
    {"name": "Drama Thriller", "url": "https://www.dens.tv/movie/genre/2600/drama-thriller"},
    {"name": "Drama War", "url": "https://www.dens.tv/movie/genre/3490/drama-war"},
    {"name": "Romance", "url": "https://www.dens.tv/movie/genre/3481/romance"},
    {"name": "Horror & Thriller", "url": "https://www.dens.tv/movie/genre/7/horror-thriller"},
    {"name": "Thriller", "url": "https://www.dens.tv/movie/genre/3477/thriller"},
    {"name": "Cerita Indonesia", "url": "https://www.dens.tv/movie/genre/5501/cerita-indonesia"},
    {"name": "Food & Cooking", "url": "https://www.dens.tv/movie/genre/4570/food"},
    {"name": "Lifestyle & Travels", "url": "https://www.dens.tv/movie/genre/5764/lifestyle-travels"},
    {"name": "Music", "url": "https://www.dens.tv/movie/genre/5756/music"},
    {"name": "Variety Show", "url": "https://www.dens.tv/movie/genre/4712/variety-show"},
    {"name": "Sports", "url": "https://www.dens.tv/movie/genre/4713/sports"},
    {"name": "Motorvision TV", "url": "https://www.dens.tv/movie/genre/1766/motorvision-tv-ondemand"},
    {"name": "My Cinema Europe", "url": "https://www.dens.tv/movie/genre/1908/my-cinema-europe-ondemand"},
    {"name": "New Release", "url": "https://www.dens.tv/movie/genre/5551/new-release"},
    {"name": "New Production", "url": "https://www.dens.tv/movie/genre/5544/new-production"},
    {"name": "Exclusive", "url": "https://www.dens.tv/movie/genre/3774/exclusive"},
    {"name": "Free Content", "url": "https://www.dens.tv/movie/genre/3772/free-content"},
    {"name": "Others", "url": "https://www.dens.tv/movie/genre-list/4559/others"},
]

SL_SESSION = streamlink.Streamlink()
SL_SESSION.set_option("http-headers", {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.dailymotion.com/"
})

def clean_title_for_search(raw_title):
    if not raw_title: return ""
    title = raw_title.split("|")[0].strip()
    title = re.sub(r"\s*\(\s*\d+\s*(?:episodes?|eps|part)?\s*\)", "", title, flags=re.IGNORECASE).strip()
    return re.sub(r"\s+ep\.?\s*\d+", "", title, flags=re.IGNORECASE).strip()

def fix_poster_url(url):
    if not url or any(bad in str(url).lower() for bad in ["play-circle", "favicon", "default", "blank", "no-image", "data:image", "adv_asset"]):
        return ""
    url = unquote(unquote(str(url).strip()))
    if url.startswith("//"): url = "https:" + url
    elif url.startswith("/"): url = "https://www.dens.tv" + url
    parsed = urlparse(url)
    safe_path = quote(parsed.path, safe="/@:()~+=&$,#")
    return urlunparse((parsed.scheme, parsed.netloc, safe_path, parsed.params, parsed.query, parsed.fragment))

def get_portrait_poster_from_search(title):
    search_keyword = clean_title_for_search(title)
    if not search_keyword: return ""
    url = "https://www.dens.tv/dens_api/json/2/B5/md5.json"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.dens.tv/", "X-Requested-With": "XMLHttpRequest"}
    try:
        res = requests.post(url, headers=headers, data={"data_1": search_keyword}, timeout=5, verify=False)
        if res.status_code == 200:
            movies = res.json().get("data", {}).get("movies", [])
            if movies:
                raw_poster = movies[0].get("poster_url", "")
                if raw_poster: return fix_poster_url(raw_poster)
    except Exception: pass
    return ""

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

def format_dens_stream_url(intercepted_url, content_id):
    if not intercepted_url:
        return None
    clean_url = intercepted_url.split("|")[0].strip()
    parsed = urlparse(clean_url)
    path = re.sub(r"/S\d+/[^/]+\.m3u8", "/index5.m3u8", parsed.path)
    path = re.sub(r"/mnf\.m3u8", "/index5.m3u8", path)
    path = re.sub(r"/index\d+\.m3u8", "/index5.m3u8", path)

    query_dict = parse_qs(parsed.query)
    query_dict["app_type"] = ["web"]
    query_dict["userid"] = [USER_ID_TARGET]
    if content_id:
        query_dict["movieid"] = [str(content_id)]

    return urlunparse(parsed._replace(path=path, query=urlencode(query_dict, doseq=True)))

async def process_movie_item(context, item, idx, total, semaphore, file_lock):
    async with semaphore:
        page = await context.new_page()
        c_id = item["id"]
        title = item["title"]
        direct_url = item.get("url")
        captured_m3u8 = None

        def handle_request(req):
            nonlocal captured_m3u8
            if ".m3u8" in req.url and "dens.tv" in req.url:
                if not captured_m3u8 or "index" in req.url:
                    captured_m3u8 = req.url

        page.on("request", handle_request)

        try:
            if direct_url and f"/{c_id}/" in direct_url:
                target_href = direct_url
            else:
                clean_title = title.replace("&", "and")
                clean_keyword = re.sub(r"[^\w\s]", " ", clean_title).strip()
                clean_keyword = re.sub(r"\s+", " ", clean_keyword)
                search_url = f"https://www.dens.tv/search?s={requests.utils.quote(clean_keyword)}"

                await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(500)

                target_href = await page.evaluate(f"""(targetId) => {{
                    const links = Array.from(document.querySelectorAll('a[href*="/watch/"]'));
                    const match = links.find(a => a.href.includes('/' + targetId + '/') || a.href.endsWith('/' + targetId));
                    return match ? match.href : null;
                }}""", c_id)

                if not target_href:
                    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
                    target_href = f"https://www.dens.tv/movie/watch/{c_id}/{slug}"

            await page.goto(target_href, wait_until="domcontentloaded", timeout=15000)
            
            for _ in range(5):
                if captured_m3u8:
                    break
                await page.wait_for_timeout(800)
                await page.evaluate("""() => {
                    let playBtn = document.querySelector('.vjs-big-play-button') || document.querySelector('#player') || document.querySelector('video');
                    if (playBtn) {
                        playBtn.click();
                        if (playBtn.play) playBtn.play();
                    }
                }""")

        except Exception:
            pass
        finally:
            page.remove_listener("request", handle_request)

        await page.close()

        if captured_m3u8:
            stream_url = format_dens_stream_url(captured_m3u8, c_id) + HEADERS_SUFFIX
            portrait_poster = get_portrait_poster_from_search(title) or item.get("logo", "")
            
            async with file_lock:
                with open("movies.m3u", "a", encoding="utf-8") as f:
                    f.write(f'#EXTINF:-1 vod="1" type="movie" content-type="movie" tvg-id="{c_id}" tvg-name="{title}" tvg-logo="{portrait_poster}" group-title="{item.get("genre", "Movies")}",{title}\n')
                    f.write(f"{stream_url}\n\n")
            print(f"[{idx}/{total}] [✓ SUCCESS] [{item.get('genre', 'Movie')}] {title} (ID: {c_id})")
            return True
        else:
            print(f"[{idx}/{total}] [X FAILED] [{item.get('genre', 'Movie')}] {title} (ID: {c_id})")
            return False

async def collect_movies_from_genres(page):
    print(f"[*] Collecting movies from {len(GENRES_MOVIE)} genres...")
    unique_movies = {}

    for g_idx, genre in enumerate(GENRES_MOVIE, 1):
        try:
            await page.goto(genre["url"], wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1000)

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3);")
            await page.wait_for_timeout(400)
            await page.evaluate("window.scrollTo(0, (document.body.scrollHeight / 3) * 2);")
            await page.wait_for_timeout(400)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await page.wait_for_timeout(600)

            movies = await page.evaluate("""() => {
                const results = [];
                const links = document.querySelectorAll('a[href*="/watch/"], a[href*="/movie/"]');
                links.forEach(a => {
                    const href = a.href || '';
                    const match = href.match(/\\/(\\d+)(?:\\/|$)/);
                    let title = a.innerText ? a.innerText.trim() : '';
                    if (!title && a.getAttribute('title')) title = a.getAttribute('title').trim();

                    if (match && title && !title.toLowerCase().includes('watch') && href.includes('/watch/')) {
                        const mId = match[1];
                        let logo = '';
                        const container = a.closest('.movie-box') || a.parentElement || a;
                        const imgs = Array.from(container.querySelectorAll('img'));
                        for (let img of imgs) {
                            let src = img.getAttribute('data-original') || img.getAttribute('data-src') || img.src || '';
                            if (src && !src.includes('svg') && !src.includes('play-circle')) {
                                logo = src;
                                break;
                            }
                        }

                        results.push({ id: mId, title: title.replace(/\\s+/g, ' ').trim(), url: href, logo: logo });
                    }
                });
                return results;
            }""")

            for m in movies:
                if m["id"] not in unique_movies:
                    m["genre"] = genre["name"]
                    unique_movies[m["id"]] = m

        except Exception as e:
            print(f"    [!] Failed to load genre {genre['name']}: {e}")

    return list(unique_movies.values())

async def main():
    print("==================================================")
    print("[MOVIE GENERATOR] Starting the Bulk Process...")
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

    print("\n--- Processing Dens.tv Movies ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        page = await context.new_page()
        movie_list = await collect_movies_from_genres(page)
        await page.close()

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
        file_lock = asyncio.Lock()

        tasks = [
            process_movie_item(context, item, idx, len(movie_list), semaphore, file_lock)
            for idx, item in enumerate(movie_list, 1)
        ]
        await asyncio.gather(*tasks)
        await browser.close()

    print("\n[SUCCESS] `movies.m3u` successfully updated!")

if __name__ == "__main__":
    asyncio.run(main())
