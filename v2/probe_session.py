import json,time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT=Path("v2/session-probe")
OUT.mkdir(parents=True,exist_ok=True)
AUTH="/tmp/xddq20/qr/storage_state.json"
HOME="https://www.wanyiwan.top/home"

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(storage_state=AUTH,viewport={"width":1280,"height":960})
    page=context.new_page()
    page.goto(HOME,wait_until="domcontentloaded",timeout=60000)
    time.sleep(12)
    data={
        "url":page.url,
        "title":page.title(),
        "needs_login":False,
        "active_title":None,
    }
    try:
        data["needs_login"]=page.locator('img[alt="立即登录"]').filter(visible=True).count()>0
    except Exception:
        try:
            data["needs_login"]=page.get_by_text("登录后查看VIP等级",exact=False).count()>0
        except Exception:
            pass
    try:
        data["active_title"]=page.locator(".swiper-slide-active .swiper-game-title").first.inner_text(timeout=3000)
    except Exception:
        pass
    page.screenshot(path=str(OUT/"home.png"),full_page=True)
    (OUT/"status.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    browser.close()
