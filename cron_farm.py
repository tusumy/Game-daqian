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

            # === 【特殊判定 1】：如果迷路掉进了“支付宝游戏中心”主页 ===
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

            # === 动作 3：无情锄地与精细化【青石斛】种植 ===
            print("--- 成功进入丹界，开启高级雷达扫描 ---")
            
            # 药田地块的相对中心坐标（基于 450x850 分辨率）
            # 这里的坐标刚好覆盖你药田中间的一圈地块块
            grid_coords = [
                (225, 480), (170, 520), (280, 520), 
                (225, 560), (170, 600), (280, 600)
            ]
            
            for idx, (x, y) in enumerate(grid_coords):
                print(f"\n[*] 正在打理第 {idx+1} 块菜地 (坐标: {x}, {y})...")
                page.mouse.click(x, y) # 邦的一拳，激活地块
                time.sleep(1.5) # 等待弹窗加载
                
                # 情况 A：如果地里有熟了的菜，匹配你切的这幅带小手的收获图
                # 图片文件名请严格命名为：shouhuo_btn.png
                if find_and_click_image(page, "shouhuo_btn.png", confidence=0.8):
                    print("[+] 视觉发现【收获】图标，仙草已顺利入库！")
                    time.sleep(2) # 等待收获动画演完
                    
                    # 收完之后地变空了，原地再补一拳，把种子弹窗打出来
                    page.mouse.click(x, y)
                    time.sleep(1.5)
                
                # 情况 B：此时或者原本就是空地，会显示选择种子弹窗，匹配你切的【青石斛】图
                # 图片文件名请严格命名为：seed_btn.png
                if find_and_click_image(page, "seed_btn.png", confidence=0.8):
                    print("[+] 视觉发现【青石斛】种子，已成功播种！")
                    time.sleep(1.5) # 等待种植完成
                else:
                    print("[-] 没有在这个地块识别到【青石斛】。可能菜还没熟，或者卡了。")
                    # 点一下屏幕最上方的空白处 (225, 50)，强行把可能卡住的弹窗关掉，防止影响下一个格子
                    page.mouse.click(225, 50)
                    time.sleep(1)

            print("--- 药田日常打理完毕，退出登录 ---")