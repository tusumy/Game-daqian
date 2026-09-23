from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

# 最后一层补丁不再依赖前面几个 runtime patch 留下任何药田 helper。
# #101/#103 证明，多个 patch 按文本区间连续替换时，会把夹在
# probe_one_plant 与 farm_plot_centers 之间的收获/面板函数一起吞掉。
# 因此这里直接把 probe_one_plant 到 probe_existing_plant 之间整段重建：
# 面板识别、VIP 保险、普通收获、36 格坐标、补种逻辑一次写全。
start = s.find("def probe_one_plant(page, events):")
end = s.find("def probe_existing_plant(page, events):", start)
if start < 0 or end < 0:
    raise SystemExit("final farm block boundary not found")

final_block = r'''def plant_panel_present(img):
    # 真空地点击后才会出现真正的选种面板：顶部并排的
    # 黄色“灵植” + 青绿色“造化灵植”双标签。
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
    # 已有灵植（包括多波灵植收过一波后的倒计时状态）会出现宽的管理操作区。
    # 先排除真正选种面板。
    if plant_panel_present(img):
        return False
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    roi=hsv[540:850,240:710]
    if roi.size == 0:
        return False
    dark=cv2.inRange(roi,np.array([0,0,0]),np.array([180,255,130]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(dark)
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        if area >= 22000 and w >= 300 and h >= 95:
            return True
    return False


def vip_monthly_warning_present(img):
    # 真正误点右侧 VIP“一键收获”后的月卡弹窗：
    # 游戏画布内大块灰白正文 + 左橙取消 + 右绿确定同时出现。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    body=hsv[430:645,250:690]
    if body.size == 0:
        return False
    pale=cv2.inRange(body,np.array([0,0,145]),np.array([180,100,255]))
    pale_frac=cv2.countNonZero(pale)/float(body.shape[0]*body.shape[1])
    if pale_frac < 0.80:
        return False

    def has_button(x0,y0,x1,y1,lo,hi,cx_lo,cx_hi,cy_lo,cy_hi):
        roi=hsv[y0:y1,x0:x1]
        mask=cv2.inRange(roi,np.array(lo),np.array(hi))
        n,labels,stats,cent=cv2.connectedComponentsWithStats(mask)
        for i in range(1,n):
            x,y,w,h,area=stats[i]
            cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
            if not (2500 <= area <= 6500 and 100 <= w <= 150 and 28 <= h <= 52):
                continue
            if cx_lo <= cx <= cx_hi and cy_lo <= cy <= cy_hi:
                return True
        return False

    left=has_button(290,565,455,635,[0,70,100],[30,255,255],350,395,595,615)
    right=has_button(495,565,660,635,[35,45,80],[100,255,255],550,600,595,615)
    return left and right


def harvest_popup_point_for_plot(img,plot_x,plot_y):
    # 普通“收获”左侧图标是肤色手，VIP“一键收获”右侧是灰色手。
    # 不按黑框宽度猜按钮，只认深色菜单背景上的肤色手。
    if plant_panel_present(img) or management_panel_present(img):
        return None
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=300,500,680,850
    roi=hsv[y0:y1,x0:x1]
    if roi.size == 0:
        return None
    skin=cv2.inRange(roi,np.array([0,30,120]),np.array([30,200,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(skin)
    candidates=[]
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        if not (300 <= area <= 1100 and 28 <= w <= 58 and 20 <= h <= 48):
            continue
        cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
        px0=max(0,int(cx-45)); px1=min(img.shape[1],int(cx+45))
        py0=max(0,int(cy-35)); py1=min(img.shape[0],int(cy+35))
        patch=hsv[py0:py1,px0:px1]
        dark=cv2.inRange(patch,np.array([0,0,0]),np.array([180,255,130]))
        dark_frac=cv2.countNonZero(dark)/float(patch.shape[0]*patch.shape[1])
        if dark_frac < 0.65:
            continue
        candidates.append((dark_frac,int(area),cx,cy))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    _,_,cx,cy=candidates[0]
    return (cx,min(835.0,cy+22.0))


def farm_plot_centers():
    # 36 块真实药田：6x6 等距网格。
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


def probe_one_plant(page, events):
    # 补种也逐格问游戏：只有真正弹出选种面板才是空地。
    planted=0
    empty_seen=0
    occupied_seen=0
    centers=farm_plot_centers()
    page.screenshot(path=str(OUT/"before_full_plant.png"),full_page=True)

    for plot_no,(x,y) in enumerate(centers,start=1):
        page.mouse.click(x,y)
        events.append({"t":round(time.time(),2),"action":"plant_grid_probe",
                       "plot_no":plot_no,"x":round(x,1),"y":round(y,1)})
        print("[VISION]",events[-1],flush=True)
        time.sleep(1.2)

        opened=screenshot_img(page)
        if not plant_panel_present(opened):
            occupied_seen+=1
            events.append({"t":round(time.time(),2),"action":"plant_grid_occupied_skip",
                           "plot_no":plot_no,"x":round(x,1),"y":round(y,1)})
            print("[VISION]",events[-1],flush=True)
            page.mouse.click(470,430)
            time.sleep(0.5)
            continue

        empty_seen+=1
        events.append({"t":round(time.time(),2),"action":"plant_grid_empty_confirmed",
                       "plot_no":plot_no,"x":round(x,1),"y":round(y,1)})
        print("[VISION]",events[-1],flush=True)

        page.mouse.click(377,687)
        events.append({"t":round(time.time(),2),"action":"plant_choice_click",
                       "plant_no":planted+1,"plot_no":plot_no,"x":377.0,"y":687.0})
        print("[VISION]",events[-1],flush=True)
        time.sleep(1.8)

        mid=screenshot_img(page)
        if plant_panel_present(mid):
            page.mouse.click(x,y)
            events.append({"t":round(time.time(),2),"action":"plant_target_after_choice",
                           "plant_no":planted+1,"plot_no":plot_no,
                           "x":round(x,1),"y":round(y,1)})
            print("[VISION]",events[-1],flush=True)
            time.sleep(2.0)
        else:
            time.sleep(1.0)

        # 回点同一格，只要不再出现选种面板，就说明地块已经占用。
        page.mouse.click(x,y)
        time.sleep(1.2)
        verify=screenshot_img(page)
        still_empty=plant_panel_present(verify)
        events.append({"t":round(time.time(),2),"action":"plant_grid_reprobe_verify",
                       "plant_no":planted+1,"plot_no":plot_no,
                       "x":round(x,1),"y":round(y,1),
                       "plant_panel":bool(still_empty)})
        print("[VISION]",events[-1],flush=True)

        if still_empty:
            page.screenshot(path=str(OUT/"plant_verify_failed.png"),full_page=True)
            page.mouse.click(470,430)
            time.sleep(0.5)
            raise RuntimeError(f"第 {plot_no} 格确认空地后补种失败：回点仍出现选种面板")

        planted+=1
        page.mouse.click(470,430)
        time.sleep(0.5)
        if planted % 5 == 0:
            page.screenshot(path=str(OUT/f"plant_progress_{planted}.png"),full_page=True)

    page.screenshot(path=str(OUT/"after_full_plant.png"),full_page=True)
    events.append({"t":round(time.time(),2),"action":"full_plant_summary",
                   "planted":planted,"plots_probed":len(centers),
                   "empty_panels_seen":empty_seen,"occupied_skipped":occupied_seen,
                   "mode":"grid_6x6_ui_oracle"})
    print("[VISION]",events[-1],flush=True)


'''

s = s[:start] + final_block + s[end:]
p.write_text(s, encoding="utf-8")
print("patched final self-contained farm block: panels + VIP guard + ordinary harvest + grid + planting")
