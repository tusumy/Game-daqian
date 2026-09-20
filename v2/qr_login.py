import json
import os
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from playwright.sync_api import sync_playwright

import recorder

ROOT = Path(__file__).resolve().parents[1]
QR_OUT = ROOT / "v2" / "qr"
QR_OUT.mkdir(parents=True, exist_ok=True)

LOGIN_URL = "https://www.wanyiwan.top/login/xddq"
GAME_URL = "https://www.wanyiwan.top/game/xddq"
PORTAL_URL = "https://www.wanyiwan.top/"
SCAN_TIMEOUT = int(os.getenv("QR_SCAN_TIMEOUT", "900"))


NETWORK_LOG = QR_OUT / "network.jsonl"
STATE_LOG = QR_OUT / "state_trace.jsonl"


def append_jsonl(path, data):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def sanitize_url(url):
    try:
        parts = urlsplit(url)
        keys = sorted({k for k, _ in parse_qsl(parts.query, keep_blank_values=True)})
        query = "&".join(f"{k}=<redacted>" for k in keys)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))
    except Exception:
        return url.split("?", 1)[0]


def data_shape(value, depth=0):
    if depth >= 3:
        return type(value).__name__
    if isinstance(value, dict):
        return {str(k): data_shape(v, depth + 1) for k, v in list(value.items())[:40]}
    if isinstance(value, list):
        return [data_shape(value[0], depth + 1)] if value else []
    return type(value).__name__


def request_shape(post_data):
    if not post_data:
        return None
    try:
        return {"json": data_shape(json.loads(post_data))}
    except Exception:
        try:
            return {"form_keys": sorted({k for k, _ in parse_qsl(post_data, keep_blank_values=True)})}
        except Exception:
            return {"kind": "opaque", "length": len(post_data)}


def hook_http(page):
    def on_request(req):
        try:
            append_jsonl(NETWORK_LOG, {
                "ts": time.time(),
                "kind": "request",
                "method": req.method,
                "resource_type": req.resource_type,
                "url": sanitize_url(req.url),
                "post": request_shape(req.post_data),
            })
        except Exception:
            pass

    def on_response(resp):
        try:
            item = {
                "ts": time.time(),
                "kind": "response",
                "status": resp.status,
                "url": sanitize_url(resp.url),
                "content_type": resp.headers.get("content-type", ""),
            }
            if "json" in item["content_type"].lower():
                try:
                    body = resp.json()
                    item["json_shape"] = data_shape(body)
                except Exception:
                    pass
            append_jsonl(NETWORK_LOG, item)
        except Exception:
            pass

    page.on("request", on_request)
    page.on("response", on_response)


def snapshot_state(page, label):
    try:
        js = page.evaluate("""() => ({
          href: location.href,
          ternPresent: !!window.__TERN__,
          clientUserPresent: !!(window.__TERN__ && window.__TERN__.user && window.__TERN__.user.clientUser),
          clientUserKeys: (window.__TERN__ && window.__TERN__.user && window.__TERN__.user.clientUser)
            ? Object.keys(window.__TERN__.user.clientUser).sort() : [],
          localStorageKeys: Object.keys(localStorage).sort(),
          sessionStorageKeys: Object.keys(sessionStorage).sort(),
        })""")
    except Exception as exc:
        js = {"error": str(exc), "href": getattr(page, "url", "")}

    try:
        cookies = page.context.cookies()
        cookie_names = sorted({f"{c.get('domain','')}|{c.get('name','')}" for c in cookies})
    except Exception:
        cookie_names = []

    append_jsonl(STATE_LOG, {
        "ts": time.time(),
        "label": label,
        "qr_present": qr_locator(page) is not None,
        "qr_page": is_qr_page(page),
        "frames": len(recorder.frames),
        "cookies": cookie_names,
        **js,
    })


