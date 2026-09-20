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
            events.append({"t": elapsed, "action": "dongfu", "score": score, "point": point})
            time.sleep(8)
            page.screenshot(path=str(OUT / "dongfu_opened.png"), full_page=True)
            time.sleep(8)
            page.screenshot(path=str(OUT / "dongfu_opened_16s.png"), full_page=True)
            opened = True
            break

        time.sleep(2)

    (OUT / "events.json").write_text(
        json.dumps(events, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "result.json").write_text(
        json.dumps(
            {"dongfu_opened": opened, "elapsed": int(time.time() - started)},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    context.storage_state(path=str(OUT / "storage_state.json"))
    browser.close()

    if not opened:
        raise SystemExit("240 秒内没有稳定识别并打开洞府")
