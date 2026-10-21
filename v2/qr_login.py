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


def portal_login_required(page):
    try:
        btn = page.locator('img[alt="立即登录"]')
        for i in range(btn.count()):
            if btn.nth(i).is_visible():
                return True
    except Exception:
        pass
    try:
        return page.get_by_text("登录后查看VIP等级", exact=False).count() > 0
    except Exception:
        return False


def wait_portal_ready(page, timeout=45):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if page.title() == "支付宝游戏中心" and page.locator(".swiper-button-next").count() > 0:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def capture_portal_login_qr(page):
    if not portal_login_required(page):
        return None

    print("[*] 首页当前是匿名态，点击右侧“立即登录”")
    try:
        page.evaluate("""() => {
          localStorage.removeItem('x-game-token-pcweb');
          localStorage.removeItem('x-game-uid-pcweb');
        }""")
    except Exception:
        pass

    btn = page.locator('img[alt="立即登录"]')
    visible = None
    for i in range(btn.count()):
        try:
            if btn.nth(i).is_visible():
                visible = btn.nth(i)
                break
        except Exception:
            pass
    if visible is None:
        raise RuntimeError("首页显示未登录，但找不到可见的“立即登录”按钮")

    visible.click(timeout=8000, force=True)

    # 点击后会导航到 /login。此时首页的“立即登录”当然消失，
    # 不能把它误判成已登录；只认登录页实际生成出来的二维码。
    deadline = time.time() + 60
    while time.time() < deadline:
        qr = qr_locator(page)
        if qr is not None:
            print(f"[+] 登录页二维码已出现，当前 URL: {page.url}")
            return qr
        snapshot_state(page, "wait_portal_qr")
        time.sleep(1)
    recorder.save_page_diagnostics(page, "portal_qr_missing")
    raise RuntimeError("点击首页“立即登录”后 60 秒内没有出现支付宝二维码")


def wait_portal_login_success(page):
    deadline = time.time() + SCAN_TIMEOUT

    while time.time() < deadline:
        if pc_web_auth_ready(page):
            print("[+] 已收到 pcweb 扫码认证结果，认证成功")
            try:
                page.context.storage_state(path=str(QR_OUT / "pc_auth_state.json"))
                recorder.save_page_diagnostics(page, "pc_auth_success")
                page.screenshot(path=str(QR_OUT / "pc_auth_success.png"), full_page=True)
            except Exception:
                pass
            return True

        snapshot_state(page, "wait_portal_login")
        time.sleep(1)
    return False


def _visible_text(page, text):
    try:
        loc = page.get_by_text(text, exact=True)
        for i in range(loc.count()):
            if loc.nth(i).is_visible():
                return True
    except Exception:
        pass
    return False


def _click_confirm_login(page):
    selectors = [
        lambda: page.get_by_role("button", name="确认登录", exact=True),
        lambda: page.get_by_text("确认登录", exact=True),
    ]
    for make in selectors:
        try:
            loc = make()
            for i in range(loc.count()):
                item = loc.nth(i)
                if item.is_visible():
                    item.click(timeout=5000, force=True)
                    return True
        except Exception:
            pass
    return False


def _remove_named_devices_and_login(page, names=("Chrome",)):
    """
    仅移除用户明确授权的设备名称。
    当前授权：移除所有 Chrome，保留 Edge。
    """
    selected = 0

    # 每一行设备卡里都有设备名 + checkbox。只在包含指定设备名的行里勾选。
    for name in names:
        try:
            rows = page.locator("div").filter(has_text=name)
            seen = set()
            for i in range(rows.count()):
                row = rows.nth(i)
                try:
                    text = row.inner_text(timeout=1000).strip()
                except Exception:
                    continue
                # 过滤祖先大容器，只保留短文本的设备行。
                if not text.startswith(name) or len(text) > 120 or text in seen:
                    continue
                seen.add(text)
                cb = row.locator('input[type="checkbox"]')
                if cb.count() == 0:
                    # 某些 UI checkbox 由 label/span 包装。
                    cb = row.locator('[role="checkbox"]')
                if cb.count() > 0:
                    try:
                        if not cb.first.is_checked():
                            cb.first.check(force=True)
                    except Exception:
                        cb.first.click(force=True)
                    selected += 1
        except Exception:
            pass

    # 兜底：按包含 Chrome 的设备行点击其左侧复选框区域。
    if selected == 0:
        try:
            labels = page.get_by_text("Chrome", exact=True)
            for i in range(labels.count()):
                label = labels.nth(i)
                if not label.is_visible():
                    continue
                row = label.locator("xpath=ancestor::*[.//input[@type='checkbox']][1]")
                if row.count() > 0:
                    cb = row.locator('input[type="checkbox"]').first
                    try:
                        if not cb.is_checked():
                            cb.check(force=True)
                    except Exception:
                        cb.click(force=True)
                    selected += 1
        except Exception:
            pass

    print(f"[+] 已按授权选择 {selected} 台 Chrome 设备准备移除")

    if selected < 2:
        recorder.save_page_diagnostics(page, "device_select_failed")
        return False

    # 明确只点“确认移除并登录”，不会碰其它设备。
    btn = page.get_by_text("确认移除并登录", exact=True)
    for i in range(btn.count()):
        item = btn.nth(i)
        if item.is_visible():
            item.click(timeout=8000, force=True)
            print("[+] 已点击“确认移除并登录”，等待前端继续进入游戏")
            return True

    recorder.save_page_diagnostics(page, "device_confirm_button_missing")
    return False


