from pathlib import Path

p=Path("v2/probe_popup.py")
s=p.read_text(encoding="utf-8")

anchor="def farm_plot_centers():"
if anchor not in s:
    raise SystemExit("farm_plot_centers anchor not found; run patch_grid_harvest.py first")

overrides=r'''def plant_panel_present(img):
    # 真正的选种面板会一直延伸到 y≈860；“浇水/锄除”管理面板只到 y≈735。
    # 不再依赖“灵植/造化灵植”标签的死颜色，避免空地因换肤被误判 occupied。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    roi=hsv[740:860,250:700]
    if roi.size == 0:
        return False
    dark=cv2.inRange(roi,np.array([0,0,0]),np.array([180,255,120]))
    frac=cv2.countNonZero(dark)/float(roi.shape[0]*roi.shape[1])
    return frac >= 0.55


def management_panel_present(img):
    # 生长期灵植点击后会出现“浇水/锄除”管理面板：宽而矮，集中在 y≈590..720。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    mid=hsv[590:720,300:650]
    tail=hsv[740:790,300:650]
    if mid.size == 0 or tail.size == 0:
        return False
    md=cv2.inRange(mid,np.array([0,0,0]),np.array([180,255,130]))
    td=cv2.inRange(tail,np.array([0,0,0]),np.array([180,255,130]))
    mf=cv2.countNonZero(md)/float(mid.shape[0]*mid.shape[1])
    tf=cv2.countNonZero(td)/float(tail.shape[0]*tail.shape[1])
    return mf >= 0.55 and tf <= 0.20


def vip_monthly_warning_present(img):
    # 真正误点“一键收获”的月卡提示位于游戏画布内部：
    # x≈250..690,y≈395..645 的大浅色弹窗，正文区几乎整块都是灰白底。
    # #91 曾把正常丹界农田误报成月卡提示，因此必须先要求正文浅色占比很高，
    # 再同时命中左橙“取消”和右绿“确定”。网页右侧常驻 VIP 权益栏完全不参与检测。
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
    # 不再根据黑框比例猜按钮位置。普通“收获”左侧图标是肤色手，
    # VIP“一键收获”右侧图标是灰色手；只认“深色菜单背景上的肤色手”。
    # 这样即使菜单随下半排整体下移，也不会碰右侧 VIP。
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
    # 点肤色手正下方的“收获”文字区域，仍在左侧按钮容器内。
    return (cx,min(835.0,cy+22.0))


'''

if "def harvest_popup_point_for_plot" not in s:
    s=s.replace(anchor,overrides+anchor,1)
else:
    start=s.find("def plant_panel_present(img):")
    end=s.find("def farm_plot_centers():",start)
    if start < 0 or end < 0:
        raise SystemExit("panel override block not found")
    s=s[:start]+overrides+s[end:]

s=s.replace("hp=harvest_popup_point(opened)","hp=harvest_popup_point_for_plot(opened,x,y)")
s=s.replace("still_open=harvest_popup_point(after) is not None","still_open=harvest_popup_point_for_plot(after,x,y) is not None")

# 收获后若出现月卡提示，立即停止并保存现场，绝不把 VIP 误触计为成功。
needle="""            after=screenshot_img(page)\n            still_open=harvest_popup_point_for_plot(after,x,y) is not None\n"""
replacement="""            after=screenshot_img(page)\n            if vip_monthly_warning_present(after):\n                page.screenshot(path=str(OUT/\"vip_one_click_misfire.png\"),full_page=True)\n                raise RuntimeError(f\"第 {plot_no} 块误触 VIP 一键收获；已停止并保存现场\")\n            still_open=harvest_popup_point_for_plot(after,x,y) is not None\n"""
if needle in s:
    s=s.replace(needle,replacement,1)

# (470,730) 会碰到丹界底部可交互角色/活动入口，曾打开药仙来访。
# 改到药田上方中间的稳定空白草地，只用于关闭选种/管理面板。
s=s.replace("page.mouse.click(470,730)","page.mouse.click(470,430)")

# #93 现场确认小苗已经种出，但棕色地块下降只有 0.165；原 0.18 阈值过严。
# 仍要求选种面板出现并且棕色占比至少下降 0.12，避免把未种上的空地算成功。
s=s.replace("before_tan-0.18","before_tan-0.12")

# #131：感悟升级也有绿色“前往”，曾被 forward_only_event_button 误当活动入口。
# 只要升级弹窗的“取消/前往”双按钮成立，forward-only 活动识别必须让路给 upgrade_cancel_point。
fwd_anchor="def forward_only_event_button(img):\n"
if fwd_anchor in s:
    fwd_start=s.find(fwd_anchor)
    fwd_head=s[fwd_start:fwd_start+220]
    if "upgrade_cancel_point(img)" not in fwd_head:
        s=s.replace(fwd_anchor,
                    fwd_anchor+"    if upgrade_cancel_point(img):\n        return None\n",1)

p.write_text(s,encoding="utf-8")
print("patched structural plant panel + VIP guard + upgrade-modal forward guard")
