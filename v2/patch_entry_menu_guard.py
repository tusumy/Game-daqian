from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

# patch_grid_harvest.py 会先把丹界点击点从 575 右移到 625，
# 所以这里不能死盯旧 return 文本。两种运行时形态都接受，最终统一保留 625。
needle_575 = '''    lf=pale_frac(left)\n    rf=pale_frac(right_bottom)\n    if lf >= 0.65 and rf >= 0.45:\n        # 当前固定 1280x960 画布中，“丹界”卡片中心约为 (575,785)。\n        return (575.0,785.0,lf,rf)\n'''
needle_625 = '''    lf=pale_frac(left)\n    rf=pale_frac(right_bottom)\n    if lf >= 0.65 and rf >= 0.45:\n        # 当前固定 1280x960 画布中，“丹界”卡片中心约为 (575,785)。\n        return (625.0,785.0,lf,rf)\n'''
replacement = '''    lf=pale_frac(left)\n    rf=pale_frac(right_bottom)\n    # #99 现场证明“公告”大白页会同时把左列和右下判成浅色，\n    # 从而被误认成洞府菜单。真洞府菜单的右侧中段是游戏背景，几乎不浅；\n    # 公告正文在同一区域则接近整片灰白。用这个结构差异做硬排除。\n    right_mid=hsv[250:700,480:680]\n    mf=pale_frac(right_mid)\n    if lf >= 0.65 and rf >= 0.45 and mf <= 0.30:\n        # 丹界点击点右移以避开黄色引导手。\n        return (625.0,785.0,lf,rf)\n'''

if needle_625 in s:
    s = s.replace(needle_625, replacement, 1)
elif needle_575 in s:
    s = s.replace(needle_575, replacement, 1)
else:
    raise SystemExit("dongfu menu detector block not found in 575/625 form")

# #108 卡死原因不是丹界菜单识别，而是公告页右上区域的亮色标题/边框
# 被通用 modal_close_point 当成关闭 X。#107 也曾连续误点同一坐标，只是后来侥幸恢复。
# 真 X 在不同公告上会有少量漂移，但自身始终是约 20~30px 的近方形亮色符号；
# 因此排除 55x27 这类大横块，只保留近方形候选。
modal_start = s.find("def modal_close_point(img):")
modal_end = s.find("\ndef mature_candidate_points(img):", modal_start)
if modal_start < 0 or modal_end < 0:
    raise SystemExit("modal_close_point block not found")

strict_modal = r'''def modal_close_point(img):
    # 通用活动/公告页右上关闭 X。#108 现场里真正 X 约 24x25，
    # 旧逻辑却因“面积最大”选中了 55x27 的亮色标题/边框，随后原地误点 62 次。
    # 这里先按 X 的近方形尺寸做硬过滤，再在合理中心区域内选最可信候选。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=630,200,690,265
    roi=hsv[y0:y1,x0:x1]
    if roi.size == 0:
        return None
    bright=cv2.inRange(roi,np.array([0,0,165]),np.array([180,255,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(bright)
    candidates=[]
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        if not (60 <= area <= 700 and 10 <= w <= 38 and 10 <= h <= 38):
            continue
        ratio=w/float(max(1,h))
        if not (0.65 <= ratio <= 1.55):
            continue
        cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
        if not (642 <= cx <= 678 and 208 <= cy <= 252):
            continue
        # 兼容不同公告 X 的轻微漂移；优先形状更方、同时略偏向历史中心区域的候选。
        score=abs(w-h)*2.0 + abs(cx-660.0)*0.25 + abs(cy-230.0)*0.20
        candidates.append((score,-area,(cx,cy)))
    if not candidates:
        return None
    candidates.sort(key=lambda z:(z[0],z[1]))
    return candidates[0][2]


'''
s = s[:modal_start] + strict_modal + s[modal_end+1:]

# 外层通用 X 若点击后画面几乎没变化，说明这次候选不可信。
# 旧逻辑下一轮会立即再次命中同一亮块，#108 因此一直空点到总超时。
# 给通用 X 一个短冷却，让模板识别、网络恢复和主界面锚点有机会继续接管流程。
outer_guard_old = '''        if not action and not main_dongfu_point(img):\n            mp=modal_close_point(img)\n'''
outer_guard_new = '''        if (not action and not main_dongfu_point(img)\n                and now >= last_click.get("outer_modal_retry_after",0)):\n            mp=modal_close_point(img)\n'''
if outer_guard_old not in s:
    raise SystemExit("outer modal guard not found")
s = s.replace(outer_guard_old, outer_guard_new, 1)

stuck_old = '''                else:\n                    page.screenshot(path=str(OUT/"outer_stuck_modal_x.png"),full_page=True)\n'''
stuck_new = '''                else:\n                    last_click["outer_modal_retry_after"]=now+15\n                    page.screenshot(path=str(OUT/"outer_stuck_modal_x.png"),full_page=True)\n'''
if stuck_old not in s:
    raise SystemExit("outer modal stuck branch not found")
s = s.replace(stuck_old, stuck_new, 1)

p.write_text(s, encoding="utf-8")
print("patched strict dongfu-menu guard + strict modal X shape + stale-X cooldown; keep x=625")
