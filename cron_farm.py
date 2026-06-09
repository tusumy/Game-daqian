import cv2
import numpy as np
import time
import os
import json
from playwright.sync_api import sync_playwright

def find_and_click_image(page, template_path, confidence=0.8):
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
    except Exception as e:
        print(f"[-] 雷达失灵: {e}")
    return False

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 【尊上太极护体防炸盾】：彻底解决第 34 行的 JSONDecodeError 暴毙劫！
        context = None
        if os.path.exists("auth.json"):
            try:
                # 尝试用纯净法力探测一下令牌格式
                with open("auth.json", "r", encoding="utf-8") as f:
                    json.load(f)
                
                print("[+] 奇迹！你的 auth.json 格式竟然是合法的，正在注入神识...")
                context = browser.new_context(
                    viewport={"width": 800, "height": 900},
                    storage_state="auth.json"
                )
            except Exception as e:
                # 核心防炸点：如果这里抛出 JSONDecodeError，直接在这个小结界里化解！
                print(f"[!] 抓到叛徒！你的 auth.json 藏有非法字符 ({e})！尊上已将其物理超度，启动裸奔模式，绝不让长工爆仓！")
                context = browser.new_context(viewport={"width": 800, "height": 900})
        else:
            print("[-] 乾坤袋里未见 auth.json，长工将赤脚前往...")
            context = browser.new_context(viewport={"width": 800, "height": 900})
            
        page = context.new_page()
        print("[+] 正在破空开辟修仙通道...")
        page.goto("https://www.wanyiwan.top/game/xddq")
        
        print("[*] 正在给整个大阵充能（等候 15 秒）...")
        time.sleep(15)

        try:
            # ==================== 步法一：物理右滑 ====================
            print("\n[★] 步骤一：按住右侧，狠狠向左拖拽 500 像素...")
            page.mouse.move(700, 300)
            page.mouse.down()
            page.mouse.move(200, 300, steps=25)
            page.mouse.up()
            time.sleep(3.0)

            # 强拍一张右滑后的现场，发到产物里
            page.screenshot(path="after_slide_scene.png")
            print("    [+] 已拍下划拉后的画面：after_slide_scene.png")

            # ==================== 步法二：锁定全屏 ====================
            print("[★] 步骤二：雷达开始锁定【全屏】图腾...")
            if find_and_click_image(page, "fullscreen_btn.png", confidence=0.75):
                print("    [+] 成功戳中【全屏】按钮！")
                time.sleep(6.0)
            else:
                print("    [-] 雷达未找到全屏，启动终极盲戳相对坐标 (320, 290)！")
                page.mouse.click(320, 290)
                time.sleep(6.0)

            # 拍一张全屏后的证物
            page.screenshot(path="after_fullscreen_scene.png")
            print("    [+] 已拍下全屏后的画面：after_fullscreen_scene.png")

            # ==================== 步法三：36坑视觉收种 ====================
            blocks = [
                {"start": (155, 530), "name": "左下药田"},
                {"start": (205, 490), "name": "左上药田"},
                {"start": (260, 480), "name": "右上药田"},
                {"start": (265, 520), "name": "右下药田"}
            ]
            dx, dy = 16, 11

            print("\n[+] 诸天至尊：三十六天罡视觉收种大阵，起！！！")
            for b in blocks:
                print(f"[*] 当前死守药田：{b['name']}")
                start_x, start_y = b["start"]
                for row in range(3):
                    for col in range(3):
                        click_x = start_x + (col * dx) - (row * dx)
                        click_y = start_y + (row * dy) + (col * dy)

                        page.mouse.click(click_x, click_y)
                        time.sleep(2.0)

                        if find_and_click_image(page, "shouhuo_btn.png", confidence=0.8):
                            print("        [+] 拔草成功！")
                            time.sleep(2.5)
                            page.mouse.click(click_x, click_y)
                            time.sleep(2.0)

                        if find_and_click_image(page, "qingshihu_seed.png", confidence=0.8):
                            print("        [+] 播种成功！")
                            time.sleep(2.0)
                        else:
                            page.mouse.click(click_x + 120, click_y + 40)
                            time.sleep(1.5)
                            find_and_click_image(page, "qingshihu_seed.png", confidence=0.8)

                        page.mouse.click(200, 30)
                        time.sleep(1.0)

            print("\n[+] --- 药田打理大阵运转完毕 ---")

        except Exception as e:
            print(f"!!! 运行中遇到法则排斥: {e}")
            page.screenshot(path="final_error_scene.png")
        finally:
            browser.close()

if __name__ == "__main__":
    run()
