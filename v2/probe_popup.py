import time, json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT=Path("v2/popup-probe")
OUT.mkdir(parents=True,exist_ok=True)
AUTH="/tmp/xddq20/qr/storage_state.json"
GAME_URL="https://www.wanyiwan.top/game/xddq"

def game_box(page):
    try:
        f=next((f for f in page.frames if "gameIframe" in f.url),None)
        if f:
            best=None
            for i in range(f.locator("canvas").count()):
                b=f.locator("canvas").nth(i).bounding_box()
                if b and b["width"]>200 and b["height"]>300:
                    area=b["width"]*b["height"]
                    if best is None or area>best[0]:
                        best=(area,b)
            if best: return best[1]
    except Exception:
        pass
    try:
        return page.locator("#game-iframe").bounding_box()
    except Exception:
        return None

def clickr(page,b,rx,ry):
    page.mouse.click(b["x"]+b["width"]*rx,b["y"]+b["height"]*ry)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(storage_state=AUTH,viewport={"width":1280,"height":960})
    page=context.new_page()
    page.goto(GAME_URL,wait_until="domcontentloaded",timeout=60000)
    time.sleep(30)
    b=game_box(page)
    (OUT/"geometry.json").write_text(json.dumps({"box":b},ensure_ascii=False,indent=2),encoding="utf-8")
    page.screenshot(path=str(OUT/"step0.png"),full_page=True)

    if b:
        # 这张公告图里右上角 X 的实测相对位置约为 x=85.2%, y=20.2%
        clickr(page,b,0.852,0.202)
        time.sleep(4)
    page.screenshot(path=str(OUT/"step1.png"),full_page=True)

    # 若下一张也是居中弹窗，先只再尝试同一右上角区域一次。
    if b:
        clickr(page,b,0.852,0.202)
        time.sleep(4)
    page.screenshot(path=str(OUT/"step2.png"),full_page=True)

    context.storage_state(path=str(OUT/"storage_state.json"))
    browser.close()
