from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

# #95 现场证明：靠下地块的“浇水/锄除”管理面板会延伸到 y>740，
# 旧版按固定高度判断会把它误认成选种面板。
# 改用 UI 结构本身：选种面板有宽大的青绿色“造化灵植”标签；
# 管理面板没有该标签，但有一整块宽大的深色操作区。
start_cls = s.find("def plant_panel_present(img):")
end_cls = s.find("def vip_monthly_warning_present(img):", start_cls)
if start_cls < 0 or end_cls < 0:
    raise SystemExit("panel classifier block not found")

classifiers = r'''def plant_panel_present(img):
    # 真正的选种面板固定带有宽大的青绿色“造化灵植”标签，
    # 位置约 x=380..505,y=540..580。背景场景虽也有青绿色，
    # 但不会形成面积>3000、宽>120、高>42 的整块标签。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=360,530,520,595
    roi=hsv[y0:y1,x0:x1]
    if roi.size == 0:
        return False
    teal=cv2.inRange(roi,np.array([70,60,70]),np.array([115,220,220]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(teal)
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
        if area >= 3000 and w >= 120 and h >= 42 and 420 <= cx <= 475 and 545 <= cy <= 582:
            return True
    return False


def management_panel_present(img):
    # “浇水/锄除”管理面板会根据地块上下移动，不能再按固定 y 尾部判断。
    # 它的主体始终是一整块约 460px 宽、120px 以上高的深色操作区。
    # 先排除真正的选种面板，再检测这块大深色连通区域。
    if plant_panel_present(img):
        return False
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=240,600,700,850
    roi=hsv[y0:y1,x0:x1]
    if roi.size == 0:
        return False
    dark=cv2.inRange(roi,np.array([0,0,0]),np.array([180,255,120]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(dark)
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        if area >= 30000 and w >= 380 and h >= 120:
            return True
    return False


'''
s = s[:start_cls] + classifiers + s[end_cls:]

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

            # 不再用“棕色下降多少”作为最终裁判。重新点击同一地块，
            # 让游戏自己的 UI 判断：有植物 -> 浇水/锄除管理面板；
            # 真空地 -> 重新打开选种面板。
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
print("patched structural panel classifiers + game-UI plant reprobe oracle")
