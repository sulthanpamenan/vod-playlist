import streamlink
from concurrent.futures import ThreadPoolExecutor

# =========================================================================
# DAILYMOTION MOVIES
# =========================================================================
DAILYMOTION_ITEMS = [
    {"title": "Mohon Doa Restu", "id": "x9qtlim", "genres": "Comedy", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/4q8Q0GQS9v2ZeMJnNiq0Its8SE7.jpg"},
    {"title": "Laura", "id": "x9f73iq", "genres": "Drama", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/zVZIcXVMFdbzTTHOThrZX7o2DO7.jpg"},
    {"title": "Tujuh Hari Untuk Keshia", "id": "x9d736m", "genres": "Drama", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/GnCJef0y75lyvI6AVRbRCaqWSi.jpg"},
    {"title": "Lovely Man", "id": "x917hi4", "genres": "Drama", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/2DpL6GyMRJEf6bgGvyWoyQeYlzu.jpg"},
    {"title": "Father's Haunted House", "id": "x9icyxk", "genres": "Comedy", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/qwfVe3no1A2sWtvP2tjYnsEe52i.jpg"},
    {"title": "Merindu Cahaya De Amstel", "id": "x9a27nu", "genres": "Romance", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/uxD1hucihvTToMEoK9HCKkEQiq4.jpg"},
    {"title": "Pasutri Gaje", "id": "x9kg0yi", "genres": "Comedy", "type": "movie", "logo": "https://image.tmdb.org/t/p/original/lY6Y2wNzOgSyLJrE8rzf8QmKZpG.jpg"}
]

# =========================================================================
# QAZAQSTAN VOD SERIALS & SHOWS (100+ KATALOG KATALOG KATALOG)
# =========================================================================
WORKER_PROXY = "https://qazaqstan-playlist.sulthan-pamenan.workers.dev/?url="

QAZAQSTAN_VOD_SERIES = [
    ("Aulet Qupiyasy", "aulet-qupiyasy", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Qyzdyn Zholy", "qyzdyn-zholy", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Gulder Syry", "gulder-syry", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Sezim Men Sert", "sezim-men-sert", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Qyz Tagdyry", "qyz-tagdyry", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Estai Men Qorlan", "estai-men-qorlan", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Bizdin Dariger", "bizdin_dariger", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Shahmatshy Qyz", "shahmatshy-qyz", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Ofiser Qyz", "ofiser_qyz", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Bir Shanyraq Astynda", "bir-shanyraq-astynda", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Zhabaiy Alma", "zhabaiy_alma", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Bir Uidin Balalary", "bir-uidin-balalary", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Ystyq Uya", "ystyq_uya", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Akzhauyn", "akzhauyn", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Korshinin Qizi", "korshinin-qizi", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Erte Koktem", "erte_koktem", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Sham Tubindegi Shyndyq", "sham_tubindegi_shyndyq", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Myn Uade", "myn_uade", "Drama", "https://cdn05.qazaqstan.tv/450x/2026/06/11/1781200884_6a2af7f4b1153.jpg"),
    ("Zhogalgan Esim", "zhogalgan_esim", "Drama", "https://cdn05.qazaqstan.tv/450x/2026/08/04/1785828747_6a71958b3cead.jpg"),
    ("Zhogalgan Zhyldar", "zhogalgan_zhyldar", "Drama", "https://cdn05.qazaqstan.tv/450x/2026/08/03/1785737556_6a7031547ec57.jpg"),
    ("Feriha", "feriha", "Drama", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Jana Jyl", "jana-jyl", "Drama", "https://cdn05.qazaqstan.tv/450x/2025/12/29/1766986908_6952149c21676.png"),
    ("Ruhtyn Kushi", "ruhtyn-kushi", "Drama", "https://cdn05.qazaqstan.tv/450x/2025/09/29/1759144347_68da699b6c79f.jpg"),
    ("Sen Qasymda Bolmasan", "sen-qasymda-bolmasan", "Drama", "https://cdn05.qazaqstan.tv/450x/2024/9/5/1725536362778.png"),
    ("Askeriant", "askeriant", "Drama", "https://cdn05.qazaqstan.tv/450x/2024/4/18/1713420160768.png"),
    ("On Alti Zhasar Chempion", "on-alti-zhasar-chempion", "Drama", "https://cdn05.qazaqstan.tv/450x/2024/10/17/1729147605771.png"),
    ("Jat Bauyr 2", "jat-bauyr2", "Drama", "https://cdn05.qazaqstan.tv/450x/2024/2/28/1709092918864.png"),
    ("Adil Zere", "adil-zere", "Drama", "https://cdn05.qazaqstan.tv/450x/2024/8/20/1724158806824.png"),
    ("Qorqyt", "qorqyt", "Drama", "https://cdn05.qazaqstan.tv/450x/2023/12/12/1702382531085.jpg"),
    ("Qudasha Qyz", "qudasha-qyz", "Drama", "https://cdn05.qazaqstan.tv/450x/2023/11/10/1699587690684.png"),
    ("Mirzhakyp Oyan Qazaq", "mirzhakyp-oyan-qazaq", "Drama", "https://cdn05.qazaqstan.tv/450x/2022/12/13/1670942391427.png"),
    ("Jalgan Omir", "jalgan-omir", "Drama", "https://cdn05.qazaqstan.tv/450x/2025/11/04/1762233147_69098b3b59e73.jpg"),
    ("Alkei Gulama Gumyr", "alkei-gulama-gumyr", "Drama", "https://cdn05.qazaqstan.tv/450x/2022/12/26/1672033968936.png"),
    ("Magzhan Men Zhastarga Senemin", "magzhan-men-zhastarga-senemin", "Drama", "https://cdn05.qazaqstan.tv/450x/2022/10/19/1666176009197.png"),
    ("Auyl Mugalimi", "auyl-mugalimi", "Drama", "https://cdn05.qazaqstan.tv/450x/2022/2/18/1645179336156.png"),
    ("Dina Kui Kudiret", "dina-kui-kudiret", "Drama", "https://cdn05.qazaqstan.tv/450x/2022/10/19/1666179383260.png"),
    ("Burkitshiqyz", "burkitshiqyz", "Drama", "https://cdn05.qazaqstan.tv/450x/2024/3/19/1710845543292.jpg"),
    ("Sunkar", "sunkar", "Drama", "https://cdn05.qazaqstan.tv/450x/2024/5/21/1716287217433.jpg"),
    ("Paryz", "paryz", "Drama", "https://cdn05.qazaqstan.tv/450x/2025/2/19/1739962763769.jpg"),
    ("Akhmet Ult Ustazy", "akhmet-ult-ustazy", "Drama", "https://cdn05.qazaqstan.tv/450x/2021/11/29/1638157671675.jpg"),
    ("Qanysh Qazyna", "qanysh-qazyna", "Drama", "https://cdn05.qazaqstan.tv/450x/2021/11/29/1638160617967.jpg"),
    ("Qursaudagy Qyz", "qursaudagy-qyz", "Drama", "https://cdn05.qazaqstan.tv/450x/2024/2/28/1709100838490.png"),
    ("Muqagali Bul Gasyrdan Emespin", "muqagali-bul-gasyrdan-emespin", "Drama", "https://cdn05.qazaqstan.tv/450x/2021/11/29/1638160717745.png"),
    ("Sezim Tolqyny 2", "sezim-tolqyny2", "Drama", "https://cdn05.qazaqstan.tv/450x/2023/9/29/1695963546698.jpg"),
    ("Shyragyn Sonbesin", "shyragyn-sonbesin", "Drama", "https://cdn05.qazaqstan.tv/450x/2024/8/20/1724159175901.png"),
    ("Zhel Ustindegi Vals", "zhel-ustindegi-vals", "Drama", "https://cdn05.qazaqstan.tv/450x/2024/12/11/1733899045957.png"),
    ("Baqyttyn Kilti 2", "baqyttyn-kilti-2", "Drama", "https://cdn05.qazaqstan.tv/450x/2023/9/4/1693828432584.jpg"),
    ("Zhat Bauyr", "zhat-bauyr", "Drama", "https://cdn05.qazaqstan.tv/450x/2023/2/24/1677217480001.png"),
    ("Umit Pen Urei", "umit-pen-urei", "Drama", "https://cdn05.qazaqstan.tv/450x/2023/6/13/1686651748476.png"),
    ("Bauyrlar", "bauyrlar", "Drama", "https://cdn05.qazaqstan.tv/450x/2024/1/29/1706503390338.jpg"),
    ("Qyzgaldaq Muny", "qyzgaldaq-muny", "Drama", "https://cdn05.qazaqstan.tv/450x/2023/8/23/1692794794191.jpg"),
    ("Kuieu Bala 2", "kuieu-bala-2", "Drama", "https://cdn05.qazaqstan.tv/450x/2022/11/9/1667986636276.jpg"),
    ("Sezim Tolkyny", "sezim-tolkyny", "Drama", "https://cdn05.qazaqstan.tv/450x/2023/1/19/1674124548210.jpg"),
    ("Zhantalas", "zhantalas", "Drama", "https://cdn05.qazaqstan.tv/450x/2023/4/17/1681720444723.jpg"),
    ("Bizdin Synyp", "bizdin-synyp", "Drama", "https://cdn05.qazaqstan.tv/450x/2023/5/15/1684127314409.jpg"),
    ("Qyzgaldak", "qyzgaldak", "Drama", "https://cdn05.qazaqstan.tv/450x/2023/3/1/1677649752827.png"),
    ("Nauryz Aiy Kelgende", "nauryz-aiy-kelgende", "Drama", "https://cdn05.qazaqstan.tv/450x/2023/3/20/1679286884645.png"),
    ("Domalaq Ana", "domalaq-ana", "Drama", "https://cdn05.qazaqstan.tv/450x/2021/11/29/1638158499646.jpg"),
    ("Ayala", "ayala", "Drama", "https://cdn05.qazaqstan.tv/450x/2022/9/5/1662376285333.JPG"),
    ("Zhuregimnin Zhauhary", "zhuregimnin-zhauhary", "Drama", "https://cdn05.qazaqstan.tv/450x/2022/11/2/1667367300380.png"),
    ("Umit", "umit", "Drama", "https://cdn05.qazaqstan.tv/450x/2022/1/11/1641873573848.jpg"),
    ("Intimag Auili", "intimag-auili", "Drama", "https://cdn05.qazaqstan.tv/450x/2022/4/13/1649840058333.png"),
    ("Orman Iesi", "orman-iesi", "Drama", "https://cdn05.qazaqstan.tv/450x/2022/5/3/1651578436608.jpg"),
    ("Baqyttyn Kilti", "baqyttyn-kilti", "Drama", "https://cdn05.qazaqstan.tv/450x/2022/9/12/1662979493530.jpg"),
    ("Kuyeu Bala", "kuyeu-bala", "Drama", "https://cdn05.qazaqstan.tv/450x/2021/11/11/1636632793265.jpg"),
    ("Qara Tanba", "qara-tanba", "Drama", "https://cdn05.qazaqstan.tv/450x/2021/12/6/1638732861185.jpg"),
    ("Samalmen Syrlasy", "samalmen-syrlasy", "Drama", "https://cdn05.qazaqstan.tv/450x/2021/9/13/1631514067179.jpg"),
    ("Jogalgan Kyz", "jogalgan-kyz", "Drama", "https://cdn05.qazaqstan.tv/450x/2021/8/13/1628855926107.jpg"),
    ("Shildede Jangan Shyraq", "shildede-jangan-shyraq", "Drama", "https://cdn05.qazaqstan.tv/450x/2021/6/30/1625032142180.jpg"),
    ("Zamandastar Serial", "zamandastar-serial", "Drama", "https://cdn05.qazaqstan.tv/450x/2021/5/11/1620716681128.jpg"),
    ("Mahabbat Qyzyq Mol Jyldar", "mahabbat_qyzyq_mol_jyldar", "Drama", "https://cdn05.qazaqstan.tv/450x/2021/3/9/1615264511360.jpg"),
    ("Tansholpan Serial", "tansholpan_serial", "Drama", "https://cdn05.qazaqstan.tv/450x/2021/2/25/1614235419448.jpg"),
    ("Nagyz Ake", "nagyz_ake", "Drama", "https://cdn05.qazaqstan.tv/450x/2021/2/10/1612928718906.jpg"),
    ("Inelik", "inelik", "Drama", "https://cdn05.qazaqstan.tv/450x/2021/1/13/1610533049648.jpg"),
    ("Akhmet Yasaui", "akhmet_yasaui", "Drama", "https://cdn05.qazaqstan.tv/450x/2021/4/15/1618459875001.jpg"),
    ("Songi Ayaldama", "songi_ayaldama", "Drama", "https://cdn05.qazaqstan.tv/450x/2020/12/30/1609319496270.jpg"),
    ("Menin Mektebim", "menin_mektebim", "Drama", "https://cdn05.qazaqstan.tv/450x/2020/12/20/1608458216267.jpg"),
    ("Abai", "abai", "Drama", "https://cdn05.qazaqstan.tv/450x/2020/11/30/1606719580269.jpg"),
    ("Al Farabi", "al_farabi", "Drama", "https://cdn05.qazaqstan.tv/450x/2020/11/30/1606724570807.png"),
    ("Shabdaly 18", "shabdaly_18", "Drama", "https://cdn05.qazaqstan.tv/450x/2020/11/17/1605587111670.jpg"),
    ("Ainymas Aiganym", "ainymas_aiganym", "Drama", "https://cdn05.qazaqstan.tv/450x/2020/10/14/1602663159107.jpg"),
    ("Qanatsyz Qustar 2", "qanatsyz_qustar2", "Drama", "https://cdn05.qazaqstan.tv/450x/2020/9/10/1599714328175.jpg"),
    ("Erkebai", "erkebai", "Drama", "https://cdn05.qazaqstan.tv/450x/2025/1/20/1737367330060.jpg"),
    ("Laila", "laila", "Drama", "https://cdn05.qazaqstan.tv/450x/2025/2/5/1738736961394.png"),
    ("Zhana Qonys", "zhana-qonys", "Drama", "https://cdn05.qazaqstan.tv/450x/2026/04/08/1775620736_69d5d2807e255.webp"),
    ("Zholairyq", "zholairyq", "Drama", "https://cdn05.qazaqstan.tv/450x/2020/7/29/1596042070498.png"),
    ("Egiz Gumyr", "egiz_gumyr", "Drama", "https://cdn05.qazaqstan.tv/450x/2019/10/20/1571559100169.jpg"),
    ("Qazbat", "qazbat", "Drama", "https://cdn05.qazaqstan.tv/450x/2020/3/10/1583836286906.jpg"),
    ("Askerden Hat", "askerden_hat", "Drama", "https://cdn05.qazaqstan.tv/450x/2020/6/9/1591698894232.jpg"),
    ("47 Balanyn Anasy", "47-balanyn-anasy", "Drama", "https://cdn05.qazaqstan.tv/450x/2019/9/2/1567396458326.png"),
    ("Qashqyn", "qashqyn", "Drama", "https://cdn05.qazaqstan.tv/450x/2019/9/27/1569559885768.jpg"),
    ("Eldin Balasy", "eldin_balasy", "Drama", "https://cdn05.qazaqstan.tv/450x/2019/11/4/1572863021330.jpg"),
    ("Gaukhar", "gaukhar", "Drama", "https://cdn05.qazaqstan.tv/450x/2019/11/18/1574070349269.jpg"),
    ("Gazizjurek", "gazizjurek", "Drama", "https://cdn05.qazaqstan.tv/450x/2019/12/20/1576833462904.png"),
    ("Aulet Ary", "aulet_ary", "Drama", "https://cdn05.qazaqstan.tv/450x/2020/2/4/1580789407364.png"),
    ("Ozuyim", "ozuyim", "Drama", "https://cdn05.qazaqstan.tv/450x/2020/3/13/1584079130067.jpg"),
    ("Orbulaq Shaiqasy", "orbulaq-shaiqasy", "Drama", "https://cdn05.qazaqstan.tv/450x/2019/12/18/1576649144052.png"),
    ("Kanatsyz Kustar", "kanatsyz-kustar", "Drama", "https://cdn05.qazaqstan.tv/450x/2019/9/12/1568292732054.png"),
    ("Zhangyryq", "zhangyryq", "Drama", "https://cdn05.qazaqstan.tv/450x/2020/5/25/1590400924439.jpg"),
    ("Bizben Birge", "bizben-birge", "Drama", "https://cdn05.qazaqstan.tv/450x/2019/9/2/1567396475374.png"),
    ("Prime Era", "prime-era", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Izgilik Formulasy", "izgilik-formulasy", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Kokjiekten Asqan Un", "kokjiekten_asqan_un", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Qaiyrly Kesh", "qaiyrly_kesh", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Superstar KZ", "superstarkz", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Qazir Aitaiyq", "qazir_aitaiyq", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Aqparat", "aqparat", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Barekeldi", "barekeldi", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Ashyk Alan", "ashyk-alan", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Zan Aldynda", "zan-aldynda", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Aqorda", "aqorda", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Tansholpan", "tansholpan", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Taza Qazaqstan", "taza_qazaqstan", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Apta", "apta", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Tapqyr Otbasy", "tapqyr-otbasy", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("1001 Tun", "1001-tun", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Zhuldyzdy Zhuzdesu", "zhuldyzdy_zhuzdesu", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png"),
    ("Zamandastar", "zamandastar", "Entertainment", "https://qazaqstan.tv/assets/images/logo.png")
]

SL_SESSION = streamlink.Streamlink()
SL_SESSION.set_option("http-headers", {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.dailymotion.com/"
})

# =========================================================================
# DAILYMOTION
# =========================================================================
def process_dailymotion_item(item):
    try:
        streams = SL_SESSION.streams(f"https://www.dailymotion.com/video/{item['id']}")
        if "best" in streams:
            url = streams['best'].url
            meta = f'#EXTINF:-1 vod="1" type="{item.get("type", "movie")}" content-type="{item.get("type", "movie")}" tvg-logo="{item["logo"]}" group-title="{item.get("genres", "Comedy")}",{item["title"]}'
            return meta, url
    except Exception as e:
        print(f"[ERROR DM] {item['title']}: {e}")
    return None

# =========================================================================
# MAIN GENERATOR
# =========================================================================
def generate_vod_playlist():
    print("[*] Generating VOD Playlist...")

    m3u = [
        "<!--more-->", "<html>", "<head>", '<meta charset="utf-8">',
        '<meta http-equiv="X-UA-Compatible" content="IE=edge">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<script language=\"javascript\">",
        'window.location.replace("https://sulthanpamenan.github.io/vod-playlist/");',
        "</script>", "</head></html>", "",
        "<================== PLAYLIST AUTOGENERATED BY SUTAN PAMENAN ==================>",
        "<================== IF YOU FIND THIS PLAYLIST, PLEASE DO NOT SELL OR DISTRIBUTE IT FOR PERSONAL GAIN ==================>",
        "", "#EXTM3U", ""
    ]

    # 1. Movies Dailymotion
    print("\n--- Adding Dailymotion Movies ---")
    with ThreadPoolExecutor(max_workers=4) as executor:
        for res in executor.map(process_dailymotion_item, DAILYMOTION_ITEMS):
            if res:
                m3u.append(res[0])
                m3u.append(res[1])

    # 2. Qazaqstan VOD Serials (100+ Catalog)
    print("\n--- Adding Qazaqstan VOD Catalog ---")
    for title, slug, genre, logo in QAZAQSTAN_VOD_SERIES:
        target_url = f"https://qazaqstan.tv/serials/{slug}"
        stream_url = f"{WORKER_PROXY}{target_url}"
        meta = f'#EXTINF:-1 vod="1" type="series" content-type="series" tvg-logo="{logo}" group-title="{genre}",{title}'
        m3u.append(meta)
        m3u.append(stream_url)

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print("\n[SUCCESS] `playlist.m3u` updated with 100+ Qazaqstan VOD items!")

if __name__ == "__main__":
    generate_vod_playlist()
