from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

# 丹界入口右移，避开偶发覆盖在卡片中央的黄色引导手。
s = s.replace("return (575.0,785.0,lf,rf)", "return (625.0,785.0,lf,rf)")

# 新活动“仙阁雅宴”这类覆盖层没有关闭 X，只有中央橙色“前往”。
# 单独识别这个固定按钮；进入活动页后马上用已有的严格左上返回箭头退回。
helper_anchor = "def today_no_remind_point(img):"
helper = r'''def forward_only_event_button(img):
    # 仅识别游戏画面下部中央那枚“前往”橙色按钮。
    # 当前仙阁雅宴按钮中心约 (470,787)，与“感悟升级”的左取消按钮位置明显不同。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=385,755,555,820
    roi=hsv[y0:y1,x0:x1]
    if roi.size == 0:
        return None
    orange=cv2.inRange(roi,np.array([0,80,100]),np.array([30,255,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(orange)
    best=None
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
        if area < 1200 or not (85 <= w <= 155 and 24 <= h <= 55):
            continue
        if not (435 <= cx <= 510 and 772 <= cy <= 808):
            continue
        if best is None or area > best[0]:
            best=(area,(cx,cy))
    return best[1] if best else None


'''
if "def forward_only_event_button(img):" not in s:
    if helper_anchor not in s:
        raise SystemExit("today_no_remind_point anchor not found")
    s=s.replace(helper_anchor,helper+helper_anchor,1)

handler_anchor = '                    # 每日活动弹窗：勾“今日不再提示”后关闭。\n'
handler = r'''                    # “仙阁雅宴”等无关闭 X、只有“前往”的覆盖层。
                    # 不能再让通用 X 把飘动桃花当关闭键；点“前往”后只做一次严格返回。
                    fp=forward_only_event_button(shot)
                    if fp:
                        page.screenshot(path=str(OUT/"forward_only_event_before.png"),full_page=True)
                        page.mouse.click(fp[0],fp[1])
                        events.append({"t":round(time.time(),2),"action":"forward_only_event_enter",
                                       "x":round(fp[0],1),"y":round(fp[1],1)})
                        print("[VISION]",events[-1],flush=True)
                        time.sleep(6)
                        entered=screenshot_img(page)
                        bp=nested_page_back_point(entered)
                        if bp:
                            page.mouse.click(bp[0],bp[1])
                            events.append({"t":round(time.time(),2),"action":"forward_only_event_back",
                                           "x":round(bp[0],1),"y":round(bp[1],1)})
                            print("[VISION]",events[-1],flush=True)
                            time.sleep(5)
                            clean_frames=0
                            continue
                        page.screenshot(path=str(OUT/"forward_only_event_no_back.png"),full_page=True)
                        abort_reason="无关闭 X 活动点前往后未识别到安全返回箭头；已保存现场"
                        break

'''
if "forward_only_event_enter" not in s:
    if handler_anchor not in s:
        raise SystemExit("post-dongfu daily anchor not found")
    s=s.replace(handler_anchor,handler+handler_anchor,1)

start = s.find("def probe_existing_plant(page, events):")
end = s.find("\n\nwith sync_playwright() as p:", start)
if start < 0 or end < 0:
    raise SystemExit("probe_existing_plant block not found")

