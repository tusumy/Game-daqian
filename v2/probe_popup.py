import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("v2/popup-probe")
OUT.mkdir(parents=True, exist_ok=True)
AUTH = "/tmp/xddq20/qr/storage_state.json"
GAME_URL = "https://www.wanyiwan.top/game/xddq"

def frame_box(page):
    try:
        f = next((f for f in page.frames if "gameIframe" in f.url), None)
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

def clickr(page,box,rx,ry):
    page.mouse.click(box["x"]+box["width"]*rx, box["y"]+box["height"]*ry)

def settle(page):
    time.sleep(25)
    box=frame_box(page)
    if box:
        clickr(page,box,0.03,0.50)  # close first overlay if present
        time.sleep(3)
        clickr(page,box,0.72,0.59)  # network prompt -> continue if present
        time.sleep(8)
        clickr(page,box,0.86,0.20)  # announcement close
        time.sleep(3)
        clickr(page,box,0.03,0.50)
        time.sleep(25)
    return frame_box(page)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(storage_state=AUTH, viewport={"width":1280,"height":960})
    page=context.new_page()
    page.goto(GAME_URL, wait_until="domcontentloaded", timeout=60000)
    box=settle(page)
    page.screenshot(path=str(OUT/"before_checkbox.png"), full_page=True)

    if box:
        # 只勾“今日不再提示”，不碰“立即前往”
        clickr(page,box,0.65,0.85)
        time.sleep(2)
    page.screenshot(path=str(OUT/"checkbox_only.png"), full_page=True)

    # 同一浏览器上下文重载，验证设置是否即时持久化。
    page.goto(GAME_URL, wait_until="domcontentloaded", timeout=60000)
    box=settle(page)
    page.screenshot(path=str(OUT/"after_reload.png"), full_page=True)

    # 保存此刻完整状态，若成功可作为后续手动任务基线。
    context.storage_state(path=str(OUT/"storage_state_after_checkbox.json"))
    browser.close()
