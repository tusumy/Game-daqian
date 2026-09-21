import json
import os
import time
import traceback

import cv2
import numpy as np
from playwright.sync_api import sync_playwright

DEFAULT_GAME_URL = "https://www.wanyiwan.top/game/xddq"
VIEWPORT = {
    "width": int(os.getenv("VIEWPORT_WIDTH", "800")),
    "height": int(os.getenv("VIEWPORT_HEIGHT", "900")),
}


def env_flag(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off", ""}


def load_storage_state():
    """优先读取 GitHub Secret；本地仍兼容仓库里的 auth.json。"""
    raw = (os.getenv("GAME_AUTH_JSON") or os.getenv("AUTH_JSON") or "").strip()
    if raw:
        try:
            state = json.loads(raw)
            print("[+] 已从环境变量载入登录态")
            return state
        except json.JSONDecodeError as exc:
            print(f"[-] GAME_AUTH_JSON/AUTH_JSON 不是有效 JSON：{exc}")

    if os.path.exists("auth.json"):
        try:
            with open("auth.json", "r", encoding="utf-8") as f:
                state = json.load(f)
            print("[+] 已从 auth.json 载入登录态")
            return state
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[-] auth.json 读取失败：{exc}")

    print("[-] 未找到可用登录态，将尝试直接打开游戏页")
    return None


def get_game_rect(page):
    """返回 canvas 在页面 CSS 坐标系中的矩形。"""
    info = page.evaluate(
        """
        (() => {
            const canvas = document.querySelector('canvas');
            if (!canvas) return null;
            const r = canvas.getBoundingClientRect();
            return {
                left: r.left,
                top: r.top,
                width: r.width,
                height: r.height
            };
        })()
        """
    )
    if not info or info["width"] <= 0 or info["height"] <= 0:
        return None
    return info


def screenshot_image(page):
    data = page.screenshot()
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)


