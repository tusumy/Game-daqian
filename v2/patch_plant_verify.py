from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

marker = '"action":"one_plant_verified"'
m = s.find(marker)
if m < 0:
    raise SystemExit("one_plant_verified marker not found")

start = s.rfind("            after=screenshot_img(page)\n", 0, m)
end = s.find("            planted+=1\n", m)
if start < 0 or end < 0:
    raise SystemExit("plant verification block not found")

replacement = r'''            after=screenshot_img(page)
            after_tan=tan_score_at(after,x,y)
            events.append({"t":round(time.time(),2),"action":"one_plant_visual_after_choice",
                           "plant_no":planted+1,
                           "x":round(x,1),"y":round(y,1),
                           "before_tan":round(before_tan,3),
                           "after_tan":round(after_tan,3)})
            print("[VISION]",events[-1],flush=True)

            # 不再用“棕色下降多少”作为最终裁判。小苗很小时地块仍会大面积露出棕色，
            # #93/#94 都已经截图证明“苗种出来了但颜色阈值误判失败”。
            # 重新点击同一地块：有植物会打开“浇水/锄除”管理面板；
            # 真空地才会重新打开选种面板。直接让游戏自己的 UI 判断是否已占用。
            page.mouse.click(x,y)
            time.sleep(1.2)
            verify=screenshot_img(page)
            occupied=management_panel_present(verify)
            still_empty=plant_panel_present(verify)
            events.append({"t":round(time.time(),2),"action":"plant_reprobe_verify",
                           "plant_no":planted+1,
                           "x":round(x,1),"y":round(y,1),
                           "management_panel":bool(occupied),
                           "plant_panel":bool(still_empty),
                           "before_tan":round(before_tan,3),
                           "after_tan":round(after_tan,3)})
            print("[VISION]",events[-1],flush=True)

            if not occupied:
                page.screenshot(path=str(OUT/"plant_verify_failed.png"),full_page=True)
                if still_empty:
                    page.mouse.click(470,430)
                    time.sleep(0.5)
                raise RuntimeError(
                    f"第 {planted+1} 块补种未通过地块回点验证："
                    f"management={occupied} plant_panel={still_empty} "
                    f"tan {before_tan:.2f}->{after_tan:.2f}"
                )

            # 已确认有植物，关闭管理面板后继续下一块。
            page.mouse.click(470,430)
            time.sleep(0.6)

'''

s = s[:start] + replacement + s[end:]
p.write_text(s, encoding="utf-8")
print("patched plant verification to game-UI reprobe oracle")
