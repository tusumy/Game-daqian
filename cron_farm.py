import cv2
import numpy as np
import time
import os
import json
from playwright.sync_api import sync_playwright

def find_and_click_image(page, template_path, confidence=0.75):
    """【无上雷达】：锁定图腾中心并狠狠戳下去"""
    try:
        screenshot_bytes = page.screenshot()
        nparr = np.frombuffer(screenshot_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if img is None or template is None: return False
        res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val >= confidence:
            h, w, _ = template.shape
            page.mouse.click(max_loc[0] + w // 2, max_loc[1] + h // 2)
            return True
    except:
        pass
    return False

def auto_wait_and_click(page, img_name, timeout=15, desc=""):
    """【死等法轨】：苦苦等待路标出现并破开它"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if find_and_click_image(page, img_name):
            time.sleep(2.0)
            return True
        time.sleep(1.0)
    return False

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 尊上太极护体盾：防坏令牌炸仓
        context = None
        if os.path.exists("auth.json"):
            try:
                with open("auth.json", "r", encoding="utf-8") as f: json.load(f)
                context = browser.new_context(viewport={"width": 800, "height": 900}, storage_state="auth.json")
                print("[+] 带着30天登录神识令牌，破空出发！")
            except:
                context = browser.new_context(viewport={"width": 800, "height": 900})
        else:
            context = browser.new_context(viewport={"width": 800, "height": 900})
            
        page = context.new_page()
        page.goto("https://www.wanyiwan.top/game/xddq")
        time.sleep(15) # 等待天地重绘

        try:
            # === 第一步：超度公告弹窗 ===
            page.mouse.click(100, 700) # 先盲砸一拳清障
            find_and_click_image(page, "close_notice.png")
            time.sleep(2.0)

            # === 第二步：大撕裂右滑 ===
            page.mouse.move(700, 300)
            page.mouse.down()
            page.mouse.move(200, 300, steps=25)
            page.mouse.up()
            time.sleep(3.0)

            # === 第三步：戳中全屏按钮 ===
            if not find_and_click_image(page, "fullscreen_btn.png"):
                page.mouse.click(320, 290)
            time.sleep(6.0)

            # === 第四步：视觉无缝自导引，一路杀进丹界 ===
            auto_wait_and_click(page, "enter_game_btn.png", timeout=10, desc="踏入仙途")
            auto_wait_and_click(page, "dongfu_btn.png", timeout=12, desc="洞府图标")
            auto_wait_and_click(page, "danjie_btn.png", timeout=12, desc="丹界药田")
            print("[+] 成功！长工已空降全屏状态下的纯净药田核心！")
            time.sleep(5.0)

            # === 第五步：三十六天罡【搜索流】精准收种大阵 ===
            # 四个大土块的中心起点坐标
            blocks = [
                {"start": (155, 530), "name": "左下药田"},
                {"start": (205, 490), "name": "左上药田"},
                {"start": (260, 480), "name": "右上药田"},
                {"start": (265, 520), "name": "右下药田"}
            ]
            dx, dy = 16, 11

            print("\n[★] 诸天至尊：升级版【神识搜索流】药田拔草播种大阵，起！！！")
            for b in blocks:
                print(f"[*] 当前死守：{b['name']}")
                start_x, start_y = b["start"]
                for row in range(3):
                    for col in range(3):
                        click_x = start_x + (col * dx) - (row * dx)
                        click_y = start_y + (row * dy) + (col * dy)

                        # 1. 狠狠戳向地块
                        page.mouse.click(click_x, click_y)
                        time.sleep(2.0)

                        # 2. 如果露出了收获图标，立刻拔草
                        if find_and_click_image(page, "shouhuo_btn.png", confidence=0.8):
                            print("        [+] 拔草成功！收割一株青石斛！")
                            time.sleep(2.5)
                            page.mouse.click(click_x, click_y) # 再次戳开这块空地
                            time.sleep(2.0)

                        # 3. 🔥【核心神技】：利用搜索框直接定向抓取青石斛！
                        # 先用雷达锁定你截图里的“搜索灵植”小框
                        if find_and_click_image(page, "search_bar.png", confidence=0.75):
                            print("        [+] 锁定了搜索灵植框，正在注入法力...")
                            time.sleep(1.0)
                            # 往搜索框里直接键盘输入“青石斛”三个字！
                            page.keyboard.type("青石斛")
                            time.sleep(1.5)
                        else:
                            # 盲戳：如果没找到 search_bar 按钮，就盲戳灵植列表左上角的搜索框大概相对位置
                            page.mouse.click(click_x + 60, click_y - 120) 
                            time.sleep(1.0)
                            page.keyboard.type("青石斛")
                            time.sleep(1.5)

                        # 4. 搜索完后，青石斛会自动变成第一个！直接雷达戳它！
                        if find_and_click_image(page, "qingshihu_seed.png", confidence=0.8):
                            print("        [+] 搜索流定向播种成功！")
                            time.sleep(2.0)
                        else:
                            # 兜底盲戳第一个种子的位置
                            print("        [-] 搜索未完全匹配，盲戳灵植第一个格子...")
                            page.mouse.click(click_x, click_y - 60)
                            time.sleep(2.0)

                        # 5. 戳一下旁边毫无关联的空白天空（比如 200, 30），清空弹窗，防止挡住下一块地
                        page.mouse.click(200, 30)
                        time.sleep(1.2)

            print("\n[+] --- 诸天药田【搜索流】收种全部圆满功成！！！ ---")

        except Exception as e:
            print(f"!!! 阵法中途遇到法則排斥: {e}")
            page.screenshot(path="lost_way_scene.png")
        finally:
            browser.close()

if __name__ == "__main__":
    run()
