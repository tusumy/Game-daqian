from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

# patch_panel_fix.py 会在 farm_plot_centers 前注入最终覆盖版的
# plant_panel_present / management_panel_present / vip_monthly_warning_present。
# 文件里还保留更早的旧 plant_panel_present，同名函数不能用 find() 抓第一处。
end_cls = s.find("def vip_monthly_warning_present(img):")
if end_cls < 0:
    raise SystemExit("final vip_monthly_warning_present not found; run patch_panel_fix.py first")
start_cls = s.rfind("def plant_panel_present(img):", 0, end_cls)
if start_cls < 0:
    raise SystemExit("final plant_panel_present not found before vip classifier")

classifiers = r'''def plant_panel_present(img):
    # 真正的选种面板顶部固定有一对并排标签：
    # 左侧黄色“灵植”，右侧青绿色“造化灵植”。
    # #97 证明仅看右侧青绿色会把管理面板上方的绿色植物状态条误认成选种面板，
    # 因此现在必须同时命中左黄 + 右青两块大标签。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    left=hsv[535:585,245:385]
    right=hsv[535:585,370:515]
    if left.size == 0 or right.size == 0:
        return False

    yellow=cv2.inRange(left,np.array([15,80,170]),np.array([35,255,255]))
    teal=cv2.inRange(right,np.array([75,50,90]),np.array([110,220,230]))
    yellow_frac=cv2.countNonZero(yellow)/float(yellow.shape[0]*yellow.shape[1])
    teal_frac=cv2.countNonZero(teal)/float(teal.shape[0]*teal.shape[1])
    return yellow_frac >= 0.35 and teal_frac >= 0.35


def management_panel_present(img):
    # “浇水/锄除”管理面板会随地块上下移动。
    # 先排除真正的双标签选种面板，再认其宽大的深色操作区。
    if plant_panel_present(img):
        return False
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=240,560,700,860
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

            # 重新点击同一地块，让游戏 UI 自己判断是否已占用：
            # 有植物 -> 浇水/锄除管理面板；真空地 -> 重新打开选种面板。
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

            page.mouse.click(470,430)
            time.sleep(0.6)

'''

s = s[:start] + replacement + s[end:]
p.write_text(s, encoding="utf-8")
print("patched dual-tab plant classifier + management panel classifier + reprobe oracle")
