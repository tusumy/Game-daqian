import cv2
import numpy as np
import time
from playwright.sync_api import sync_playwright

def find_and_click_image(page, template_path, confidence=0.8):
    """
    用OpenCV在当前游戏画面中寻找指定的切图，找到了就点它中心点
    """
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

def find_seed_by_relative_flipping(page, b_click_x, b_click_y):
    """
    【尊上终极自创】：乾坤挪移相对翻页术。
    根据当前土坑的动态坐标 (b_click_x, b_click_y)，推算并点击相对的翻页按钮。
    """
    for page_num in range(3):  # 最多翻3页，防止种子耗尽导致卡死
        print(f"        [动态雷达] 正在扫描地块周边的种子菜单第 {page_num + 1} 页...")
        
        # 视觉雷达尝试在当前界面寻找青石斛种子
        if find_and_click_image(page, "qingshihu_seed.png", confidence=0.8):
            return True
            
        # ⚠️ 核心微调区：若第一页没有，根据当前土坑，实时推算翻页箭头的绝对坐标！
        # 本尊这里假设翻页按钮在当前地块的【右方120像素，下方40像素】处。
        # 明日你若发现戳不准翻页，只需修改下面这两行偏移量（+120 和 +40）即可！
        flip_x = b_click_x + 120
        flip_y = b_click_y + 40
        
        print(f"        [-] 当前页未见种子，启动相对翻页：戳动态坐标 ({flip_x}, {flip_y})")
        page.mouse.click(flip_x, flip_y) 
        time.sleep(1.5)  # 等待翻页动画
        
    return False

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # ------------------ 你的前置登录与着陆逻辑 ------------------
        # （系统会自动执行你原先写在前面的特定游戏URL跳转）
        # ----------------------------------------------------------

        try:
            print("--- 成功着陆丹界！雷达开启像素级扫描 ---")

            # ==================== 尊上无上绝学：36坑视觉收种相对合一大阵 ====================
            blocks = [
                {"start": (155, 530), "name": "左下药田"},
                {"start": (205, 490), "name": "左上药田"},
                {"start": (260, 480), "name": "右上药田"},
                {"start": (265, 520), "name": "右下药田"}
            ]
            dx, dy = 16, 11

            print("\n[+] 诸天至尊：36坑视觉动态收种大阵，轰然起航！！！")

            for b in blocks:
                print(f"[*] 雷达正在死守并锁死：{b['name']}")
                start_x, start_y = b["start"]

                for row in range(3):
                    for col in range(3):
                        click_x = start_x + (col * dx) - (row * dx)
                        click_y = start_y + (row * dy) + (col * dy)

                        print(f"\n    [★] 正在精准对准第 {row*3 + col + 1} 块动态土坑 (坐标: {click_x}, {click_y})")

                        # 第一步：先对这个小土坑狠狠砸下一拳
                        page.mouse.click(click_x, click_y)
                        time.sleep(2.5)

                        # 第二步：情况A - 如果熟了，收割极品青石斛
                        if find_and_click_image(page, "shouhuo_btn.png", confidence=0.8):
                            print("        [+] 拔草成功！收割一株极品青石斛！")
                            time.sleep(3.0)

                            # 地空了，原地再补一拳，重新调出动态种子菜单
                            page.mouse.click(click_x, click_y)
                            time.sleep(2.5)

                        # 第三步：情况B - 将当前坑位的绝对坐标传进去，进行【动态相对翻页寻种】
                        if find_seed_by_relative_flipping(page, click_x, click_y):
                            print("        [+] 播种成功！全新青石斛已入土安家！")
                            time.sleep(2.0)
                        else:
                            print("        [-] 警告：动态翻遍3页未能找到种子，可能种子彻底耗尽！")

                        # 安全机制：点一下最上方绝对空白处清场弹窗，并重置下一次菜单
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
