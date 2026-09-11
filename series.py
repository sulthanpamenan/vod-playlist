import asyncio
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
import requests
import urllib3
from playwright.async_api import async_playwright

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USER_ID_TARGET = "wnctpm5uf2j"
HEADERS_SUFFIX = "|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36&Origin=https://www.dens.tv&Referer=https://www.dens.tv/"
MAX_CONCURRENT_TASKS = 3

CATEGORIES_SERIES = [
    {"name": "Series Utama", "url": "https://www.dens.tv/movie/category/1113/series"},
    {"name": "Free Streaming", "url": "https://www.dens.tv/movie/category/1057/free-streaming"},
    {"name": "Horror & Thriller", "url": "https://www.dens.tv/movie/category/1120/horror-and-thriller"},
    {"name": "Thriller", "url": "https://www.dens.tv/movie/category/1126/thriller"},
    {"name": "Food & Cooking", "url": "https://www.dens.tv/movie/category/1114/food-and-cooking"},
    {"name": "Lifestyle & Travels", "url": "https://www.dens.tv/movie/category/1115/lifestyle-and-travels"},
    {"name": "Music & Entertainment", "url": "https://www.dens.tv/movie/category/1116/music-and-entertainment"},
    {"name": "Variety Show", "url": "https://www.dens.tv/movie/category/1117/variety-show"},
    {"name": "Sports", "url": "https://www.dens.tv/movie/category/1118/sports-and-hobbies"},
    {"name": "Cerita Indonesia", "url": "https://www.dens.tv/movie/category/1119/cerita-indonesia"},
    {"name": "Exclusive Shows", "url": "https://www.dens.tv/movie/category/1121/exclusive-shows"},
]

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

async def process_series_item(context, item, idx, total, semaphore, file_lock):
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
            logo = item.get("logo", "")
            async with file_lock:
                with open("series.m3u", "a", encoding="utf-8") as f:
                    f.write(f'#EXTINF:-1 vod="1" type="series" content-type="series" tvg-id="{c_id}" tvg-name="{title}" tvg-logo="{logo}" group-title="{item.get("genre", "Series")}",{title}\n')
                    f.write(f"{stream_url}\n\n")
            print(f"[{idx}/{total}] [✓ SUCCESS] [{item.get('genre', 'Series')}] {title} (ID: {c_id})")
            return True
        else:
            print(f"[{idx}/{total}] [X FAILED] [{item.get('genre', 'Series')}] {title} (ID: {c_id})")
            return False

async def collect_series_from_categories(page):
    print(f"[*] Collecting series from {len(CATEGORIES_SERIES)} categories...")
    unique_items = {}
    parent_series = []

    for cat in CATEGORIES_SERIES:
        try:
            await page.goto(cat["url"], wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1000)

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
            await page.wait_for_timeout(500)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await page.wait_for_timeout(800)

            items = await page.evaluate("""() => {
                const results = [];
                const links = document.querySelectorAll('a[href*="/watch/"]');
                links.forEach(a => {
                    const href = a.href || '';
                    const match = href.match(/\\/watch\\/(\\d+)/);
                    let title = a.innerText ? a.innerText.trim() : '';
                    const img = a.querySelector('img');
                    let logo = '';
                    if (img) {
                        logo = img.getAttribute('data-original') || img.getAttribute('data-src') || img.src || '';
                    }
                    if (!title && img) title = img.alt || '';
                    if (!title && a.getAttribute('title')) title = a.getAttribute('title').trim();
                    if (match && title && !title.toLowerCase().includes('watch')) {
                        results.push({ id: match[1], title: title.replace(/\\s+/g, ' ').trim(), url: href, logo: logo });
                    }
                });
                return results;
            }""")

            for item in items:
                if item["id"] not in unique_items:
                    item["genre"] = cat["name"]
                    unique_items[item["id"]] = item
                    parent_series.append(item)

        except Exception as e:
            print(f"    [!] Failed to load category {cat['name']}: {e}")

    print(f"\n[*] Deep Crawling Sidebar DOM from {len(parent_series)} Parent Series...")
    for parent in parent_series:
        try:
            parent_url = parent.get("url") or f"https://www.dens.tv/movie/watch/{parent['id']}"
            await page.goto(parent_url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(800)

            episodes = await page.evaluate("""() => {
                const results = [];
                const links = document.querySelectorAll('.player-sidebar a[href*="/watch/"], .tab-content a[href*="/watch/"]');
                links.forEach(a => {
                    const href = a.href || '';
                    const match = href.match(/\\/watch\\/(\\d+)/);
                    let title = a.innerText ? a.innerText.trim() : '';
                    const img = a.querySelector('img');
                    let logo = '';
                    if (img) {
                        logo = img.getAttribute('data-original') || img.getAttribute('data-src') || img.src || '';
                    }
                    if (!title && img) title = img.alt || '';
                    if (!title && a.getAttribute('title')) title = a.getAttribute('title').trim();
                    if (match && title && !title.toLowerCase().includes('watch')) {
                        results.push({ id: match[1], title: title.replace(/\\s+/g, ' ').trim(), url: href, logo: logo });
                    }
                });
                return results;
            }""")

            for ep in episodes:
                if ep["id"] not in unique_items:
                    ep["genre"] = parent["genre"]
                    if not ep.get("logo"):
                        ep["logo"] = parent.get("logo", "")
                    unique_items[ep["id"]] = ep

        except Exception:
            pass

    return list(unique_items.values())

async def main():
    print("==================================================")
    print("[SERIES GENERATOR] Starting the Bulk Process...")
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

    with open("series.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(header_content) + "\n\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        page = await context.new_page()
        series_list = await collect_series_from_categories(page)
        await page.close()

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
        file_lock = asyncio.Lock()

        tasks = [
            process_series_item(context, item, idx, len(series_list), semaphore, file_lock)
            for idx, item in enumerate(series_list, 1)
        ]
        await asyncio.gather(*tasks)
        await browser.close()

    print("\n[SUCCESS] `series.m3u` successfully updated!")

if __name__ == "__main__":
    asyncio.run(main())