replacement = r'''def farm_plot_centers():
    # #87 最终药田图校准：36 块地实际组成规则的 6x6 等距网格。
    # 顶点约 (476,486)，两条格轴分别为 (+33,+15) / (-33,+15)。
    # 直接扫真实地块，不再依赖某一种成熟灵植的颜色/白金花点外观。
    base_x,base_y=476.0,486.0
    dx,dy=33.0,15.0
    pts=[]
    for i in range(6):
        for j in range(6):
            pts.append((base_x+dx*(i-j),base_y+dy*(i+j)))
    pts.sort(key=lambda p:(p[1],p[0]))
    return pts


def local_plot_change_score(a,b,x,y):
    x=int(round(x)); y=int(round(y))
    x0=max(0,x-30); x1=min(a.shape[1],x+31)
    y0=max(0,y-38); y1=min(a.shape[0],y+28)
    ra=a[y0:y1,x0:x1]
    rb=b[y0:y1,x0:x1]
    if ra.size == 0 or rb.size == 0 or ra.shape != rb.shape:
        return 999.0
    ga=cv2.cvtColor(ra,cv2.COLOR_BGR2GRAY)
    gb=cv2.cvtColor(rb,cv2.COLOR_BGR2GRAY)
    return float(np.mean(cv2.absdiff(ga,gb)))


def probe_existing_plant(page, events):
    # 新方案：逐格探测 36 个真实地块。
    # 成熟株无论品种外观，只要点击后出现“特权”菜单，就点左侧普通“收获”。
    # 未成熟株通常无菜单；真空地若弹出选种面板，只记录并关闭，最后统一补种。
    harvested=0
    empty_panels=0
    centers=farm_plot_centers()
    page.screenshot(path=str(OUT/"before_grid_harvest.png"),full_page=True)

    events.append({"t":round(time.time(),2),"action":"grid_harvest_start",
                   "plots":len(centers)})
    print("[VISION]",events[-1],flush=True)

    for plot_no,(x,y) in enumerate(centers,start=1):
        before=screenshot_img(page)
        page.mouse.click(x,y)
        events.append({"t":round(time.time(),2),"action":"grid_plot_probe",
                       "plot_no":plot_no,"x":round(x,1),"y":round(y,1)})
        print("[VISION]",events[-1],flush=True)
        time.sleep(0.9)

        opened=screenshot_img(page)
        hp=harvest_popup_point(opened)
        if hp:
            hx=float(hp[0]); hy=float(hp[1])
            page.mouse.click(hx,hy)
            time.sleep(1.8)

            after=screenshot_img(page)
            still_open=harvest_popup_point(after) is not None
            if still_open:
                time.sleep(1.2)
                after=screenshot_img(page)
                still_open=harvest_popup_point(after) is not None

            change=local_plot_change_score(before,after,x,y)
            events.append({"t":round(time.time(),2),"action":"grid_harvest_verified",
                           "plot_no":plot_no,"harvest_no":harvested+1,
                           "x":round(x,1),"y":round(y,1),
                           "menu_closed":not still_open,
                           "local_change":round(change,2)})
            print("[VISION]",events[-1],flush=True)

            if still_open:
                page.screenshot(path=str(OUT/"grid_harvest_menu_stuck.png"),full_page=True)
                raise RuntimeError(f"第 {plot_no} 块点击普通收获后特权菜单仍未关闭")

            harvested+=1
            if harvested % 6 == 0:
                page.screenshot(path=str(OUT/f"grid_harvest_progress_{harvested}.png"),full_page=True)
            continue

        # 收获菜单没出现。若这是空地，会打开选种面板；先关掉，全部扫描后再统一种。
        if plant_panel_present(opened):
            empty_panels+=1
            events.append({"t":round(time.time(),2),"action":"grid_plot_empty_panel",
                           "plot_no":plot_no,"x":round(x,1),"y":round(y,1)})
            print("[VISION]",events[-1],flush=True)
            page.mouse.click(470,730)
            time.sleep(0.5)
        else:
            # 未成熟株/不可收状态。点稳定空白处，清掉可能出现的小提示再扫下一格。
            events.append({"t":round(time.time(),2),"action":"grid_plot_not_harvestable",
                           "plot_no":plot_no,"x":round(x,1),"y":round(y,1)})
            print("[VISION]",events[-1],flush=True)
            page.mouse.click(470,730)
            time.sleep(0.35)

    page.screenshot(path=str(OUT/"after_grid_harvest.png"),full_page=True)
    events.append({"t":round(time.time(),2),"action":"full_harvest_summary",
                   "harvested":harvested,"plots_probed":len(centers),
                   "empty_panels_seen":empty_panels,
                   "mode":"grid_6x6"})
    print("[VISION]",events[-1],flush=True)

    probe_one_plant(page,events)
'''

s = s[:start] + replacement + s[end:]
p.write_text(s, encoding="utf-8")
print("patched forward-only event + 6x6 grid harvest + Danjie entry")
