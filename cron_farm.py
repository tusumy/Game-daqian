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
    import time  # 确保最顶上有这行！！！

# ... 前面的代码保持不动，直到你看到 try: 这一行 ...

        try:
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
                        if find_and_click_image(page, "qingshihu_seed.png", confidence=0.8):
                            print("        [+] 播种成功！全新青石斛已入土安家！")
                            time.sleep(2.0)  # 等待种植动画完成
                        else:
                            print("        [-] 警告：未能找到种子，可能此坑已经种过了，或者种子耗尽！")

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
