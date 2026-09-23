from pathlib import Path

p=Path("v2/probe_popup.py")
s=p.read_text(encoding="utf-8")

anchor="def farm_plot_centers():"
if anchor not in s:
    raise SystemExit("farm_plot_centers anchor not found; run patch_grid_harvest.py first")

overrides=r'''def plant_panel_present(img):
    # 真正的选种面板会一直延伸到 y≈860；“浇水/锄除”管理面板只到 y≈735。
    # 只看下半段的暗色占比，避免把管理面板误认成选种面板。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    roi=hsv[740:860,250:700]
    if roi.size == 0:
        return False
    dark=cv2.inRange(roi,np.array([0,0,0]),np.array([180,255,120]))
    frac=cv2.countNonZero(dark)/float(roi.shape[0]*roi.shape[1])
    return frac >= 0.55


def management_panel_present(img):
    # 生长期灵植点击后会出现“浇水/锄除”管理面板：宽而矮，集中在 y≈590..720。
    # 与真正选种面板、下半排“特权”收获面板分开。
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


def harvest_popup_point_for_plot(img,plot_x,plot_y):
    # 上半区沿用已经验证成功的“特权”菜单检测。
    hp=harvest_popup_point(img)
    if hp:
        return hp

    # 选种面板和浇水/锄除管理面板绝不能当成收获菜单。
    if plant_panel_present(img) or management_panel_present(img):
        return None

    # 下半排地块的“特权”菜单会整体下移，旧检测框(y<=710)看不到。
    # #89 现场校准：菜单在 y≈680..800，普通收获位于所点地块左下方；
    # 这里只在该区域确有明显暗色菜单时才给出左侧普通“收获”坐标。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    roi=hsv[680:800,340:590]
    if roi.size == 0:
        return None
    dark=cv2.inRange(roi,np.array([0,0,0]),np.array([180,255,130]))
    frac=cv2.countNonZero(dark)/float(roi.shape[0]*roi.shape[1])
    if frac < 0.45:
        return None

    hx=max(330.0,min(600.0,float(plot_x)-57.0))
    hy=max(700.0,min(770.0,float(plot_y)+132.0))
    return (hx,hy)


'''

if "def harvest_popup_point_for_plot" not in s:
    s=s.replace(anchor,overrides+anchor,1)

s=s.replace("hp=harvest_popup_point(opened)","hp=harvest_popup_point_for_plot(opened,x,y)")
s=s.replace("still_open=harvest_popup_point(after) is not None","still_open=harvest_popup_point_for_plot(after,x,y) is not None")

p.write_text(s,encoding="utf-8")
print("patched strict plant panel + management panel guard + lower harvest fallback")
