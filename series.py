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

async def test_single_series():
    print("[TEST SERIES] Running test for 1 item...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        page = await context.new_page()

        # Buka Halaman Kategori Series Resmi
        print("[*] Navigating to Series Category page...")
        await page.goto("https://www.dens.tv/movie/category/1113/series", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(1000)

        # Ambil link nonton yang valid (bukan link genre-list)
        series = await page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a[href*="/movie/watch/"], a[href*="/watch/"]'));
            for (let a of links) {
                const href = a.href || '';
                const match = href.match(/\\/watch\\/(\\d+)/);
                let title = a.innerText ? a.innerText.trim() : (a.getAttribute('title') || '');

                if (match && title && !href.includes('/genre-list/')) {
                    return { id: match[1], title: title, url: href };
                }
            }
            return null;
        }""")

        print(f"[*] Found Series Item: {series}")

        if not series or not series["id"]:
            print("[X TEST FAILED] Serial tidak ditemukan di halaman kategori!")
            await browser.close()
            return

        poster_potret = f"https://www.dens.tv/images/poster/potrait/{series['id']}.jpg"

        captured_m3u8 = None
        def handle_request(req):
            nonlocal captured_m3u8
            if ".m3u8" in req.url and "dens.tv" in req.url:
                captured_m3u8 = req.url

        page.on("request", handle_request)
        print(f"[*] Navigating to watch page: {series['url']}")
        await page.goto(series['url'], wait_until="domcontentloaded", timeout=20000)

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
            final_stream = format_dens_stream_url(captured_m3u8, series["id"]) + HEADERS_SUFFIX
            print("\n================ RESULT TEST SERIES ================")
            print(f'#EXTINF:-1 vod="1" tvg-id="{series["id"]}" tvg-name="{series["title"]}" tvg-logo="{poster_potret}",{series["title"]}')
            print(f"{final_stream}")
            print("====================================================\n")
            print("[✓ TEST PASSED] Series & Poster Potret Berhasil!")
        else:
            print("[X TEST FAILED] Stream M3U8 Series tidak tertangkap!")

if __name__ == "__main__":
    asyncio.run(test_single_series())
