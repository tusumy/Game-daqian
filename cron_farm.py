def run():
    with sync_playwright() as p:
        # 改：关闭无头模式，方便观察
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 800, "height": 900})

        if os.path.exists("auth.json"):
            try:
                with open("auth.json", "r", encoding="utf-8") as f:
                    json.load(f)
                context = browser.new_context(
                    viewport={"width": 800, "height": 900},
                    storage_state="auth.json"
                )
            except:
                pass

        page = context.new_page()
        page.goto("https://www.wanyiwan.top/game/xddq")
        time.sleep(15)

        # === 【新】加入视口强制对齐 ===
        # 强制重置滚动，保证坐标系与截图环境一致
        page.evaluate("window.scrollTo(0, 0)")
        page.mouse.move(0, 0)
        time.sleep(1.0)

        try:
            # === 第一步：右滑清场 + 关闭公告 ===
            page.mouse.move(750, 300)
            page.mouse.down()
            page.mouse.move(150, 300, steps=30)
            page.mouse.up()
            time.sleep(3.0)

            page.mouse.click(100, 750)
            time.sleep(1.5)
            find_and_click_image(page, "close_notice.png")
            time.sleep(2.5)

            # === 第二步：导航进丹界 ===
            auto_wait_and_click(page, "enter_game_btn.png", timeout=12, desc="踏入仙途")
            auto_wait_and_click(page, "dongfu_btn.png", timeout=15, desc="洞府")
            auto_wait_and_click(page, "danjie_btn.png", timeout=15, desc="丹界药田")
            time.sleep(5.0)

            # === 第三步：药田大阵（相对偏移逻辑不变） ===
            farm_blocks = [
                {"img": "block_1.png", "name": "左下药田"},
                {"img": "block_2.png", "name": "左上药田"},
                {"img": "block_3.png", "name": "右上药田"},
                {"img": "block_4.png", "name": "右下药田"}
            ]

            dx, dy = 16, 11

            print("\n[★] 诸天至尊：【像素锁定·绝对命中流】收种大阵，起！！！")
            for b in farm_blocks:
                print(f"[*] 雷达正在全屏动态搜寻：【{b['name']}】的基准图腾...")
                center_coord = find_image_center(page, b["img"], confidence=0.7)

                if center_coord is None:
                    print(f"    [-] 警告：屏幕上没抓到【{b['name']}】的切图，使用兜底坐标...")
                    if b["name"] == "左下药田":
                        center_coord = (155, 530)
                    elif b["name"] == "左上药田":
                        center_coord = (205, 490)
                    elif b["name"] == "右上药田":
                        center_coord = (260, 480)
                    else:
                        center_coord = (265, 520)

                base_x, base_y = center_coord
                print(f"    [+] 基准坐标锁定成功：({base_x}, {base_y})。开始挨个收拾九层地块...")

                for row in range(3):
                    for col in range(3):
                        click_x = base_x + (col * dx) - (row * dx)
                        click_y = base_y + (row * dy) + (col * dy)

                        page.mouse.click(click_x, click_y)
                        time.sleep(2.0)

                        if find_and_click_image(page, "shouhuo_btn.png", confidence=0.8):
                            print("        [+] 抓到熟透的青石斛，收割！")
                            time.sleep(2.5)
                            page.mouse.click(click_x, click_y)
                            time.sleep(2.0)

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

                        page.mouse.click(200, 30)
                        time.sleep(1.2)

            print("\n[+] --- 诸天药田【绝对命中流】大阵全部圆满功成！！！ ---")

        except Exception as e:
            print(f"!!! 阵法阻碍: {e}")
            page.screenshot(path="error_scene.png")
        finally:
            browser.close()