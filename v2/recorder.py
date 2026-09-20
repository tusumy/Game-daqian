import base64
import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "v2" / "capture"
OUT.mkdir(parents=True, exist_ok=True)

VIEWPORT = {"width": 800, "height": 900}
GAME_URL = os.getenv("GAME_URL", "https://www.wanyiwan.top/game/xddq")

frames = []
marker = "boot"


def set_marker(name):
    global marker
    marker = name
    print(f"[MARK] {name}")


def decode_header(payload):
    if not isinstance(payload, (bytes, bytearray)) or len(payload) < 10:
        return None
    b = bytes(payload)
    header_be = int.from_bytes(b[0:2], "big", signed=False)
    length_be = int.from_bytes(b[2:6], "big", signed=False)
    msg_be = int.from_bytes(b[6:10], "big", signed=False)
    header_le = int.from_bytes(b[0:2], "little", signed=False)
    length_le = int.from_bytes(b[2:6], "little", signed=False)
    msg_le = int.from_bytes(b[6:10], "little", signed=False)
    return {
        "header_be": header_be,
        "length_be": length_be,
        "msg_be": msg_be,
        "header_le": header_le,
        "length_le": length_le,
        "msg_le": msg_le,
    }


def record_frame(direction, payload):
    item = {
        "ts": time.time(),
        "marker": marker,
        "direction": direction,
        "kind": "text" if isinstance(payload, str) else "binary",
    }
    if isinstance(payload, str):
        item["text"] = payload[:1000]
        item["length"] = len(payload)
    else:
        raw = bytes(payload)
        item["length"] = len(raw)
        item["header"] = decode_header(raw)
        item["hex_prefix"] = raw[:32].hex()
        item["base64"] = base64.b64encode(raw).decode("ascii")
    frames.append(item)


def hook_websocket(ws):
    print(f"[WS] {ws.url}")
    ws.on("framesent", lambda payload: record_frame("sent", payload))
    ws.on("framereceived", lambda payload: record_frame("recv", payload))
    ws.on("close", lambda: print(f"[WS] closed {ws.url}"))


def screenshot_image(page):
    raw = page.screenshot()
    return cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)


def game_rect(page):
    return page.evaluate(
        """(() => {
            const c = document.querySelector('canvas');
            if (!c) return null;
            const r = c.getBoundingClientRect();
            return {left:r.left, top:r.top, width:r.width, height:r.height};
        })()"""
    )


def game_to_page(page, x, y):
    r = game_rect(page)
    if not r:
        return int(x), int(y)
    return int(round(r["left"] + x)), int(round(r["top"] + y))


def click_game(page, x, y):
    px, py = game_to_page(page, x, y)
    page.mouse.click(px, py)


def drag_game(page, x1, y1, x2, y2):
    sx, sy = game_to_page(page, x1, y1)
    ex, ey = game_to_page(page, x2, y2)
    page.mouse.move(sx, sy)
    page.mouse.down()
    page.mouse.move(ex, ey, steps=30)
    page.mouse.up()


def template_path(name):
    return str(ROOT / name)


def find_image_center(page, name, confidence=0.75):
    img = screenshot_image(page)
    template = cv2.imread(template_path(name), cv2.IMREAD_COLOR)
    if img is None or template is None:
        return None

    r = game_rect(page)
    ox = oy = 0
    search = img
    if r:
        x1 = max(0, int(round(r["left"])))
        y1 = max(0, int(round(r["top"])))
        x2 = min(img.shape[1], int(round(r["left"] + r["width"])))
        y2 = min(img.shape[0], int(round(r["top"] + r["height"])))
        if x2 > x1 and y2 > y1:
            search = img[y1:y2, x1:x2]
            ox, oy = x1, y1

    th, tw = template.shape[:2]
    if th > search.shape[0] or tw > search.shape[1]:
        return None

    result = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
    _, score, _, loc = cv2.minMaxLoc(result)
    if score < confidence:
        return None
    return ox + loc[0] + tw // 2, oy + loc[1] + th // 2


def click_image(page, name, confidence=0.75):
    p = find_image_center(page, name, confidence)
    if not p:
        return False
    page.mouse.click(*p)
    return True


def wait_click(page, name, label, timeout=15, confidence=0.72):
    set_marker(label)
    start = time.time()
    while time.time() - start < timeout:
        if click_image(page, name, confidence):
            time.sleep(2.5)
            return True
        time.sleep(1)
    print(f"[-] timeout: {label}")
    return False


