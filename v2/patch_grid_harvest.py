from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

# 丹界入口右移，避开偶发覆盖在卡片中央的黄色引导手。
s = s.replace("return (575.0,785.0,lf,rf)", "return (625.0,785.0,lf,rf)")

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
print("patched 6x6 grid harvest + Danjie entry")
