import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("v2/popup-probe")
OUT.mkdir(parents=True, exist_ok=True)
AUTH = "/tmp/xddq20/qr/storage_state.json"
GAME_URL = "https://www.wanyiwan.top/game/xddq"

def game_box(page):
    try:
        f = next((f for f in page.frames if "gameIframe" in f.url), None)
        if f:
            best = None
            for i in range(f.locator("canvas").count()):
                b = f.locator("canvas").nth(i).bounding_box()
                if b and b["width"] > 200 and b["height"] > 300:
                    area = b["width"] * b["height"]
                    if best is None or area > best[0]:
                        best = (area, b)
            if best:
                return best[1]
    except Exception:
        pass
    try:
        return page.locator("#game-iframe").bounding_box()
    except Exception:
        return None

def clickr(page, box, rx, ry):
    page.mouse.click(box["x"] + box["width"] * rx, box["y"] + box["height"] * ry)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(storage_state=AUTH, viewport={"width":1280,"height":960})
    page = context.new_page()
    page.goto(GAME_URL, wait_until="domcontentloaded", timeout=60000)

    time.sleep(30)
    box = game_box(page)
    page.screenshot(path=str(OUT/"before_close.png"), full_page=True)

    if box:
        # 所有活动/公告弹窗统一先点右上角 X。只关闭，不进入活动。
        # 当前画面右上角关闭按钮大约位于游戏画布 84% 宽、18% 高处。
        for i in range(4):
            clickr(page, box, 0.84, 0.18)
            time.sleep(3)

            # GitHub runner 偶发“网络状况不佳”，若还在则点绿色“继续”
            # 该位置只在网络提示出现时有效；否则只是落在背景区域。
            clickr(page, box, 0.72, 0.59)
            time.sleep(3)

    page.screenshot(path=str(OUT/"after_close_all.png"), full_page=True)
    time.sleep(20)
    page.screenshot(path=str(OUT/"main_ready.png"), full_page=True)

    context.storage_state(path=str(OUT/"storage_state_after_close.json"))
    browser.close()
