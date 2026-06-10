import cv2
import numpy as np
import time
import os
import json
from playwright.sync_api import sync_playwright

def find_image_center(page, template_path, confidence=0.7):
    """【真视雷达】：只寻找图腾的中心坐标 (X, Y)，绝不盲点"""
    try:
        screenshot_bytes = page.screenshot()
        nparr = np.frombuffer(screenshot_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if img is None or template is None: return None
        res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val >= confidence:
            h, w, _ = template.shape
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return (center_x, center_y)
    except:
        pass
    return None

def find_and_click_image(page, template_path, confidence=0.75):
    """【无上砸拳】"""
    center = find_image_center(page, template_path, confidence)
    if center:
        page.mouse.click(center[0], center[1])
        return True
    return False

def image_exists(page, template_path, confidence=0.75):
    """【真视之眼】"""
    return find_image_center(page, template_path, confidence) is not None

def auto_wait_and_click(page, img_name, timeout=15, desc=""):
    """【死等法轨】"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if find_and_click_image(page, img_name):
            time.sleep(2.5)
            return True
        time.sleep(1.2)
    return False

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 800, "height": 900})
        
        if os.path.exists("auth.json"):
            try:
                with open("auth.json", "r", encoding="utf-8") as f: json.load(f)
                context = browser.new_context(viewport={"width": 800, "height": 900}, storage_state="auth.json")
            except: pass
            
        page = context.new_page()
        page.goto("https://www.wanyiwan.top/game/xddq")
        time.sleep(15)

        try:
            # === 第一步：遵循小仙神谕，右滑清场 ===
            page.mouse.move(750, 300)
            page.mouse.down()
            page.mouse.move(150, 300, steps=30)
            page.mouse.up()
            time.sleep(3.0)

            # 盲砸空白处超度公告
            page.mouse.click(100, 750)
            time.sleep(1.5)
            find_and_click_image(page, "close_notice.png")
            time.sleep(2.5)

            # === 第二步：无缝导航杀进丹界 ===
            auto_wait_and_click(page, "enter_game_btn.png", timeout=12, desc="踏入仙途")
            auto_wait_and_click(page, "dongfu_btn.png", timeout=15, desc="洞府")
            auto_wait_and_click(page, "danjie_btn.png", timeout=15, desc="丹界药田")
            time.sleep(5.0)

            # === 🔥 第三步：【图腾定位流】三十六天罡绝不落空大阵 ===
            # 明天记得把这四块大药田的名字对齐切图哦！
            farm_blocks = [
                {"img": "block_1.png", "name": "左下药田"},
                {"img": "block_2.png", "name": "左上药田"},
                {"img": "block_3.png", "name": "右上药田"},
                {"img": "block_4.png", "name": "右下药田"}
            ]
            
            # 菱形格子的相对偏移间距（像素级别微调）
            dx, dy = 16, 11

            print("\n[★] 诸天至尊：【像素锁定·绝对命中流】收种大阵，起！！！")
            for b in farm_blocks:
                print(f"[*] 雷达正在全屏动态搜寻：【{b['name']}】的基准图腾...")
                
                # 动态寻找这块药田在当前屏幕上的真实中心坐标！
                center_coord = find_image_center(page, b["img"], confidence=0.7)
                
                if center_coord is None:
                    print(f"    [-] 警告：屏幕上没抓到【{b['name']}】的切图，可能长着菜遮住了。换个低配盲戳兜底...")
                    # 盲戳兜底坐标，防止彻底卡死
                    if b["name"] == "左下药田": center_coord = (155, 530)
                    elif b["name"] == "左上药田": center_coord = (205, 490)
                    elif b["name"] == "右上药田": center_coord = (260, 480)
                    else: center_coord = (265, 520)

                # 拿到了绝对不会偏的中心坐标，开始衍生3x3九个格子！
                base_x, base_y = center_coord
                print(f"    [+] 基准坐标锁定成功：({base_x}, {base_y})。开始挨个收拾九层地块...")

                for row in range(3):
                    for col in range(3):
                        # 以找到的实体大土块为轴心进行菱形偏移
                        click_x = base_x + (col * dx) - (row * dx)
                        click_y = base_y + (row * dy) + (col * dy)

                        # 狠狠戳下去
                        page.mouse.click(click_x, click_y)
                        time.sleep(2.0)

                        # 如果熟了就拔草
                        if find_and_click_image(page, "shouhuo_btn.png", confidence=0.8):
                            print("        [+] 抓到熟透的青石斛，收割！")
                            time.sleep(2.5)
                            page.mouse.click(click_x, click_y) # 重新戳开
                            time.sleep(2.0)

                        # 判断是不是空地
                        if image_exists(page, "search_bar.png", confidence=0.75):
                            find_and_click_image(page, "search_bar.png", confidence=0.75)
                            time.sleep(1.0)
                            page.keyboard.type("青石斛")
                            time.sleep(1.5)

                            if find_and_click_image(page, "qingshihu_seed.png", confidence=0.8):
                                print("        [+] 绝对命中！播种成功！")
                            else:
                                page.mouse.click(click_x, click_y - 60)
                            time.sleep(2.0)
                        else:
                            print("        [-] 地里长着活菜呢，不打扰，跳过...")

                        # 每次点完清场时间窗
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