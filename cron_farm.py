import os
import time
import random
import cv2
import numpy as np
from playwright.sync_api import sync_playwright

def find_and_click_image(page, template_path, confidence=0.8):
    """
    大招：用 OpenCV 在当前游戏画面中寻找指定的切图，找到了就点它中心点
    """
    try:
        # 截取当前云端浏览器画面
        screenshot_bytes = page.screenshot()
        nparr = np.frombuffer(screenshot_bytes, np.uint8)
        img_rgb = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        
        # 读取你上传的素材图
        template = cv2.imread(template_path, 0)
        if template is None:
            print(f"[-] 没找到素材图片: {template_path}")
            return False
            
        w, h = template.shape[::-1]
        
        # 像素级模板匹配
        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= confidence)
        points = list(zip(*loc[::-1]))
        
        if points:
            pt = points[0]
            click_x = pt[0] + w // 2
            click_y = pt[1] + h // 2
            print(f"[+] 视觉发现目标 {template_path}，精准坐标: ({click_x}, {click_y})")
            page.mouse.click(click_x, click_y)
            return True
    except Exception as e:
        print(f"[-] 视觉识别出错: {e}")
    return False

def run():
    game_url = os.environ.get("GAME_URL")
    if not game_url:
        print("[-] 错误：GitHub Secrets 中未配置 GAME_URL")
        return

    with sync_playwright() as p:
        # 严格锁定手机版分辨率比例
        WIDTH, HEIGHT = 450, 850
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": WIDTH, "height": HEIGHT})
        page = context.new_page()
        
        print("--- AI 开始硬闯游戏大门 ---")
        try:
            page.goto(game_url, wait_until="networkidle", timeout=60000)
            time.sleep(10)

            # === 【特殊判定 1】：如果迷路掉进了“宝游戏中心”主页 ===
            if "游戏中心" in page.title() or page.locator("text='寻道大千'").is_visible(timeout=3000):
                print("[!] 误入游戏中心，正在强行修正...")
                try:
                    page.locator("text='寻道大千'").first.click()
                    time.sleep(10)
                except:
                    page.mouse.click(225, 300) # 盲点推荐位
                    time.sleep(10)

            # === 【特殊判定 2】：处理“踏入仙途”加载图 ===
            print("[*] 正在通过【踏入仙途】大门...")
            tr_x, tr_y = int(WIDTH * 0.5), int(HEIGHT * 0.75)
            page.mouse.click(tr_x, tr_y)
            time.sleep(2)
            page.mouse.click(tr_x, tr_y) # 补一枪防漏点
            
            print("[*] 正在加载游戏主界面（给服务器 15 秒）...")
            time.sleep(15) 

            # === 动作 1：点击主界面左下角的“洞府” ===
            df_x, df_y = int(WIDTH * 0.26), int(HEIGHT * 0.94)
            print("-> 点击【洞府】...")
            page.mouse.click(df_x, df_y)
            time.sleep(3 + random.random())

            # === 动作 2：点击弹窗右下角的“丹界” ===
            dj_x, dj_y = int(WIDTH * 0.75), int(HEIGHT * 0.68)
            print("-> 点击【丹界】...")
            page.mouse.click(dj_x, dj_y)
            time.sleep(5 + random.random()) # 等药田完全加载出来

            # === 动作 3：视觉流点格子并种下【青石斛】 ===
            print("--- 成功进入丹界，开启雷达扫描 ---")
            
            # 假设你地块多，循环尝试打理 5 次
            for i in range(5):
                # 寻找空地
                if find_and_click_image(page, "empty_grid.png", confidence=0.75):
                    print(f"[+] 成功点击第 {i+1} 块空地，等待种子菜单...")
                    time.sleep(2) # 等选菜弹窗出来
                    
                    # 寻找并点击“青石斛”种子
                    if find_and_click_image(page, "seed_btn.png", confidence=0.8):
                        print(f"[+] 成功种下青石斛！")
                        time.sleep(2) # 等种完关闭弹窗
                    else:
                        print("[-] 弹窗里没找到【青石斛】按钮，可能卡了或种子没了。")
                        # 随便点下旁边关闭弹窗，防止卡死
                        page.mouse.click(int(WIDTH * 0.9), int(HEIGHT * 0.2))
                        time.sleep(1)
                else:
                    print("[*] 扫描完毕，当前没有发现空闲的菜地。")
                    break

            print("--- 药田日常打理完毕，退出登录 ---")

        except Exception as e:
            print(f"!!! 运行异常: {e}")
            page.screenshot(path="failed_scene.png")
            print("[*] 已保存翻车现场截图 `failed_scene.png`")
            
        finally:
            browser.close()

if __name__ == "__main__":
    run()
