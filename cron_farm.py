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
            
      # ==================== 尊上无上绝学：36坑视觉收种合一完全体大阵 ====================
    # 1. 测算四大区块的左上角起点坐标与斜 45 度视角步长
    blocks = [
        {"start": (155, 530), "name": "左下药田"},
        {"start": (205, 490), "name": "左上药田"},
        {"start": (260, 480), "name": "右上药田"},
        {"start": (265, 520), "name": "右下药田"}
    ]
    dx, dy = 16, 11  # 像素级黄金步长
    
    print("\n[+] 诸天至尊：36坑视觉收种合一无上大阵，起！！！")
    
    # 2. 四大药田核心大循环
    for b in blocks:
        print(f"[*] 雷达正在死守并锁死：{b['name']}")
        start_x, start_y = b["start"]
        
        # 3. 3x3 矩阵式斜向透视，一个坑位一个坑位地进行深度压榨
        for row in range(3):
            for col in range(3):
                # 完美的 3D 斜角坐标转换，精确定位当前这一个小土坑
                click_x = start_x + (col * dx) - (row * dx)
                click_y = start_y + (row * dy) + (col * dy)
                
                print(f"\n    [★] 正在全神贯注对准第 {row*3 + col + 1} 块小土坑 (坐标: {click_x}, {click_y})")
                
                # 第一步：先对这个小土坑狠狠砸下一拳
                page.mouse.click(click_x, click_y)
                time.sleep(2.5)  # 给地块弹窗预留充足的灵力反应时间
                
                # 第二步：情况A - 如果熟了，调用视觉雷达抓取“收获”小手
                if find_and_click_image(page, "shouhuo_btn.png", confidence=0.8):
                    print("        [+] 拔草成功！收割一株极品青石斛！")
                    time.sleep(3.0)  # 等收割动画彻底播完，免得卡住法轨
                    
                    # 地空了，原地再补一拳，调出种子菜单
                    page.mouse.click(click_x, click_y)
                    time.sleep(2.5)
                
                # 第三步：情况B - 无论原本就是空地，还是刚刚收割完的空地，现在统一开始种菜
                # 调用视觉雷达，寻找并点击你的“青石斛种子”图标
                if find_and_click_image(page, "qingshihu_seed.png", confidence=0.8):
                    print("        [+] 播种成功！全新青石斛已入土安家！")
                    time.sleep(2.0)  # 等待种植动画完成
                else:
                    print("        [-] 警告：未能找到种子，可能此坑已经种过了，或者种子耗尽！")
                    
    print("\n[+] 功德圆满！36块灵田已全部深度扫描并完成收种，无一遗漏！")
    # ===================================================================================
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
