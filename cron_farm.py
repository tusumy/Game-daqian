import cv2
import numpy as np
import time
from playwright.sync_api import sync_playwright

def find_and_click_image(page, template_path, confidence=0.8):
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
    return False

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 设置一个符合网页版修仙游戏的视口
        page = browser.new_page(viewport={"width": 400, "height": 800})
        
        # 直接访问你给的网页真身！
        page.goto("https://www.wanyiwan.top/game/xddq")
        time.sleep(10) # 给网页加载留足灵气

        try:
            print("[+] 已成功登录网页版修仙秘境！")
            
            # 核心区块定义
            blocks = [(155, 530), (205, 490), (260, 480), (265, 520)]
            
            for start_x, start_y in blocks:
                # 遍历这块田里的坑位
                for i in range(9):
                    # 简单的坐标偏移逻辑
                    cx = start_x + (i % 3) * 16
                    cy = start_y + (i // 3) * 11
                    
                    page.mouse.click(cx, cy)
                    time.sleep(2)
                    
                    if find_and_click_image(page, "shouhuo_btn.png"):
                        time.sleep(2)
                        page.mouse.click(cx, cy)
                        time.sleep(2)
                    
                    # 尝试种菜（若第一页找不到，Playwright 会自动在页面元素里找）
                    if not find_and_click_image(page, "qingshihu_seed.png"):
                         # 简单的翻页逻辑：若找不到，点击页面右侧区域尝试翻页
                         page.mouse.click(350, 450)
                         time.sleep(1)
                         find_and_click_image(page, "qingshihu_seed.png")
                    
                    page.mouse.click(200, 20) # 点击上方空白处重置
                    time.sleep(1)

        except Exception as e:
            print(f"!!! 渡劫失败: {e}")
            page.screenshot(path="failed.png")
        finally:
            browser.close()

if __name__ == "__main__":
    run()