def save_page_diagnostics(page, name):
    try:
        info = {
            "url": page.url,
            "title": page.title(),
            "links": page.evaluate(
                """() => Array.from(document.querySelectorAll('a')).slice(0, 300).map((a, i) => ({
                    i,
                    text: (a.innerText || a.textContent || '').trim().slice(0, 120),
                    href: a.href || '',
                    title: a.getAttribute('title') || '',
                    aria: a.getAttribute('aria-label') || ''
                }))"""
            ),
            "images": page.evaluate(
                """() => Array.from(document.images).slice(0, 300).map((img, i) => ({
                    i,
                    alt: img.alt || '',
                    title: img.title || '',
                    src: img.src || ''
                }))"""
            ),
        }
        (OUT / f"{name}.json").write_text(
            json.dumps(info, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (OUT / f"{name}.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(OUT / f"{name}.png"))
    except Exception as exc:
        print(f"[-] 保存页面诊断失败: {exc}")


def has_canvas(page):
    try:
        text = page.locator("body").inner_text(timeout=1000)
        if "支付宝扫码即玩" in text or "使用支付宝扫码即玩" in text:
            return False
    except Exception:
        pass

    try:
        canvases = page.locator("canvas")
        for i in range(canvases.count()):
            box = canvases.nth(i).bounding_box()
            if box and box["width"] >= 300 and box["height"] >= 300:
                return True
        return False
    except Exception:
        return False


def _click_and_follow_page(page, target, label):
    context = page.context
    before = list(context.pages)
    print(f"[+] 点击大厅入口: {label}")
    target.click(timeout=8000, force=True)
    time.sleep(3)

    after = list(context.pages)
    spawned = [p for p in after if p not in before]
    if spawned:
        launched = spawned[-1]
        try:
            launched.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass
        print(f"[+] 检测到新游戏页: {launched.url}")
        return launched

    print(f"[PAGE] 点击后仍在当前页 url={page.url}; frames={len(page.frames)}")
    return page


def enter_xddq_from_portal(page):
    print(f"[PAGE] url={page.url} title={page.title()!r}")
    if has_canvas(page):
        print("[+] 已检测到 canvas，当前已在游戏页")
        return page

    # 首页真正的游戏启动入口使用 gameId=xddq。
    # 排行榜里的 appId 卡片只用于排行/展示，不再把它当最终启动入口。
    launch_selectors = [
        '[data-aspm-desc="feeds-游戏卡片_N"][data-aspm-param*="gameId=xddq"]',
        '[data-aspm-desc="Banner-轮播卡片_N"][data-aspm-param*="gameId=xddq"]',
        '[data-aspm-param*="gameId=xddq"]',
    ]

    for selector in launch_selectors:
        try:
            loc = page.locator(selector)
            if loc.count() == 0:
                continue

            # feeds 卡通常是实际可点击游戏卡；banner 可能处于非当前轮播页。
            target = loc.first
            launched = _click_and_follow_page(page, target, selector)
            time.sleep(8)

            if launched is not page:
                return launched
            if has_canvas(page) or recorder_frames_present():
                return page

            # 某些版本会在首页内嵌 iframe 载入游戏，先把 frame URL 记录下来。
            frame_urls = [f.url for f in page.frames]
            print(f"[PAGE] 启动点击后的 frame urls: {frame_urls}")
            if len(page.frames) > 1:
                return page
        except Exception as exc:
            print(f"[-] 游戏启动入口 {selector} 点击失败: {exc}")

    # 兼容旧的直接链接/文本入口。
    selectors = [
        'a[href*="/game/xddq"]',
        'a[href*="xddq"]',
        'a:has-text("寻道大千")',
        '[title*="寻道大千"]',
        '[aria-label*="寻道大千"]',
    ]
    for selector in selectors:
        try:
            loc = page.locator(selector)
            if loc.count() == 0:
                continue
            launched = _click_and_follow_page(page, loc.first, selector)
            time.sleep(8)
            if launched is not page or has_canvas(page):
                return launched
        except Exception as exc:
            print(f"[-] 兼容入口 {selector} 点击失败: {exc}")

    direct_url = "https://www.wanyiwan.top/game/xddq"
    print(f"[*] 大厅启动入口均未建立游戏连接，最后尝试直达 {direct_url}")
    page.goto(direct_url, wait_until="domcontentloaded", timeout=60000)
    time.sleep(10)
    print(f"[PAGE] 直达后 url={page.url} title={page.title()!r}")
    if has_canvas(page):
        return page

    save_page_diagnostics(page, "portal_stuck")
    return None


def recorder_frames_present():
    return bool(frames)

def plant_any_available_seed(page, cell="unknown"):
    """在当前种子面板里种任意可用种子。

    优先兼容旧青石斛模板；若种子列表已更新，则以搜索框为锚点，
    从列表第一项开始尝试。只要点击后出现新的上行 WS 帧，或种子面板关闭，
    就视为已触发一次种植。
    """
    if find_image_center(page, "qingshihu_seed.png", 0.80):
        set_marker(f"seed_any_legacy:{cell}")
        if click_image(page, "qingshihu_seed.png", 0.80):
            time.sleep(1.8)
            return True

    search = find_image_center(page, "search_bar.png", 0.70)
    if not search:
        print(f"[-] {cell}: 未识别到种子列表")
        return False

    sx, sy = search
    # 新版种子多时不再搜索固定名称；从列表顶部往下尝试可见种子卡。
    candidates = [
        (sx, sy + 70),
        (sx, sy + 115),
        (sx, sy + 160),
        (sx, sy + 205),
    ]

    for idx, (x, y) in enumerate(candidates, start=1):
        sent_before = sum(1 for f in frames if f.get("direction") == "sent")
        set_marker(f"seed_any_candidate:{cell}:{idx}")
        page.mouse.click(x, y)
        time.sleep(1.5)
        sent_after = sum(1 for f in frames if f.get("direction") == "sent")

        panel_still_open = find_image_center(page, "search_bar.png", 0.70) is not None
        if sent_after > sent_before or not panel_still_open:
            print(f"[+] {cell}: 已尝试种植当前可用种子，第 {idx} 项")
            return True

    print(f"[-] {cell}: 可见种子候选均未触发种植")
    return False


def summarize():
    sent = defaultdict(Counter)
    recv = defaultdict(Counter)
    for f in frames:
        h = f.get("header")
        if not h:
            continue
        mid = h.get("msg_be")
        if f["direction"] == "sent":
            sent[f["marker"]][mid] += 1
        else:
            recv[f["marker"]][mid] += 1

    print("\n=== SENT MSG IDS BY MARKER ===")
    for name, counts in sent.items():
        print(f"{name}: {dict(counts)}")

    print("\n=== RECV MSG IDS BY MARKER ===")
    for name, counts in recv.items():
        print(f"{name}: {dict(counts)}")


def normalize_cookie_list(items):
    cookies = []
    for item in items:
        cookie = {
            "name": item["name"],
            "value": item.get("value", ""),
            "domain": item["domain"],
            "path": item.get("path", "/"),
            "httpOnly": bool(item.get("httpOnly", False)),
            "secure": bool(item.get("secure", False)),
        }

        expires = item.get("expires", item.get("expirationDate"))
        if expires is not None:
            cookie["expires"] = float(expires)

        same_site = item.get("sameSite")
        if isinstance(same_site, str):
            normalized = same_site.strip().lower()
            mapping = {
                "strict": "Strict",
                "lax": "Lax",
                "none": "None",
                "no_restriction": "None",
                "unspecified": None,
            }
            if normalized in mapping and mapping[normalized]:
                cookie["sameSite"] = mapping[normalized]

        cookies.append(cookie)

    return {"cookies": cookies, "origins": []}


def parse_auth_payload(raw, source_name):
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{source_name} 不是有效 JSON: {exc}") from exc

    if isinstance(data, list):
        print(f"[+] {source_name} 检测为浏览器 cookie 数组，自动转换")
        return normalize_cookie_list(data)

    if isinstance(data, dict) and isinstance(data.get("cookies"), list):
        print(f"[+] {source_name} 检测为 Playwright storage_state")
        return {
            "cookies": normalize_cookie_list(data["cookies"])["cookies"],
            "origins": data.get("origins", []),
        }

    raise RuntimeError(
        f"{source_name} 格式不支持：需要浏览器 cookie 数组，"
        "或包含 cookies/origins 的 Playwright storage_state。"
    )


def load_storage_state():
    auth_file = (os.getenv("GAME_AUTH_FILE") or "").strip()
    if auth_file:
        path = Path(auth_file)
        if path.exists():
            raw = path.read_text(encoding="utf-8")
            return parse_auth_payload(raw, "GAME_AUTH_FILE")

    raw = (os.getenv("GAME_COOKIES_JSON") or "").strip()
    if raw:
        return parse_auth_payload(raw, "GAME_COOKIES_JSON")

    raw = (os.getenv("GAME_AUTH_JSON") or "").strip()
    if raw:
        return parse_auth_payload(raw, "GAME_AUTH_JSON")

    path = ROOT / "auth.json"
    if path.exists():
        try:
            raw = path.read_text(encoding="utf-8")
            return parse_auth_payload(raw, "仓库 auth.json")
        except RuntimeError as exc:
            raise RuntimeError(
                "仓库 auth.json 不可用。不要把登录 cookie 提交进 git；"
                "请改用 GitHub Secret: GAME_COOKIES_JSON。"
            ) from exc

    raise RuntimeError(
        "没有可用登录态。推荐把浏览器导出的 cookie 数组"
        "放进 GitHub Secret: GAME_COOKIES_JSON。"
    )


def run():
    storage_state = load_storage_state()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        kwargs = {
            "viewport": VIEWPORT,
            "device_scale_factor": 1,
            "storage_state": storage_state,
        }
        context = browser.new_context(**kwargs)

        def bind_ws(p):
            try:
                p.on("websocket", hook_websocket)
            except Exception:
                pass

        context.on("page", bind_ws)
        page = context.new_page()
        bind_ws(page)

        try:
            set_marker("open_game")
            page.goto(GAME_URL or "https://www.wanyiwan.top/game/xddq", wait_until="domcontentloaded", timeout=60000)
            time.sleep(8)

            launched_page = enter_xddq_from_portal(page)
            if not launched_page:
                raise RuntimeError("已登录万一玩，但仍无法进入寻道大千；已保存 portal_stuck 诊断文件")
            page = launched_page

            time.sleep(4)
            save_page_diagnostics(page, "game_entry")

            drag_game(page, 750, 300, 150, 300)
            time.sleep(2)
            click_game(page, 100, 750)
            time.sleep(1)
            set_marker("close_notice")
            click_image(page, "close_notice.png", 0.70)
            time.sleep(2)

            enter_clicked = wait_click(page, "enter_game_btn.png", "enter_game", 12)
            if not enter_clicked:
                print("[*] 未识别到旧版进入游戏按钮，尝试按当前 canvas 状态继续")
                save_page_diagnostics(page, "after_enter_timeout")

            if not wait_click(page, "dongfu_btn.png", "open_dongfu", 15):
                save_page_diagnostics(page, "dongfu_timeout")
                raise RuntimeError("未找到洞府入口；已保存 dongfu_timeout 诊断文件")

            if not wait_click(page, "danjie_btn.png", "open_danjie", 15):
                save_page_diagnostics(page, "danjie_timeout")
                raise RuntimeError("未找到丹界药田入口；已保存 danjie_timeout 诊断文件")

            time.sleep(4)

            blocks = [
                ("block_1.png", "left_bottom", (155, 530)),
                ("block_2.png", "left_top", (205, 490)),
                ("block_3.png", "right_top", (260, 480)),
                ("block_4.png", "right_bottom", (265, 520)),
            ]
            dx, dy = 16, 11

            for image, block_name, fallback in blocks:
                base = find_image_center(page, image, 0.70)
                if base is None:
                    base = game_to_page(page, *fallback)

                bx, by = base
                for row in range(3):
                    for col in range(3):
                        cell = f"{block_name}_{row}_{col}"
                        x = bx + (col * dx) - (row * dx)
                        y = by + (row * dy) + (col * dy)

                        set_marker(f"cell_open:{cell}")
                        page.mouse.click(x, y)
                        time.sleep(1.6)

                        if find_image_center(page, "shouhuo_btn.png", 0.80):
                            set_marker(f"harvest:{cell}")
                            click_image(page, "shouhuo_btn.png", 0.80)
                            time.sleep(2.0)
                            set_marker(f"cell_reopen:{cell}")
                            page.mouse.click(x, y)
                            time.sleep(1.6)

                        if find_image_center(page, "search_bar.png", 0.75):
                            set_marker(f"seed_panel:{cell}")
                            plant_any_available_seed(page, cell)

                        set_marker(f"close_panel:{cell}")
                        click_game(page, 200, 30)
                        time.sleep(0.9)

            set_marker("done")
            page.screenshot(path=str(OUT / "final.png"))

        finally:
            with open(OUT / "frames.jsonl", "w", encoding="utf-8") as f:
                for item in frames:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            summarize()
            browser.close()


if __name__ == "__main__":
    run()