def find_image_center(page, template_path, confidence=0.75, within_game=True):
    """
    在当前截图里匹配模板。
    within_game=True 时只在 canvas 范围内匹配，但返回值始终是页面绝对坐标，
    因此后续点击不再额外叠加 canvas 偏移。
    """
    try:
        img = screenshot_image(page)
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if img is None or template is None:
            return None

        origin_x = 0
        origin_y = 0
        search_img = img

        if within_game:
            rect = get_game_rect(page)
            if rect:
                x1 = max(0, int(round(rect["left"])))
                y1 = max(0, int(round(rect["top"])))
                x2 = min(img.shape[1], int(round(rect["left"] + rect["width"])))
                y2 = min(img.shape[0], int(round(rect["top"] + rect["height"])))
                if x2 > x1 and y2 > y1:
                    search_img = img[y1:y2, x1:x2]
                    origin_x, origin_y = x1, y1

        th, tw = template.shape[:2]
        ih, iw = search_img.shape[:2]
        if th > ih or tw > iw:
            return None

        result = cv2.matchTemplate(search_img, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < confidence:
            return None

        return (
            origin_x + max_loc[0] + tw // 2,
            origin_y + max_loc[1] + th // 2,
        )
    except Exception as exc:
        print(f"[-] 模板匹配失败 {template_path}: {exc}")
        return None


def find_and_click_image(page, template_path, confidence=0.75, within_game=True):
    center = find_image_center(page, template_path, confidence, within_game)
    if not center:
        return False
    page.mouse.click(center[0], center[1])
    return True


def image_exists(page, template_path, confidence=0.75, within_game=True):
    return (
        find_image_center(page, template_path, confidence, within_game) is not None
    )


def auto_wait_and_click(
    page, img_name, timeout=15, desc="", confidence=0.75, within_game=True
):
    start = time.time()
    while time.time() - start < timeout:
        if find_and_click_image(page, img_name, confidence, within_game):
            print(f"[+] 已点击：{desc or img_name}")
            time.sleep(2.5)
            return True
        time.sleep(1.0)
    print(f"[-] 等待超时：{desc or img_name}")
    return False


def game_to_page(page, x, y):
    """把以 canvas 左上角为原点的坐标换算成页面绝对坐标。"""
    rect = get_game_rect(page)
    if not rect:
        return int(x), int(y)
    return int(round(rect["left"] + x)), int(round(rect["top"] + y))


def click_game(page, x, y):
    px, py = game_to_page(page, x, y)
    page.mouse.click(px, py)


def drag_game(page, x1, y1, x2, y2, steps=30):
    sx, sy = game_to_page(page, x1, y1)
    ex, ey = game_to_page(page, x2, y2)
    page.mouse.move(sx, sy)
    page.mouse.down()
    page.mouse.move(ex, ey, steps=steps)
    page.mouse.up()


def enter_danjie(page, timeout=180):
    """稳定清理登录/活动弹窗并进入丹界药田。"""
    deadline = time.time() + timeout
    last_click = {}

    while time.time() < deadline:
        now = time.time()

        # 个人信息保护提示：只点明确的“同意”模板。
        if now - last_click.get("privacy", 0) > 5:
            if find_and_click_image(
                page, "v2/templates/privacy_agree.png", confidence=0.80
            ):
                print("[+] 已处理个人信息保护提示")
                last_click["privacy"] = now
                time.sleep(3)
                continue

        # 网络状况不佳：优先点绿色“继续”，避免误点背后界面。
        if now - last_click.get("continue", 0) > 6:
            if find_and_click_image(
                page, "v2/templates/continue.png", confidence=0.80
            ):
                print("[+] 网络提示：继续")
                last_click["continue"] = now
                time.sleep(6)
                continue

        # 每日活动是固定分支：勾“今日不再提示”，再关右上角 X。
        daily = find_image_center(
            page, "v2/templates/daily_no_remind.png", confidence=0.78
        )
        if daily:
            page.mouse.click(daily[0] - 42, daily[1])
            time.sleep(0.8)
            closed = find_and_click_image(
                page, "v2/templates/event_x.png", confidence=0.82
            )
            if not closed:
                # 当前游戏 canvas 约 480px 宽；右上角空白处仅作保守兜底。
                click_game(page, 430, 120)
            print("[+] 每日活动：已勾今日不再提示并关闭")
            last_click["daily"] = now
            time.sleep(3)
            continue

        # 仙官发玉不是必经流程：只有模板真的出现才处理。
        officer = find_image_center(
            page, "v2/templates/officer_no_remind.png", confidence=0.80
        )
        if officer:
            page.mouse.click(officer[0] - 86, officer[1])
            time.sleep(0.8)
            # 点仙官层右侧空白收掉，不等待它出现，也不把它当固定步骤。
            click_game(page, 460, 320)
            print("[+] 仙官发玉：已勾本次登录不再提示并收起")
            last_click["officer"] = now
            time.sleep(3)
            continue

        # 公告/活动海报优先关闭。
        closed = False
        for path, desc in (
            ("v2/templates/notice_x.png", "公告"),
            ("v2/templates/event_x.png", "活动"),
            ("close_notice.png", "旧公告"),
        ):
            if find_and_click_image(page, path, confidence=0.82):
                print(f"[+] 已关闭{desc}")
                time.sleep(3)
                closed = True
                break
        if closed:
            continue

        # 启动画面：踏入仙途。兼容旧大模板和 v2 小模板。
        entered = False
        for path, confidence in (
            ("enter_game_btn.png", 0.72),
            ("v2/templates/enter_game_small.jpg", 0.75),
        ):
            if find_and_click_image(page, path, confidence=confidence):
                print("[+] 已点击踏入仙途")
                last_click["enter"] = now
                time.sleep(10)
                entered = True
                break
        if entered:
            continue

        # 已经在洞府时，丹界入口出现就直接进入。
        if find_and_click_image(page, "danjie_btn.png", confidence=0.72):
            print("[+] 已进入丹界药田")
            time.sleep(5)
            return True

        # 主界面洞府入口：优先沿用正式任务模板，失败再尝试 v2 模板。
        if now - last_click.get("dongfu", 0) > 6:
            for path, confidence in (
                ("dongfu_btn.png", 0.72),
                ("v2/templates/dongfu.png", 0.75),
            ):
                if find_and_click_image(page, path, confidence=confidence):
                    print("[+] 已点击洞府")
                    last_click["dongfu"] = now
                    time.sleep(6)
                    break
            else:
                time.sleep(1.5)
            continue

        time.sleep(1.5)

    return False


def run():
    game_url = os.getenv("GAME_URL", DEFAULT_GAME_URL)
    headless = env_flag("HEADLESS", default=bool(os.getenv("CI")))
    storage_state = load_storage_state()

    page = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context_kwargs = {
            "viewport": VIEWPORT,
            "device_scale_factor": 1,
        }
        if storage_state:
            context_kwargs["storage_state"] = storage_state

        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.set_default_timeout(15_000)

        try:
            print(
                f"[+] 启动浏览器：headless={headless}, viewport="
                f"{VIEWPORT['width']}x{VIEWPORT['height']}"
            )
            page.goto(game_url, wait_until="domcontentloaded", timeout=60_000)
            time.sleep(12)

            rect = get_game_rect(page)
            if rect:
                print(
                    "[+] 游戏 canvas："
                    f"left={rect['left']:.1f}, top={rect['top']:.1f}, "
                    f"size={rect['width']:.0f}x{rect['height']:.0f}"
                )
            else:
                print("[-] 暂未检测到 canvas，将继续尝试页面坐标")

            # 稳定启动：弹窗出现才处理，不再盲滑/盲点，也不等待可选仙官层。
            if not enter_danjie(page, timeout=180):
                raise RuntimeError("未能在限定时间内进入丹界药田")

            farm_blocks = [
                {
                    "img": "block_1.png",
                    "name": "左下药田",
                    "fallback": (155, 530),
                },
                {
                    "img": "block_2.png",
                    "name": "左上药田",
                    "fallback": (205, 490),
                },
                {
                    "img": "block_3.png",
                    "name": "右上药田",
                    "fallback": (260, 480),
                },
                {
                    "img": "block_4.png",
                    "name": "右下药田",
                    "fallback": (265, 520),
                },
            ]
            dx, dy = 16, 11

            print("\n[★] 开始逐块检查药田")
            for block in farm_blocks:
                print(f"[*] 搜寻：{block['name']}")
                base = find_image_center(page, block["img"], confidence=0.70)

                if base is None:
                    print(
                        f"    [-] 未匹配到 {block['name']}，使用 canvas 内兜底坐标"
                    )
                    base = game_to_page(page, *block["fallback"])
                else:
                    print(f"    [+] 匹配成功：{base}")

                base_x, base_y = base

                for row in range(3):
                    for col in range(3):
                        click_x = base_x + (col * dx) - (row * dx)
                        click_y = base_y + (row * dy) + (col * dy)

                        # base 已是页面绝对坐标，绝不能再重复加 canvas 偏移。
                        page.mouse.click(click_x, click_y)
                        time.sleep(1.8)

                        if find_and_click_image(
                            page, "shouhuo_btn.png", confidence=0.80
                        ):
                            print("        [+] 收获")
                            time.sleep(2.2)
                            page.mouse.click(click_x, click_y)
                            time.sleep(1.8)

                        if image_exists(page, "search_bar.png", confidence=0.75):
                            find_and_click_image(
                                page, "search_bar.png", confidence=0.75
                            )
                            time.sleep(0.8)
                            page.keyboard.press("Control+A")
                            page.keyboard.type("青石斛")
                            time.sleep(1.3)

                            if find_and_click_image(
                                page, "qingshihu_seed.png", confidence=0.80
                            ):
                                print("        [+] 播种青石斛")
                            else:
                                # 仅作为模板识别失败时的保守兜底。
                                page.mouse.click(click_x, click_y - 60)
                                print("        [-] 种子模板未命中，已尝试兜底点击")
                            time.sleep(1.8)
                        else:
                            print("        [=] 当前地块无需播种")

                        # 点击游戏画布上方空白处，尽量关闭残留面板。
                        click_game(page, 200, 30)
                        time.sleep(1.0)

            page.screenshot(path="final_scene.png")
            print("\n[+] 药田流程执行完成")

        except Exception as exc:
            print(f"!!! 自动化执行失败：{exc}")
            traceback.print_exc()
            if page is not None:
                try:
                    page.screenshot(path="error_scene.png")
                except Exception:
                    pass
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    run()
