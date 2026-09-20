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
            best = None
            for i in range(f.locator("canvas").count()):
                b = f.locator("canvas").nth(i).bounding_box()
                if b and b["width"] > 200 and b["height"] > 300:
                    area=b["width"]*b["height"]
                    if best is None or area>best[0]:
                        best=(area,b)
            if best:
                return best[1]
    except Exception:
        pass
    try:
        return page.locator("#game-iframe").bounding_box()
    except Exception:
        return None

def clickr(page, box, rx, ry):
    page.mouse.click(box["x"]+box["width"]*rx, box["y"]+box["height"]*ry)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(storage_state=AUTH, viewport={"width":1280,"height":960})
    page=context.new_page()
    page.goto(GAME_URL, wait_until="domcontentloaded", timeout=60000)
    time.sleep(25)
    box=frame_box(page)

    # 关闭首次公告/处理网络提示
    if box:
        clickr(page,box,0.03,0.50)
        time.sleep(3)
        clickr(page,box,0.72,0.59)  # 若出现“网络状况不佳”，点“继续”
        time.sleep(8)
        clickr(page,box,0.86,0.20)  # 公告右上角关闭位
        time.sleep(3)
        clickr(page,box,0.03,0.50)
        time.sleep(20)

    page.screenshot(path=str(OUT/"popup_before.png"), full_page=True)

    box=frame_box(page)
    if box:
        # 造化灵植弹窗：勾“今日不再提示”，再点“立即前往”
        clickr(page,box,0.65,0.85)
        time.sleep(1)
        clickr(page,box,0.50,0.80)
        time.sleep(8)

    page.screenshot(path=str(OUT/"activity_opened.png"), full_page=True)
    (OUT/"geometry.json").write_text(json.dumps({"box":box,"frames":[f.url for f in page.frames]}, ensure_ascii=False, indent=2), encoding="utf-8")
    browser.close()
