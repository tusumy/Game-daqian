import json
import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

import recorder

ROOT = Path(__file__).resolve().parents[1]
QR_OUT = ROOT / "v2" / "qr"
QR_OUT.mkdir(parents=True, exist_ok=True)

GAME_URL = os.getenv("GAME_URL") or "https://www.wanyiwan.top/game/xddq"
SCAN_TIMEOUT = int(os.getenv("QR_SCAN_TIMEOUT", "900"))


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
                    recorder.set_marker(f"search_open:{cell}")
                    recorder.click_image(page, "search_bar.png", 0.75)
                    time.sleep(0.8)
                    page.keyboard.press("Control+A")
                    page.keyboard.type("青石斛")
                    time.sleep(1.2)

                    if recorder.find_image_center(page, "qingshihu_seed.png", 0.80):
                        recorder.set_marker(f"seed_qingshihu:{cell}")
                        recorder.click_image(page, "qingshihu_seed.png", 0.80)
                        time.sleep(1.8)

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

        ok = False
        try:
            recorder.set_marker("open_login")
            page.goto(GAME_URL, wait_until="domcontentloaded", timeout=60000)

            deadline = time.time() + 90
            while time.time() < deadline:
                if is_qr_page(page) or real_game_ready(page):
                    break
                time.sleep(1)

            if is_qr_page(page):
                print("[*] 已进入支付宝扫码页，等待二维码组件真正生成")
                qr = None
                qr_deadline = time.time() + 90
                while time.time() < qr_deadline:
                    qr = qr_locator(page)
                    if qr is not None:
                        break
                    if real_game_ready(page):
                        break
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

                    deadline = time.time() + SCAN_TIMEOUT
                    left_qr_since = None
                    while time.time() < deadline:
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

                        time.sleep(1)
                    else:
                        raise RuntimeError("等待支付宝扫码超时")
            elif not real_game_ready(page):
                recorder.save_page_diagnostics(page, "login_state_unknown")
                raise RuntimeError("既没有出现支付宝扫码页，也没有检测到真实游戏连接")

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
