            # === 动作 3：无情锄地与精细化【青石斛】种植 ===
            print("--- 成功进入丹界，开始高级雷达扫描 ---")
            
            # 这里是你药田里几块地的大概中心坐标（基于450x850分辨率）
            # 我们可以直接用盲点把这几块地激活，看它弹出来的是什么
            grid_coords = [
                (225, 480), (170, 520), (280, 520), 
                (225, 560), (170, 600), (280, 600)
            ]
            
            for idx, (x, y) in enumerate(grid_coords):
                print(f"\n[*] 正在检查第 {idx+1} 块菜地 (坐标: {x}, {y})...")
                page.mouse.click(x, y) # 邦的一拳，点一下地块
                time.sleep(1.5) # 等弹窗
                
                # 情况 A：如果地里有熟了的菜，会弹出“收取”按钮
                if find_and_click_image(page, "shouqu_btn.png", confidence=0.8):
                    print("[+] 视觉发现【收取】按钮，菜已收割！")
                    time.sleep(2) # 等收完动画
                    
                    # 收完之后地就空了，再次点击这块地，让它弹出种子的弹窗
                    page.mouse.click(x, y)
                    time.sleep(1.5)
                
                # 情况 B：此时或者原本就是空地，会显示选择种子弹窗，我们寻找【青石斛】
                if find_and_click_image(page, "seed_btn.png", confidence=0.8):
                    print("[+] 视觉发现【青石斛】种子，已成功种下！")
                    time.sleep(1.5)
                else:
                    print("[-] 没有识别到【青石斛】按钮。可能地里菜还没熟，或者卡了。")
                    # 点一下屏幕最上方的空白处 (比如 225, 50)，强行关闭可能存在的弹窗，防止卡死下一次循环
                    page.mouse.click(225, 50)
                    time.sleep(1)

            print("--- 药田日常打理完毕，退出登录 ---")
