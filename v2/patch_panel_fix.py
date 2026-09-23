from pathlib import Path

p=Path("v2/probe_popup.py")
s=p.read_text(encoding="utf-8")

anchor="def farm_plot_centers():"
if anchor not in s:
    raise SystemExit("farm_plot_centers anchor not found; run patch_grid_harvest.py first")

overrides=r'''def plant_panel_present(img):
    # 真正的选种面板会一直延伸到 y≈860；“浇水/锄除”管理面板只到 y≈735。
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
    # 误点右侧“一键收获”后会出现月卡激活提示：中央浅色大框 + 左橙取消/右绿确定。
    # 只在收获动作之后使用；一旦出现立即判失败，绝不继续把它当普通收获成功。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    modal=hsv[390:650,250:690]
    if modal.size == 0:
        return False
    pale=cv2.inRange(modal,np.array([0,0,145]),np.array([180,100,255]))
    pale_frac=cv2.countNonZero(pale)/float(modal.shape[0]*modal.shape[1])
    if pale_frac < 0.40:
        return False

    def has_button(x0,y0,x1,y1,lo,hi):
        roi=hsv[y0:y1,x0:x1]
        mask=cv2.inRange(roi,np.array(lo),np.array(hi))
        n,labels,stats,cent=cv2.connectedComponentsWithStats(mask)
        for i in range(1,n):
            x,y,w,h,area=stats[i]
            if area >= 1400 and w >= 80 and h >= 24:
                return True
        return False

    return (has_button(290,560,455,635,[0,70,100],[30,255,255]) and
            has_button(500,560,660,635,[35,45,80],[100,255,255]))


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

p.write_text(s,encoding="utf-8")
print("patched skin-hand ordinary harvest + VIP guard + safe dismiss point")
