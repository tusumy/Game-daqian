import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("v2/ui-probe")
OUT.mkdir(parents=True, exist_ok=True)
AUTH = Path("/tmp/xddq20/qr/storage_state.json")
GAME_URL = "https://www.wanyiwan.top/game/xddq"

def game_frame(page):
    for f in page.frames:
        if "gameIframe" in f.url:
            return f
    return None

def game_box(page):
    frame = game_frame(page)
    if frame:
        try:
            canvases = frame.locator("canvas")
            best = None
            for i in range(canvases.count()):
                box = canvases.nth(i).bounding_box()
                if box and box["width"] > 200 and box["height"] > 300:
                    if best is None or box["width"] * box["height"] > best["width"] * best["height"]:
                        best = box
            if best:
                return best
        except Exception:
            pass
    try:
        return page.locator("#game-iframe").bounding_box()
    except Exception:
        return None

def shot(page, name):
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(storage_state=str(AUTH), viewport={"width":1280,"height":960})
    page = context.new_page()
    page.goto(GAME_URL, wait_until="domcontentloaded", timeout=60000)
    time.sleep(20)

    box = game_box(page)
    (OUT / "geometry.json").write_text(json.dumps({
        "url": page.url,
        "frames": [f.url for f in page.frames],
        "game_box": box,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shot(page, "before")

    page.keyboard.press("Escape")
    time.sleep(3)
    shot(page, "after_escape")

    box = game_box(page)
    if box:
        # 关闭首次公告
        page.mouse.click(box["x"] + box["width"] * 0.03, box["y"] + box["height"] * 0.50)
        time.sleep(3)
    shot(page, "after_backdrop")

    # 多等一会儿，把主界面完整加载出来；每 20 秒留一张图便于判断加载进度。
    for sec in (20, 40, 60, 90, 120):
        time.sleep(20 if sec < 120 else 30)
        shot(page, f"load_{sec}s")

    box = game_box(page)
    if box:
        # 若加载完成后仍有活动弹窗，再用已验证安全的左侧遮罩点击关闭。
        page.mouse.click(box["x"] + box["width"] * 0.03, box["y"] + box["height"] * 0.50)
        time.sleep(4)
    shot(page, "after_final_backdrop")

    browser.close()
