import os
import time
import random
import cv2
import numpy as np
from playwright.sync_api import sync_playwright

def find_and_click_image(page, template_path, confidence=0.8):
    """
    用 OpenCV 在当前游戏画面中寻找指定的切图，找到了就点它中心点
    """
    try:
        screenshot_bytes = page.screenshot()
        nparr = np.frombuffer(screenshot_bytes, np.uint8)
        img_rgb = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        
        template = cv2.imread(template_path, 0)
        if template is None:
            print(f"[-] 找不到素材图片: {template_path}")
            return False
            
        w, h = template.shape[::-1]
        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= confidence)
        points = list(zip(*loc[::-1]))
        
        if points:
            pt = points[0]
            click_x = pt[0] + w // 2
            click_y = pt[1] + h // 2
            print(f"[+] 视觉识别成功：发现 {template_path}，执行点击 ({click_x}, {click_y})")
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
        WIDTH, HEIGHT = 450, 850
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": WIDTH, "height": HEIGHT})
        page = context.new_page()
        
        print("--- 大佬别慌，AI 抗卡顿战机已起飞 ---")
        try:
            # 1. 进网址，给足 30 秒等基础网络响应
            page.goto(game_url, wait_until="networkidle", timeout=90000)
            print("[*] 正在注入灵力，死等网页基础加载 (30秒)...")
            time.sleep(30)

            # === 【防迷路】游戏中心判定 ===
            if "游戏中心" in page.title() or page.locator("text='寻道大千'").is_visible(timeout=5000):
                print("[!] 误入游戏中心，强行修正中...")
                try:
                    page.locator("text='寻道大千'").first.click()
                    time.sleep(15)
                except:
                    page.mouse.click(225, 300) 
                    time.sleep(15)

            # === 【核心防卡】踏入仙途 ===
            print("[*] 正在跨越【踏入仙途】大门...")
            tr_x, tr_y = int(WIDTH * 0.5), int(HEIGHT * 0.75)
            # 疯狂连点 3 下，彻底击碎网络延迟
            for _ in range(3):
                page.mouse.click(tr_x, tr_y)
                time.sleep(1.5)
            
            # 核心痛点：进入主界面加载极慢，这次给足 35 秒死等！
            print("[*] 大门已开！正在拼命加载游戏主界面数据 (死等 35秒)...")
            time.sleep(35) 

            # === 动作 1：点击主界面左下角的“洞府” ===
            df_x, df_y = int(WIDTH * 0.26), int(HEIGHT * 0.94)
            print("-> 正在戳【洞府】按钮...")
            page.mouse.click(df_x, df_y)
            time.sleep(5) # 提高容错，等弹出菜单完全展开

            # === 动作 2：点击弹窗右下角的“丹界” ===
            dj_x, dj_y = int(WIDTH * 0.75), int(HEIGHT * 0.68)
            print("-> 正在戳【丹界】传送阵...")
            page.mouse.click(dj_x, dj_y)
            print("[*] 正在穿越至丹界药田 (死等 10秒让地块加载)...")
            time.sleep(10) # 药田加载很耗时，给足10秒！

            # === 动作 3：无情锄地与【青石斛】精细化种植 ===
            print("--- 成功着陆丹界！雷达开启像素级扫描 ---")
            
            # 药田 6 块地的黄金相对中心坐标
            grid_coords = [
                (225, 480), (170, 520), (280, 520), 
                (225, 560), (170, 600), (280, 600)
            ]
            
            for idx, (x, y) in enumerate(grid_coords):
                print(f"\n[*] 雷达对准第 {idx+1} 块菜地 ({x}, {y})")
                page.mouse.click(x, y) 
                time.sleep(2.5) # 给地块弹窗预留充足时间
                
                # 情况 A：如果熟了，抓取“收获”小手
                if find_and_click_image(page, "shouhuo_btn.png", confidence=0.8):
                    print("[+] 拔草成功！")
                    time.sleep(3) # 等收割动画彻底播完
                    
                    # 地空了，原地再补一拳调出种子菜单
                    page.mouse.click(x, y)
                    time.sleep(2.5)
                
                # 情况 B：如果是空地，寻找【青石斛】并种下
                if find_and_click_image(page, "seed_btn.png", confidence=0.8):
                    print("[+] 成功种下【青石斛】！")
                    time.sleep(2.5) 
                else:
                    print("[-] 未发现可种状态（可能菜未熟、或种子耗尽）。")
                    # 安全机制：点一下最上方空白处关闭可能残存的弹窗，防止卡死下一个格子
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
