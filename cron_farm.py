import cv2
import numpy as np
import time
from playwright.sync_api import sync_playwright

def find_and_click_image(page, template_path, confidence=0.8):
    """
    用OpenCV在当前游戏画面中寻找指定的切图，找到了就点它中心点
    """
    # 这里保持你原有的视觉雷达函数逻辑不动
    try:
        screenshot_bytes = page.screenshot()
        nparr = np.frombuffer(screenshot_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        
        if img is None or template is None:
            return False
            
        res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        if max_val >= confidence:
            h, w, _ = template.shape
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            page.mouse.click(center_x, center_y)
            return True
    except Exception as e:
        print(f"[-] 视觉雷达扫描异常: {e}")
    return False

def run():
    with sync_playwright() as p:
        # 这里对应你原先启动浏览器、登录、进入丹界的逻辑
        # 假设你原本的变量名是 browser 和 page
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # ------------------ 你的前置登录与着陆逻辑 ------------------
        # （此处系统会自动执行你原先写在前面的特定游戏URL跳转与登录）
        # ----------------------------------------------------------

        try:
            print("--- 成功着陆丹界！雷达开启像素级扫描 ---")

            # ==================== 尊上无上绝学：36坑视觉收种合一大阵 ====================
            blocks = [
                {"start": (155, 530), "name": "左下药田"},
                {"start": (205, 490), "name": "左上药田"},
                {"start": (260, 480), "name": "右上药田"},
                {"start": (265, 520), "name": "右下药田"}
            ]
            dx, dy = 16, 11

            print("\n[+] 诸天至尊：36坑视觉收种合一无上大阵，起！！！")

            for b in blocks:
                print(f"[*] 雷达正在死守并锁死：{b['name']}")
                start_x, start_y = b["start"]

                for row in range(3):
                    for col in range(3):
                        click_x = start_x + (col * dx) - (row * dx)
                        click_y = start_y + (row * dy) + (col * dy)

                        print(f"\n    [★] 正在全神贯注对准第 {row*3 + col + 1} 块小土坑 (坐标: {click_x}, {click_y})")

                        # 第一步：先对这个小土坑狠狠砸下一拳
                        page.mouse.click(click_x, click_y)
                        time.sleep(2.5)

                        # 第二步：情况A - 如果熟了，调用视觉雷达抓取“收获”小手
                        if find_and_click_image(page, "shouhuo_btn.png", confidence=0.8):
                            print("        [+] 拔草成功！收割一株极品青石斛！")
                            time.sleep(3.0)

                            # 地空了，原地再补一拳，调出种子菜单
                            page.mouse.click(click_x, click_y)
                            time.sleep(2.5)

                        # 第三步：情况B - 无论原本就是空地，还是刚收割完的空地，开始种菜
                        if find_and_click_image(page, "qingshihu_seed.png", confidence=0.8):
                            print("        [+] 播种成功！全新青石斛已入土安家！")
                            time.sleep(2.0)
                        else:
                            print("        [-] 警告：未能找到种子，可能此坑已经种过了，或者种子耗尽！")

                        # 安全机制：点一下最上方空白处关闭可能残存的弹窗
                        page.mouse.click(225, 50)
                        time.sleep(1.5)

            print("--- 药田日常无缝打理完毕，功成身退 ---")

        except Exception as e:
            print(f"!!! 渡劫失败，翻车原因: {e}")
            page.screenshot(path="failed_scene.png")
            print("[*] 翻车现场已拍照存证 `failed_scene.png`")

        finally:
            browser.close()

if __name__ == "__main__":
    run()
