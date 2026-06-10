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

def image_exists(page, template_path, confidence=0.75):
    """【真视之眼】：只看当前画面里到底有没有这个图腾，绝不瞎戳"""
    try:
        screenshot_bytes = page.screenshot()
        nparr = np.frombuffer(screenshot_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if img is None or template is None: return False
        res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        return max_val >= confidence
    except:
        return False

def auto_wait_and_click(page, img_name, timeout=15, desc=""):
    """【死等法轨】：苦苦等待路标出现并破开它"""
    print(f"[*] 寻路雷达：正在搜寻【{desc}】路标...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if find_and_click_image(page, img_name):
            print(f"    [+] 成功破开路标：【{desc}】！")
            time.sleep(2.5)
            return True
        time.sleep(1.2)
    print(f"    [-] 警告：超时未见【{desc}】，尝试盲破或执行下一步...")
    return False

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 建立黄金手机视口画布 (800x900)
        context_args = {"viewport": {"width": 800, "height": 900}}
        if os.path.exists("auth.json"):
            try:
                with open("auth.json", "r", encoding="utf-8") as f: json.load(f)
                context_args["storage_state"] = "auth.json"
                print("[+] 成功载入免扫码神识，长工空降大千世界...")
            except:
                pass
        
        context = browser.new_context(**context_args)
        page = context.new_page()
        page.goto("https://www.wanyiwan.top/game/xddq")
        print("[*] 正在开辟修仙通道，等待天地重绘 15 秒...")
        time.sleep(15)

        try:
            # === 🔥 小仙神谕第一步：按住右侧，狠狠向左拉动，展露完美初始画布 ===
            print("\n[★] 步骤一：物理右滑拉出全景（绝不点全屏按钮）...")
            page.mouse.move(750, 300)
            page.mouse.down()
            page.mouse.move(150, 300, steps=30)
            page.mouse.up()
            time.sleep(3.0)

            # === 🔥 小仙神谕第二步：在最完美的初始画面上，点空白处直接把公告给点掉 ===
            print("[★] 步骤二：在左下方大虚空空白处砸下盲拳，超度公告弹窗...")
            page.mouse.click(100, 750) # 狠狠戳一下左下角的安全空白区，震碎公告
            time.sleep(1.5)
            # 兜底雷达：万一没震碎，再用切图补一刀
            find_and_click_image(page, "close_notice.png")
            time.sleep(2.5)

            # === 🔥 小仙神谕第三步：直接在当前最稳固的初始比例下，一路寻路杀进丹界 ===
            print("\n[★] 步骤三：雷达全自动无缝导航大阵，启动！")
            auto_wait_and_click(page, "enter_game_btn.png", timeout=12, desc="踏入仙途按钮")
            auto_wait_and_click(page, "dongfu_btn.png", timeout=15, desc="主界面·洞府图标")
            auto_wait_and_click(page, "danjie_btn.png", timeout=15, desc="洞府内部·丹界药田")
            
            # 拍下一张现场实景，供小仙明日查账
            page.screenshot(path="current_danjie_scene.png")
            print("[+] 奇迹！长工已在最稳固的手机初始画面下，成功空降药田核心！")
            time.sleep(4.0)

            # === 第四步：三十六天罡【自适应绕开活菜】收种大阵 ===
            # 基于初始无全屏画面下的四个大土块起点（长工会自己微调）
            blocks = [
                {"start": (155, 530), "name": "左下药田"},
                {"start": (205, 490), "name": "左上药田"},
                {"start": (260, 480), "name": "右上药田"},
                {"start": (265, 520), "name": "右下药田"}
            ]
            dx, dy = 16, 11

            print("\n[★] 诸天至尊：智能自适应【手机初始比例·搜索流】收种大阵，起！！！")
            for b in blocks:
                print(f"[*] 当前死守药田：{b['name']}")
                start_x, start_y = b["start"]
                for row in range(3):
                    for col in range(3):
                        click_x = start_x + (col * dx) - (row * dx)
                        click_y = start_y + (row * dy) + (col * dy)

                        # 1. 狠狠戳向地块
                        page.mouse.click(click_x, click_y)
                        time.sleep(2.0)

                        # 2. 如果熟了，立马拔草
                        if find_and_click_image(page, "shouhuo_btn.png", confidence=0.8):
                            print("        [+] 拔草成功！收割一株极品青石斛！")
                            time.sleep(2.5)
                            page.mouse.click(click_x, click_y) # 重新点开这块空地
                            time.sleep(2.0)

                        # 3. 🚨【小仙自愈判定】：看看到底是不是空地？
                        # 如果是空地，屏幕上必然会露出“search_bar.png（搜索灵植框）”！
                        if image_exists(page, "search_bar.png", confidence=0.75):
                            print("        [+] 确认是空地，施展搜索直达播种神通...")
                            find_and_click_image(page, "search_bar.png", confidence=0.75)
                            time.sleep(1.0)
                            
                            # 注入法力输入青石斛
                            page.keyboard.type("青石斛")
                            time.sleep(1.5)

                            # 认准种子切图点下去
                            if find_and_click_image(page, "qingshihu_seed.png", confidence=0.8):
                                print("        [+] 搜索流定向播种成功！")
                            else:
                                page.mouse.click(click_x, click_y - 60) # 兜底盲戳第一个
                            time.sleep(2.0)
                        else:
                            # 🚨 如果既没有收获，也没有弹出搜索框，说明这里长着你之前种的活菜呢！
                            print("        [-] 此地活菜正旺。长工绝不瞎打扰，默默退下...")

                        # 4. 点一下上方虚空（200, 30），无情抽走生长时间弹窗，防止挡住下一块地！
                        page.mouse.click(200, 30)
                        time.sleep(1.2)

            print("\n[+] --- 诸天药田【手机纯净比例】大阵全部圆满功成！！！ ---")

        except Exception as e:
            print(f"!!! 大阵途中遇到阻碍: {e}")
            page.screenshot(path="lost_way_scene.png")
        finally:
            browser.close()

if __name__ == "__main__":
    run()