def wait_login_frontend_finish(page, timeout=150):
    deadline = time.time() + timeout
    auth_seen = False
    confirm_clicked = False

    while time.time() < deadline:
        url = page.url

        if "/game/xddq" in url:
            print(f"[+] 前端登录收尾完成，已跳到游戏页: {url}")
            return "game"

        if pc_web_auth_ready(page) and not auth_seen:
            auth_seen = True
            print("[+] pcweb 扫码认证已成功，等待前端设备检查与登录收尾")
            try:
                recorder.save_page_diagnostics(page, "pc_auth_wait_frontend")
            except Exception:
                pass

        # 达到 3 台设备上限时必须由用户决定移除哪一台；绝不自动删除。
        if _visible_text(page, "登录设备数量已达上限"):
            recorder.save_page_diagnostics(page, "device_limit")
            # 用户已明确授权：删除两台 Chrome，保留 Edge。
            if _remove_named_devices_and_login(page, names=("Chrome",)):
                time.sleep(3)
                continue
            write_status({
                "state": "device_limit",
                "message": "已到设备上限，但自动选择两台 Chrome 失败",
                "url": url,
            })
            return "device_limit"

        # 未满上限时，官方弹窗允许不移除任何设备直接“确认登录”。
        if (not confirm_clicked) and _visible_text(page, "管理登录设备"):
            if _click_confirm_login(page):
                confirm_clicked = True
                print("[+] 检测到普通设备管理提示，已点击“确认登录”（未移除任何设备）")

        # /login/xddq 理论上会直接跳 /game/xddq；保留 home 作为异常诊断信号。
        if "/home" in url:
            print("[*] 登录流程回到了首页，检查账号态后再继续")
            if not portal_login_required(page):
                return "home"

        snapshot_state(page, "wait_frontend_login_finish")
        time.sleep(1)

    return None


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 960},
            device_scale_factor=1,
        )

        def bind_page(p):
            try:
                p.on("websocket", recorder.hook_websocket)
            except Exception:
                pass
            try:
                hook_http(p)
            except Exception:
                pass

        context.on("page", bind_page)
        page = context.new_page()
        bind_page(page)

        ok = False
        try:
            # 直接走带 gameId 的官方登录路由。前端成功收尾后会自行 replace 到 /game/xddq。
            recorder.set_marker("open_login_xddq")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)

            # 清掉可能残留的半截 pcweb 状态，只让这次二维码登录驱动完整 onSuccess 流程。
            try:
                page.evaluate("""() => {
                  localStorage.removeItem('x-game-token-pcweb');
                  localStorage.removeItem('x-game-uid-pcweb');
                }""")
            except Exception:
                pass

            qr_canvas = None
            qr_deadline = time.time() + 90
            while time.time() < qr_deadline:
                qr_canvas = qr_locator(page)
                if qr_canvas is not None:
                    break
                snapshot_state(page, "wait_login_xddq_qr")
                time.sleep(1)

            if qr_canvas is None:
                recorder.save_page_diagnostics(page, "login_xddq_qr_missing")
                raise RuntimeError("/login/xddq 已打开，但 90 秒内没有生成二维码")

            qr_canvas.screenshot(path=str(QR_OUT / "qr.png"))
            page.screenshot(path=str(QR_OUT / "login_page.png"), full_page=True)
            write_status({
                "state": "waiting_for_scan",
                "url": page.url,
                "expires_in_seconds": SCAN_TIMEOUT,
                "flow": "login_xddq_frontend_owned",
            })
            (QR_OUT / "READY").write_text(
                "scan qr.png with Alipay", encoding="utf-8"
            )
            print(f"[QR_READY] /login/xddq 二维码已生成，等待扫码，最多 {SCAN_TIMEOUT} 秒")

            result = wait_login_frontend_finish(page, timeout=SCAN_TIMEOUT)
            if result == "device_limit":
                raise RuntimeError("登录设备数量已达上限，需要用户选择要移除的旧设备")
            if result is None:
                raise RuntimeError("扫码后前端登录收尾超时，没有进入寻道大千")

            if result == "home":
                # 正常情况不该走这里；若站点改成回首页，就用已登录首页启动游戏。
                recorder.set_marker("frontend_returned_home")
                launched = recorder.enter_xddq_from_portal(page)
                if not launched:
                    raise RuntimeError("登录成功后回到首页，但未能启动寻道大千")
                page = launched

            # The login token is already authenticated after the frontend reaches
            # the game route. Save it BEFORE testing whether the embedded game
            # canvas loads: network popups can block game readiness for minutes.
            if not pc_web_auth_ready(page):
                raise RuntimeError("前端已跳转，但缺少扫码后的登录凭据，拒绝保存空登录态")
            context.storage_state(path=str(QR_OUT / "storage_state.json"))
            write_status({"state": "auth_saved", "url": page.url})
            print("[AUTH_SAVED] 扫码认证完成，已提前保存可恢复的登录状态", flush=True)

            game_deadline = time.time() + 120
            while time.time() < game_deadline:
                snapshot_state(page, "wait_real_game")
                if real_game_ready(page):
                    break
                time.sleep(1)

            if not real_game_ready(page):
                recorder.save_page_diagnostics(page, "game_not_ready_after_frontend_login")
                raise RuntimeError("前端已完成登录跳转，但 120 秒内没有建立真实游戏连接")

            recorder.set_marker("login_success")
            context.storage_state(path=str(QR_OUT / "storage_state.json"))
            write_status({"state": "logged_in", "url": page.url})
            page.screenshot(path=str(QR_OUT / "after_scan.png"), full_page=True)
            print(f"[+] 完整登录并进入游戏成功: {page.url}")

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
