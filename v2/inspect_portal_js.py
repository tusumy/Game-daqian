from pathlib import Path
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import hashlib

OUT = Path("v2/portal-js")
OUT.mkdir(parents=True, exist_ok=True)

captured = {}

def safe_name(url):
    name = Path(urlparse(url).path).name or hashlib.sha1(url.encode()).hexdigest() + ".js"
    return name

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 960})

    def on_response(resp):
        try:
            url = resp.url
            ctype = (resp.headers.get("content-type") or "").lower()
            if "180020010001270314" in url and ("javascript" in ctype or url.endswith(".js")):
                body = resp.body()
                captured[url] = body
        except Exception:
            pass

    page.on("response", on_response)
    page.goto("https://www.wanyiwan.top/home", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(8000)

    # 触发首页更多异步 chunks
    try:
        for _ in range(3):
            page.locator(".swiper-button-next").first.click(force=True)
            page.wait_for_timeout(1200)
    except Exception:
        pass

    # 打开登录页，再捕获登录相关 chunks
    try:
        btn = page.locator('img[alt="立即登录"]')
        for i in range(btn.count()):
            if btn.nth(i).is_visible():
                btn.nth(i).click(force=True)
                break
        page.wait_for_timeout(6000)
    except Exception:
        pass

    (OUT / "script_urls.txt").write_text("\n".join(sorted(captured)), encoding="utf-8")
    for url, body in captured.items():
        (OUT / safe_name(url)).write_bytes(body)

    page.screenshot(path=str(OUT / "page.png"), full_page=True)
    browser.close()
