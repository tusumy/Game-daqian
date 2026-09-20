import json
import time
from pathlib import Path

import cv2
import numpy as np
from playwright.sync_api import sync_playwright

OUT = Path("v2/popup-probe")
TPL = Path("v2/templates")
OUT.mkdir(parents=True, exist_ok=True)

AUTH = "/tmp/xddq20/qr/storage_state.json"
GAME_URL = "https://www.wanyiwan.top/game/xddq"

TEMPLATES = {
    "notice_x": (cv2.imread(str(TPL / "notice_x.png")), 0.82),
    "event_x": (cv2.imread(str(TPL / "event_x.png")), 0.82),
    "continue": (cv2.imread(str(TPL / "continue.png")), 0.88),
    "dongfu": (cv2.imread(str(TPL / "dongfu.png")), 0.90),
}


def snap(page):
    raw = page.screenshot()
    return cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)


def match(img, templ):
    if img is None or templ is None:
        return 0.0, None
    result = cv2.matchTemplate(img, templ, cv2.TM_CCOEFF_NORMED)
    _, score, _, loc = cv2.minMaxLoc(result)
    h, w = templ.shape[:2]
    return float(score), (loc[0] + w // 2, loc[1] + h // 2)


def click_match(page, img, name):
    templ, threshold = TEMPLATES[name]
    score, point = match(img, templ)
    if point and score >= threshold:
        print(f"[MATCH] {name} score={score:.3f} at={point}", flush=True)
        page.mouse.click(*point)
        return True, score, point
    return False, score, point


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        storage_state=AUTH,
        viewport={"width": 1280, "height": 960},
    )
    page = context.new_page()
    page.goto(GAME_URL, wait_until="domcontentloaded", timeout=60000)

    started = time.time()
    next_debug = 0
    opened = False
    events = []
    dongfu_clicked_at = None
    dongfu_clicks = 0

    while time.time() - started < 240:
        img = snap(page)
        elapsed = int(time.time() - started)

        if elapsed >= next_debug:
            page.screenshot(path=str(OUT / f"state_{elapsed:03d}s.png"), full_page=True)
            next_debug += 20

        acted = False
        for name, pause in (
            ("notice_x", 4),
            ("event_x", 4),
            ("continue", 8),
        ):
            ok, score, point = click_match(page, img, name)
            if ok:
                events.append({"t": elapsed, "action": name, "score": score, "point": point})
                time.sleep(pause)
                acted = True
                break
        if acted:
            continue

        ok, score, point = click_match(page, img, "dongfu")
        if ok:
            # 活动弹窗可能恰好在这一帧之后出现，所以点完不立即判成功。
            # 若后续仍看到洞府，说明点击被弹窗截走，再点一次即可。
            if dongfu_clicked_at is None or time.time() - dongfu_clicked_at >= 5:
                events.append({"t": elapsed, "action": "dongfu", "score": score, "point": point})
                dongfu_clicks += 1
                page.mouse.click(*point)
                dongfu_clicked_at = time.time()
                time.sleep(4)
            else:
                time.sleep(1)
            continue

        # 已经点过洞府，并且此刻没有任何已知弹窗、网络提示，也看不到主界面洞府按钮，
        # 连续等几秒后才认定页面真的切进去了。
        if dongfu_clicked_at is not None and time.time() - dongfu_clicked_at >= 5:
            time.sleep(3)
            check = snap(page)
            blocked = False
            for check_name in ("notice_x", "event_x", "continue", "dongfu"):
                templ, threshold = TEMPLATES[check_name]
                s, _ = match(check, templ)
                if s >= threshold:
                    blocked = True
                    break
            if not blocked:
                page.screenshot(path=str(OUT / "dongfu_opened.png"), full_page=True)
                time.sleep(8)
                page.screenshot(path=str(OUT / "dongfu_opened_8s.png"), full_page=True)
                opened = True
                break

        time.sleep(2)

    (OUT / "events.json").write_text(
        json.dumps(events, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "result.json").write_text(
        json.dumps(
            {
                "dongfu_opened": opened,
                "dongfu_clicks": dongfu_clicks,
                "elapsed": int(time.time() - started),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    context.storage_state(path=str(OUT / "storage_state.json"))
    browser.close()

    if not opened:
        raise SystemExit("240 秒内没有稳定识别并打开洞府")
