import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT=Path("v2/main-probe")
OUT.mkdir(parents=True, exist_ok=True)
AUTH="/tmp/xddqstate/storage_state_after_checkbox.json"
GAME_URL="https://www.wanyiwan.top/game/xddq"

def box(page):
    try:
        f=next((f for f in page.frames if "gameIframe" in f.url),None)
        if f:
            best=None
            for i in range(f.locator("canvas").count()):
                b=f.locator("canvas").nth(i).bounding_box()
                if b and b["width"]>200 and b["height"]>300:
                    area=b["width"]*b["height"]
                    if best is None or area>best[0]: best=(area,b)
            if best:return best[1]
    except: pass
    try:return page.locator("#game-iframe").bounding_box()
    except:return None

def clickr(page,b,rx,ry):
    page.mouse.click(b["x"]+b["width"]*rx,b["y"]+b["height"]*ry)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(storage_state=AUTH, viewport={"width":1280,"height":960})
    page=context.new_page()
    page.goto(GAME_URL,wait_until="domcontentloaded",timeout=60000)
    time.sleep(30)
    b=box(page)
    page.screenshot(path=str(OUT/"before_enter.png"),full_page=True)
    if b:
        clickr(page,b,0.50,0.81)   # “踏入仙途”
        time.sleep(35)
    page.screenshot(path=str(OUT/"main_after_enter.png"),full_page=True)

    b=box(page)
    if b:
        clickr(page,b,0.86,0.20)   # 公告右上角 X
        time.sleep(6)
    page.screenshot(path=str(OUT/"main_clean.png"),full_page=True)

    # runner 上游戏资源加载偏慢；等待后若出现“网络状况不佳”，点绿色“继续”。
    time.sleep(70)
    page.screenshot(path=str(OUT/"main_wait70.png"),full_page=True)
    b=box(page)
    if b:
        clickr(page,b,0.72,0.59)
        time.sleep(10)
        # 某些情况下继续后会再弹一次公告，尝试关闭右上角。
        clickr(page,b,0.86,0.20)
        time.sleep(5)
    page.screenshot(path=str(OUT/"main_final.png"),full_page=True)
    context.storage_state(path=str(OUT/"storage_state_main.json"))
    browser.close()
