import asyncio
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from playwright.async_api import async_playwright

USER_ID_TARGET = "wnctpm5uf2j"
HEADERS_SUFFIX = "|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36&Origin=https://www.dens.tv&Referer=https://www.dens.tv/"

def format_dens_stream_url(intercepted_url, content_id):
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

async def test_single_movie():
    print("[TEST MOVIE] Running test for 1 item...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        page = await context.new_page()

        print("[*] Navigating to Action Genre page...")
        await page.goto("https://www.dens.tv/movie/genre/8/action", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(1000)

        movie = await page.evaluate("""() => {
            const a = document.querySelector('a[href*="/watch/"]');
            if (!a) return null;
            
            const href = a.href || '';
            const match = href.match(/\\/watch\\/(\\d+)/);
            let title = a.innerText ? a.innerText.trim() : (a.getAttribute('title') || '');
            if (!title) {
                const img = a.querySelector('img');
                if (img) title = img.alt || '';
            }

            return { id: match ? match[1] : null, title: title, url: href };
        }""")

        print(f"[*] Found Item: {movie}")

        if not movie or not movie["id"]:
            print("[X TEST FAILED] Film tidak ditemukan di DOM!")
            await browser.close()
            return

        # Bentuk URL Poster Potret Statis Resmi Dens.tv berdasarkan Movie ID
        poster_potret = f"https://www.dens.tv/images/poster/potrait/{movie['id']}.jpg"

        captured_m3u8 = None
        def handle_request(req):
            nonlocal captured_m3u8
            if ".m3u8" in req.url and "dens.tv" in req.url:
                captured_m3u8 = req.url

        page.on("request", handle_request)
        print(f"[*] Navigating to watch page: {movie['url']}")
        await page.goto(movie['url'], wait_until="domcontentloaded", timeout=20000)

        for _ in range(5):
            if captured_m3u8:
                break
            await page.wait_for_timeout(800)
            await page.evaluate("""() => {
                let playBtn = document.querySelector('.vjs-big-play-button') || document.querySelector('video');
                if (playBtn) playBtn.click();
            }""")

        await browser.close()

        if captured_m3u8:
            final_stream = format_dens_stream_url(captured_m3u8, movie["id"]) + HEADERS_SUFFIX
            print("\n================ RESULT TEST MOVIE ================")
            print(f'#EXTINF:-1 vod="1" tvg-id="{movie["id"]}" tvg-name="{movie["title"]}" tvg-logo="{poster_potret}",{movie["title"]}')
            print(f"{final_stream}")
            print("====================================================\n")
            print("[✓ TEST PASSED] Movie & Poster Potret Berhasil!")
        else:
            print("[X TEST FAILED] Stream M3U8 tidak tertangkap!")

if __name__ == "__main__":
    asyncio.run(test_single_movie())
