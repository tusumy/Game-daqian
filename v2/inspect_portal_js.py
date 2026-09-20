from pathlib import Path
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import re

OUT = Path("v2/portal-js")
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 960})
    page.goto("https://www.wanyiwan.top/home", wait_until="networkidle", timeout=90000)

    scripts = page.locator("script[src]")
    urls = []
    for i in range(scripts.count()):
        src = scripts.nth(i).get_attribute("src")
        if src and "180020010001270314" in src:
            urls.append(src)

    # 触发首页动态 chunks
    try:
        page.locator(".swiper-button-next").first.click(force=True)
    except Exception:
        pass
    page.wait_for_timeout(3000)

    for req in page.context.pages:
        pass

    dynamic = page.evaluate("""() => Array.from(document.scripts).map(s => s.src).filter(Boolean)""")
    for src in dynamic:
        if "180020010001270314" in src and src not in urls:
            urls.append(src)

    (OUT / "script_urls.txt").write_text("\n".join(urls), encoding="utf-8")

    for idx, url in enumerate(urls):
        try:
            body = page.evaluate("""async (u) => {
              const r = await fetch(u, {credentials:'include'});
              return await r.text();
            }""", url)
        except Exception as exc:
            body = f"/* FETCH ERROR: {exc} */"
        name = Path(urlparse(url).path).name or f"bundle_{idx}.js"
        (OUT / name).write_text(body, encoding="utf-8")

    page.screenshot(path=str(OUT / "home.png"), full_page=True)
    browser.close()
