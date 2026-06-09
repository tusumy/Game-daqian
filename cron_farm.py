import cv2
import numpy as np
import time
from playwright.sync_api import sync_playwright

def find_and_click_image(page, template_path, confidence=0.8):
    """
    【无上雷达】：用OpenCV在当前游戏视口中寻找指定的切图（比如全屏按钮、收获、种子）
    找到了就直接狠狠戳它的中心点。
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
        print(f"[-] 雷达扫描遇到法则干扰: {e}")
    return False

def run():
    with sync_playwright() as p:
        # 1. 模拟一个标准的凡间手机大视口
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 800, "height": 900})
        
        print("[+] 正在破空开辟修仙通道，目标：寻道大千网页盒子...")
        page.goto("https://www.wanyiwan.top/game/xddq")
        time.sleep(15)  # 网页首次加载极慢，本尊多给它留足 15 秒灵力！

        try:
            # ==================== 步法一：尊上绝学·物理右滑大撕裂 ====================
            print("\n[★] 步骤一：初始状态看不见全屏！启动【物理鼠标按住左滑】秘术...")
            
            # 模拟手指按住屏幕右侧 (700, 300) 的位置，然后狠狠往左拖动到 (200, 300)
            # 这样就能把隐藏在右边屏幕外的【全屏】区域给强行拽进来！
            page.mouse.move(700, 300)
            page.mouse.down()
            page.mouse.move(200, 300, steps=20)  # 平滑拖拽，防止天道识别为妖法
            page.mouse.up()
            print("    [+] 屏幕已向右划拉完毕！隐藏区域已显形！")
            time.sleep(2.0)

            # 现在的视口里绝对能看见“全屏”了！立刻调用雷达捕捉！
            # ⚠️ 注意：你需要在本地准备一张截图，切下那个写着“全屏”两个字的小方块，命名为 'fullscreen_btn.png'
            print("[★] 步骤二：雷达开始锁定【全屏】图腾...")
            if find_and_click_image(page, "fullscreen_btn.png", confidence=0.8):
                print("    [+] 成功戳中【全屏】按钮！画面已铺满，进入绝对固定纯净模式！")
                time.sleep(6.0)  # 等待全屏重绘
            else:
                print("    [-] 警告：右滑后雷达仍未捕捉到‘全屏’图腾！启动无上盲戳机制...")
                # 根据你第二张图的比例，全屏按钮在全屏前的相对盲戳位置大概在 (320, 290) 附近
                page.mouse.click(320, 290)
                time.sleep(6.0)

            # ------------------------------------------------------------------
            # ⚠️ 此时整个世界彻底清净了！游戏已经全屏！
            # 请在这里继续写你点进“丹界药田”的死坐标或者视觉逻辑
            print("[+] 正在穿过登录大阵，进入丹界深处...")
            time.sleep(5.0) 
            # ------------------------------------------------------------------

            # ==================== 步法三：36坑视觉收种无上大阵 ====================
            blocks = [
                {"start": (155, 530), "name": "左下药田"},
                {"start": (205, 490), "name": "左上药田"},
                {"start": (260, 480), "name": "右上药田"},
                {"start": (265, 520), "name": "右下药田"}
            ]
            dx, dy = 16, 11

            print("\n[+] 诸天至尊：三十六天罡视觉动态收种大阵，轰然起航！！！")

            for b in blocks:
                print(f"[*] 当前死守药田：{b['name']}")
                start_x, start_y = b["start"]

                for row in range(3):
                    for col in range(3):
                        click_x = start_x + (col * dx) - (row * dx)
                        click_y = start_y + (row * dy) + (col * dy)

                        print(f"    [坑位定位] 瞄准第 {row*3 + col + 1} 块土坑 (坐标: {click_x}, {click_y})")

                        # 一拳砸向土坑
                        page.mouse.click(click_x, click_y)
                        time.sleep(2.5)

                        # 情况A：如果熟了，收割
                        if find_and_click_image(page, "shouhuo_btn.png", confidence=0.8):
                            print("        [+] 拔草成功！收割一株极品青石斛！")
                            time.sleep(3.0)
                            # 原地补一拳，调出种子菜单
                            page.mouse.click(click_x, click_y)
                            time.sleep(2.5)

                        # 情况B：种菜 + 动态相对翻页
                        if find_and_click_image(page, "qingshihu_seed.png", confidence=0.8):
                            print("        [+] 播种成功！全新青石斛已入土安家！")
                            time.sleep(2.0)
                        else:
                            print("        [-] 第一页未见种子，尝试点击右侧相对翻页箭头...")
                            page.mouse.click(click_x + 120, click_y + 40)
                            time.sleep(1.5)
                            if find_and_click_image(page, "qingshihu_seed.png", confidence=0.8):
                                print("        [+] 翻页后播种成功！")
                                time.sleep(2.0)
                            else:
                                print("        [-] 警告：此坑可能已种，或种子已耗尽！")

                        # 安全机制
                        page.mouse.click(200, 30)
                        time.sleep(1.5)

            print("\n[+] --- 三十六块药田全部打理完毕，功成身退！ ---")

        except Exception as e:
            print(f"!!! 渡劫暴毙，原因: {e}")
            page.screenshot(path="failed_scene.png")
            print("[*] 罪证已拍下 `failed_scene.png`")
        finally:
            browser.close()

if __name__ == "__main__":
    run()