import cv2
import numpy as np
import time
import os
import json
from playwright.sync_api import sync_playwright

def find_image_center(page, template_path, confidence=0.7):
    """寻找图像中心坐标"""
    try:
        screenshot_bytes = page.screenshot()
        nparr = np.frombuffer(screenshot_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if img is None or template is None:
            return None
        res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val >= confidence:
            h, w, _ = template.shape
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return (center_x, center_y)
    except Exception:
        pass
    return None

def find_and_click_image(page, template_path, confidence=0.75):
    """点击图片中心"""
    center = find_image_center(page, template_path, confidence)
    if center:
        page.mouse.click(center[0], center[1])
        return True
    return False

def image_exists(page, template_path, confidence=0.75):
    """判断图片是否存在"""
    return find_image_center(page, template_path, confidence) is not None

def auto_wait_and_click(page, img_name, timeout=15, desc=""):
    """等待并点击"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if find_and_click_image(page, img_name):
            time.sleep(2.5)
            return True
        time.sleep(1.2)
    return False

def run():
    with sync_playwright() as p:
        # 关闭无头模式，方便观察；你可以自己改回True
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 800, "height": 900})

        if os.path.exists("auth.json"):
            try:
                with open("auth.json", "r", encoding="utf-8") as f:
                    json.load(f)
                context = browser.new_context(
                    viewport={"width": 800, "height": 900},
                    storage_state="auth.json"
                )
            except:
                pass

        page = context.new_page()
        page.goto("https://www.wanyiwan.top/game/xddq")
        time.sleep(15)

        # === 关键修正：获取游戏容器的真实偏移 ===
        container_info = page.evaluate("""
            (() => {
                const canvas = document.querySelector('canvas');
                if (!canvas) return null;
                const rect = canvas.getBoundingClientRect();
                return { left: rect.left, top: rect.top };
            })()
        """)
        offset_x = container_info['left'] if container_info else 0
        offset_y = container_info['top'] if container_info else 0
        print(f"检测到游戏容器偏移: ({offset_x}, {offset_y})")

        # === 定义带偏移修正的点击函数 ===
        def click_with_offset(x, y):
            page.mouse.click(int(x + offset_x), int(y + offset_y))

        try:
            # === 第一步：右滑清场 ===
            page.mouse.move(750, 300)
            page.mouse.down()
            page.mouse.move(150, 300, steps=30)
            page.mouse.up()
            time.sleep(3.0)

            page.mouse.click(100, 750)
            time.sleep(1.5)
            # 修正后的点击
            find_and_click_image(page, "close_notice.png")
            time.sleep(2.5)

            # === 第二步：导航 ===
            auto_wait_and_click(page, "enter_game_btn.png", timeout=12, desc="踏入仙途")
            auto_wait_and_click(page, "dongfu_btn.png", timeout=15, desc="洞府")
            auto_wait_and_click(page, "danjie_btn.png", timeout=15, desc="丹界药田")
            time.sleep(5.0)

            # === 第三步：药田大阵 ===
            farm_blocks = [
                {"img": "block_1.png", "name": "左下药田"},
                {"img": "block_2.png", "name": "左上药田"},
                {"img": "block_3.png", "name": "右上药田"},
                {"img": "block_4.png", "name": "右下药田"}
            ]

            dx, dy = 16, 11

            print("\n[★] 诸天至尊：【像素锁定·绝对命中流】收种大阵，起！！！")
            for b in farm_blocks:
                print(f"[*] 雷达正在全屏动态搜寻：【{b['name']}】的基准图腾...")
                center_coord = find_image_center(page, b["img"], confidence=0.7)

                if center_coord is None:
                    print(f"    [-] 警告：屏幕上没抓到【{b['name']}】的切图，使用兜底坐标...")
                    if b["name"] == "左下药田":
                        center_coord = (155, 530)
                    elif b["name"] == "左上药田":
                        center_coord = (205, 490)
                    elif b["name"] == "右上药田":
                        center_coord = (260, 480)
                    else:
                        center_coord = (265, 520)

                base_x, base_y = center_coord
                print(f"    [+] 基准坐标锁定成功：({base_x}, {base_y})。开始挨个收拾九层地块...")

                for row in range(3):
                    for col in range(3):
                        click_x = base_x + (col * dx) - (row * dx)
                        click_y = base_y + (row * dy) + (col * dy)

                        # 使用带偏移修正的点击
                        click_with_offset(click_x, click_y)
                        time.sleep(2.0)

                        if find_and_click_image(page, "shouhuo_btn.png", confidence=0.8):
                            print("        [+] 抓到熟透的青石斛，收割！")
                            time.sleep(2.5)
                            click_with_offset(click_x, click_y)
                            time.sleep(2.0)

                        if image_exists(page, "search_bar.png", confidence=0.75):
                            find_and_click_image(page, "search_bar.png", confidence=0.75)
                            time.sleep(1.0)
                            page.keyboard.type("青石斛")
                            time.sleep(1.5)

                            if find_and_click_image(page, "qingshihu_seed.png", confidence=0.8):
                                print("        [+] 绝对命中！播种成功！")
                            else:
                                click_with_offset(click_x, click_y - 60)
                            time.sleep(2.0)
                        else:
                            print("        [-] 地里长着活菜呢，不打扰，跳过...")

                        page.mouse.click(200, 30)
                        time.sleep(1.2)

            print("\n[+] --- 诸天药田【绝对命中流】大阵全部圆满功成！！！ ---")

        except Exception as e:
            print(f"!!! 阵法阻碍: {e}")
            page.screenshot(path="error_scene.png")
        finally:
            browser.close()

if __name__ == "__main__":
    run()