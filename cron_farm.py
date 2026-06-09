import os
import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 1. 如果你上传了 auth.json，长工会带着它投胎
        if os.path.exists("auth.json"):
            print("[+] 侦测到 auth.json，正在注入神识状态...")
            context = browser.new_context(
                viewport={"width": 800, "height": 900},
                storage_state="auth.json"
            )
        else:
            print("[-] 未找到 auth.json，长工以白丁之身前往...")
            context = browser.new_context(viewport={"width": 800, "height": 900})
            
        page = context.new_page()
        print("[+] 正在破空开辟通道，目标：寻道大千...")
        page.goto("https://www.wanyiwan.top/game/xddq")
        
        # 给足 15 秒让它加载！
        print("[*] 正在等待秘境加载完毕（15秒）...")
        time.sleep(15)
        
        try:
            # 【抓拍现场一】：刚进游戏时的第一画面（看看它到底有没有自动登录成功！）
            print("[★] 正在抓拍初始画面...")
            page.screenshot(path="01_initial_scene.png")
            print("    [+] 初始画面已拍下：01_initial_scene.png")
            
            # 执行物理右滑
            print("[★] 正在执行物理解锁（右滑）...")
            page.mouse.move(700, 300)
            page.mouse.down()
            page.mouse.move(200, 300, steps=20)
            page.mouse.up()
            time.sleep(3.0)
            
            # 【抓拍现场二】：右滑之后的画面（看看全屏按钮到底露出来没有！）
            print("[★] 正在抓拍右滑后的画面...")
            page.screenshot(path="02_after_slide_scene.png")
            print("    [+] 右滑画面已拍下：02_after_slide_scene.png")
            
            print("\n[+] --- 摄魂大阵打理完毕，两张罪证已拍下，请去 GitHub 产物里查收 ---")
            
        except Exception as e:
            print(f"!!! 摄魂失败: {e}")
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    run()