def write_status(data):
    (QR_OUT / "status.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def is_qr_page(page):
    try:
        text = page.locator("body").inner_text(timeout=1500)
        return "支付宝扫码即玩" in text or "使用支付宝扫码即玩" in text
    except Exception:
        return False


def qr_locator(page):
    selectors = [
        ".qrCodeContainer-yvXXNfUj canvas",
        "[class*='qrCodeContainer'] canvas",
        "canvas[ke]",
    ]
    for selector in selectors:
        try:
            loc = page.locator(selector)
            for i in range(loc.count()):
                item = loc.nth(i)
                box = item.bounding_box()
                if box and box["width"] >= 100 and box["height"] >= 100:
                    return item
        except Exception:
            pass
    return None


def pc_web_auth_ready(page):
    try:
        return bool(page.evaluate("""() =>
          !!localStorage.getItem('x-game-token-pcweb') &&
          !!localStorage.getItem('x-game-uid-pcweb')
        """))
    except Exception:
        return False


def real_game_ready(page):
    if recorder.frames:
        return True
    if client_user_ready(page):
        return True
    if is_qr_page(page):
        return False
    try:
        if "/game/xddq" in page.url:
            canvases = page.locator("canvas")
            for i in range(canvases.count()):
                box = canvases.nth(i).bounding_box()
                if box and box["width"] >= 300 and box["height"] >= 300:
                    return True
    except Exception:
        pass
    return False


def mark_failed(message):
    write_status({"state": "failed", "message": message})
    (QR_OUT / "FAILED").write_text(message, encoding="utf-8")


def client_user_ready(page):
    try:
        return bool(
            page.evaluate(
                """() => !!(window.__TERN__ && window.__TERN__.user && window.__TERN__.user.clientUser)"""
            )
        )
    except Exception:
        return False


def save_frames():
    with open(QR_OUT / "frames.jsonl", "w", encoding="utf-8") as f:
        for item in recorder.frames:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def probe_farm(page):
    recorder.set_marker("post_login_wait")
    time.sleep(18)
    page.screenshot(path=str(QR_OUT / "game_loaded.png"))

    # 旧版脚本进入游戏前的手势先保留；如果网页新版不需要，也不会影响抓包主目标。
    try:
        recorder.drag_game(page, 750, 300, 150, 300)
        time.sleep(2)
        recorder.click_game(page, 100, 750)
        time.sleep(1)
        recorder.set_marker("close_notice")
        recorder.click_image(page, "close_notice.png", 0.70)
        time.sleep(2)
    except Exception as exc:
        print(f"[-] 预处理手势失败: {exc}")

    recorder.set_marker("enter_game")
    if recorder.wait_click(page, "enter_game_btn.png", "enter_game", 15):
        time.sleep(5)
    else:
        recorder.save_page_diagnostics(page, "qr_after_enter_timeout")

    if not recorder.wait_click(page, "dongfu_btn.png", "open_dongfu", 20):
        recorder.save_page_diagnostics(page, "qr_dongfu_timeout")
        print("[-] 已登录，但旧洞府模板未命中；保留当前 WebSocket 抓包")
        return

    if not recorder.wait_click(page, "danjie_btn.png", "open_danjie", 20):
        recorder.save_page_diagnostics(page, "qr_danjie_timeout")
        print("[-] 已进入洞府，但旧丹界模板未命中；保留当前 WebSocket 抓包")
        return

    time.sleep(4)
    page.screenshot(path=str(QR_OUT / "danjie.png"))

    blocks = [
        ("block_1.png", "left_bottom", (155, 530)),
        ("block_2.png", "left_top", (205, 490)),
        ("block_3.png", "right_top", (260, 480)),
        ("block_4.png", "right_bottom", (265, 520)),
    ]
    dx, dy = 16, 11

    for image, block_name, fallback in blocks:
        base = recorder.find_image_center(page, image, 0.70)
        if base is None:
            base = recorder.game_to_page(page, *fallback)

        bx, by = base
        for row in range(3):
            for col in range(3):
                cell = f"{block_name}_{row}_{col}"
                x = bx + (col * dx) - (row * dx)
                y = by + (row * dy) + (col * dy)

                recorder.set_marker(f"cell_open:{cell}")
                page.mouse.click(x, y)
                time.sleep(1.5)

                if recorder.find_image_center(page, "shouhuo_btn.png", 0.80):
                    recorder.set_marker(f"harvest:{cell}")
                    recorder.click_image(page, "shouhuo_btn.png", 0.80)
                    time.sleep(2)
                    recorder.set_marker(f"cell_reopen:{cell}")
                    page.mouse.click(x, y)
                    time.sleep(1.5)

                if recorder.find_image_center(page, "search_bar.png", 0.75):
                    recorder.set_marker(f"seed_panel:{cell}")
                    recorder.plant_any_available_seed(page, cell)

                recorder.set_marker(f"close_panel:{cell}")
                recorder.click_game(page, 200, 30)
                time.sleep(0.8)


def run():
    storage = None
    try:
        storage = recorder.load_storage_state()
    except Exception as exc:
        print(f"[*] 现有登录态不可用也没关系，将走二维码登录: {exc}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        kwargs = {
            "viewport": {"width": 1280, "height": 960},
            "device_scale_factor": 1,
        }
        if storage:
            kwargs["storage_state"] = storage

        context = browser.new_context(**kwargs)
        page = context.new_page()
        page.on("websocket", recorder.hook_websocket)
        hook_http(page)

        ok = False
        try:
            recorder.set_marker("open_login")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            snapshot_state(page, "after_goto")

            deadline = time.time() + 90
            while time.time() < deadline:
                if is_qr_page(page) or real_game_ready(page):
                    break
                snapshot_state(page, "wait_initial")
                time.sleep(1)

            if pc_web_auth_ready(page):
                print("[+] 已从保存的 storage_state 恢复 pcweb 登录态，跳过重新扫码")
            elif is_qr_page(page):
                print("[*] 已进入支付宝扫码页，等待二维码组件真正生成")
                qr = None
                qr_deadline = time.time() + 90
                while time.time() < qr_deadline:
                    qr = qr_locator(page)
                    if qr is not None:
                        break
                    if real_game_ready(page):
                        break
                    snapshot_state(page, "wait_qr_canvas")
                    time.sleep(1)

                if real_game_ready(page):
                    print("[+] 等二维码期间检测到游戏已连接，直接继续")
                elif qr is None:
                    recorder.save_page_diagnostics(page, "qr_missing_canvas")
                    raise RuntimeError("支付宝扫码页已加载，但二维码组件 90 秒内仍未生成")
                else:
                    qr.screenshot(path=str(QR_OUT / "qr.png"))
                    page.screenshot(path=str(QR_OUT / "login_page.png"), full_page=True)
                    write_status({
                        "state": "waiting_for_scan",
                        "url": page.url,
                        "expires_in_seconds": SCAN_TIMEOUT,
                    })
                    (QR_OUT / "READY").write_text("scan qr.png with Alipay", encoding="utf-8")
                    print(f"[QR_READY] 二维码已生成，等待支付宝扫码，最多 {SCAN_TIMEOUT} 秒")
                    snapshot_state(page, "qr_ready")

                    deadline = time.time() + SCAN_TIMEOUT
                    left_qr_since = None
                    while time.time() < deadline:
                        if pc_web_auth_ready(page):
                            print("[+] 已检测到 pcweb 登录凭据写入 localStorage")
                            break
                        if real_game_ready(page):
                            break

                        current_qr = qr_locator(page)
                        if current_qr is None and "/login/xddq" not in page.url:
                            if left_qr_since is None:
                                left_qr_since = time.time()
                            elif time.time() - left_qr_since >= 5:
                                print("[+] 二维码已消失并离开登录页，按扫码成功继续")
                                break
                        else:
                            left_qr_since = None

                        snapshot_state(page, "wait_after_scan")
                        time.sleep(1)
                    else:
                        raise RuntimeError("等待支付宝扫码超时")
            elif not real_game_ready(page):
                recorder.save_page_diagnostics(page, "login_state_unknown")
                raise RuntimeError("既没有出现支付宝扫码页，也没有检测到真实游戏连接")

            if pc_web_auth_ready(page) and not real_game_ready(page):
                print("[+] 支付宝 PC 登录已成功，保存登录态并从玩一玩首页进入游戏")
                context.storage_state(path=str(QR_OUT / "storage_state.json"))
                recorder.set_marker("pc_auth_open_portal")
                page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=60000)
                time.sleep(4)
                recorder.save_page_diagnostics(page, "portal_after_pc_auth")

                if not recorder.enter_xddq_from_portal(page):
                    raise RuntimeError("PC 登录成功，但从玩一玩首页未能进入寻道大千")

                game_deadline = time.time() + 90
                while time.time() < game_deadline:
                    snapshot_state(page, "wait_game_after_pc_auth")
                    if real_game_ready(page):
                        break
                    time.sleep(1)

                if not real_game_ready(page):
                    recorder.save_page_diagnostics(page, "pc_auth_game_not_ready")
                    raise RuntimeError("PC 登录凭据已拿到，但返回游戏页后未建立游戏连接")

            snapshot_state(page, "login_success_detected")
            recorder.set_marker("login_success")
            write_status({"state": "logged_in", "url": page.url})
            page.screenshot(path=str(QR_OUT / "after_scan.png"), full_page=True)
            context.storage_state(path=str(QR_OUT / "storage_state.json"))
            print(f"[+] 登录态确认成功，当前 URL: {page.url}")

            time.sleep(12)
            recorder.save_page_diagnostics(page, "post_login")
            probe_farm(page)
            recorder.set_marker("done")
            time.sleep(5)

            write_status({
                "state": "done",
                "url": page.url,
                "captured_frames": len(recorder.frames),
            })
            (QR_OUT / "DONE").write_text(
                f"frames={len(recorder.frames)}", encoding="utf-8"
            )
            ok = True

        except Exception as exc:
            message = str(exc)
            print(f"[!] {message}")
            mark_failed(message)
            try:
                recorder.save_page_diagnostics(page, "failure")
            except Exception:
                pass
            raise
        finally:
            save_frames()
            recorder.summarize()
            if not ok and not (QR_OUT / "FAILED").exists():
                mark_failed("扫码抓包进程未正常完成")
            browser.close()


if __name__ == "__main__":
    run()

# QR_REFRESH_TRIGGER
