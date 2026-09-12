import asyncio
import re
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse, urlunparse
import requests
import urllib3
from playwright.async_api import async_playwright

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USER_ID_TARGET = "wnctpm5uf2j"
HEADERS_SUFFIX = "|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36&Origin=https://www.dens.tv&Referer=https://www.dens.tv/"

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

        print("[*] Navigating to Series page...")
        await page.goto("https://www.dens.tv/movie/genre/5501/cerita-indonesia", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(1500)

        series = await page.evaluate("""() => {
            const allLinks = Array.from(document.querySelectorAll('a'));
            for (let a of allLinks) {
                const href = a.href || '';
                const match = href.match(/\\/(?:watch|detail|play)\\/(\\d+)/);
                let title = a.innerText ? a.innerText.trim() : (a.getAttribute('title') || '');
                const isNav = /category|genre|list|home|see all/i.test(title);
                if (match && title && !isNav && title.length > 2) {
                    return { id: match[1], title: title, url: href };
                }
            }
            return null;
        }""")

        print(f"[*] Found Series Item: {series}")
        if not series or not series["id"]:
            print("[X TEST FAILED] Serial tidak ditemukan!")
            await browser.close()
            return

        # Ambil Poster Potret Presisi via API md5.json
        portrait_poster = get_portrait_poster_from_search(series["title"])

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
            print(f'#EXTINF:-1 vod="1" tvg-id="{series["id"]}" tvg-name="{series["title"]}" tvg-logo="{portrait_poster}",{series["title"]}')
            print(f"{final_stream}")
            print("====================================================\n")
            print("[✓ TEST PASSED] Series & Poster Potret Berhasil!")
        else:
            print("[X TEST FAILED] Stream M3U8 Series tidak tertangkap!")

if __name__ == "__main__":
    asyncio.run(test_single_series())
