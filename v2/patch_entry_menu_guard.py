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

# #109 现场：关闭公告后能正确点到洞府，但随即出现“节日欢庆豪礼”购买层。
# 这个层右上不是普通白 X，而是粉/蓝圆片里的交叉图标；如果把通用 X 放宽去吃它，
# 会重新引入 #108 的误识别。因此给这个购买层做单独、结构化识别。
festival_helper = r'''def festival_offer_close_point(img):
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)

    # 右上装饰关闭钮由大块粉色圆片 + 大块青蓝圆片叠在一起，
    # #109 实测两块面积都在 2k 左右；公告白页没有这组组合。
    x0,y0,x1,y1=600,170,690,275
    roi=hsv[y0:y1,x0:x1]
    if roi.size == 0:
        return None

    cyan=cv2.inRange(roi,np.array([80,60,80]),np.array([110,255,255]))
    pink=cv2.inRange(roi,np.array([145,45,100]),np.array([179,255,255]))

    def has_big(mask,area_lo,area_hi,w_lo,w_hi,h_lo,h_hi,cx_lo,cx_hi,cy_lo,cy_hi):
        n,labels,stats,cent=cv2.connectedComponentsWithStats(mask)
        for i in range(1,n):
            x,y,w,h,area=stats[i]
            cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
            if not (area_lo <= area <= area_hi and w_lo <= w <= w_hi and h_lo <= h <= h_hi):
                continue
            if cx_lo <= cx <= cx_hi and cy_lo <= cy <= cy_hi:
                return True
        return False

    if not has_big(cyan,1500,3800,45,75,45,80,620,646,228,262):
        return None
    if not has_big(pink,1400,3800,45,80,50,90,612,642,182,218):
        return None

    # 两块彩色圆片命中后，再只在交叉图标的小窗口里找白/浅金亮部。
    bx0,by0,bx1,by1=625,190,665,235
    broi=hsv[by0:by1,bx0:bx1]
    bright=cv2.inRange(broi,np.array([0,0,175]),np.array([180,100,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(bright)
    best=None
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        cx=float(cent[i][0]+bx0); cy=float(cent[i][1]+by0)
        if not (120 <= area <= 500 and 16 <= w <= 32 and 18 <= h <= 36):
            continue
        if not (636 <= cx <= 652 and 207 <= cy <= 226):
            continue
        score=abs(cx-643.5)+abs(cy-216.0)
        if best is None or score < best[0]:
            best=(score,(cx,cy))
    return best[1] if best else None


'''
helper_anchor="def modal_close_point(img):"
if helper_anchor not in s:
    raise SystemExit("modal helper anchor not found")
s=s.replace(helper_anchor,festival_helper+helper_anchor,1)

post_anchor = '''                    # 充值推广类黄色 X。\n                    yp=promo_yellow_x_point(shot)\n'''
post_replacement = '''                    # #109 的“节日欢庆豪礼”购买层：右上粉蓝交叉图标关闭。\n                    fp=None\n                    if time.time() >= last_click.get("festival_offer_retry_after",0):\n                        fp=festival_offer_close_point(shot)\n                    if fp:\n                        before_close=shot\n                        page.mouse.click(fp[0],fp[1])\n                        time.sleep(2)\n                        after_close=screenshot_img(page)\n                        change=scene_change_score(before_close,after_close)\n                        events.append({"t":round(time.time(),2),"action":"post_dongfu_festival_offer_x",\n                                       "x":round(fp[0],1),"y":round(fp[1],1),\n                                       "scene_change":round(change,2)})\n                        print("[VISION]",events[-1],flush=True)\n                        if change >= 2.0:\n                            clear_count+=1\n                            clean_frames=0\n                            time.sleep(4)\n                            continue\n                        last_click["festival_offer_retry_after"]=time.time()+15\n                        page.screenshot(path=str(OUT/"festival_offer_stuck.png"),full_page=True)\n\n                    # 充值推广类黄色 X。\n                    yp=promo_yellow_x_point(shot)\n'''
if post_anchor not in s:
    raise SystemExit("post-dongfu promo anchor not found")
s=s.replace(post_anchor,post_replacement,1)

p.write_text(s, encoding="utf-8")
print("patched strict dongfu-menu guard + strict modal X + #109 festival-offer close + stale-X cooldown; keep x=625")
