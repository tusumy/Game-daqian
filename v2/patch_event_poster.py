from pathlib import Path

p=Path("v2/probe_popup.py")
s=p.read_text(encoding="utf-8")

# #111/#115 现场：“东海寻珍”等活动海报底部稳定带“今日不再提示”，
# 右上关闭键是米黄色 X。#115 又证明这类海报会被较宽松的 profile_overlay_present
# 抢先误认，导致 cleanup 循环反复点暗处，专用海报关闭逻辑根本轮不到。
# 因此除了结构化识别海报外，还必须把它放到“资料提示层”之前处理。
helper_anchor="def modal_close_point(img):"
if helper_anchor not in s:
    raise SystemExit("modal helper anchor not found")

event_helper=r'''def event_poster_close_point(img):
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=600,190,660,260
    roi=hsv[y0:y1,x0:x1]
    if roi.size == 0:
        return None

    # “东海寻珍”一类海报的米黄 X：约 24x24，中心 (631,235)。
    beige=cv2.inRange(roi,np.array([5,15,210]),np.array([35,100,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(beige)
    candidates=[]
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
        if not (100 <= area <= 260 and 16 <= w <= 30 and 16 <= h <= 30):
            continue
        if not (620 <= cx <= 640 and 224 <= cy <= 244):
            continue
        score=abs(w-h)*2.0 + abs(cx-631.0) + abs(cy-235.0)
        candidates.append((score,-area,(cx,cy)))
    if not candidates:
        return None
    candidates.sort(key=lambda z:(z[0],z[1]))
    return candidates[0][2]


'''
s=s.replace(helper_anchor,event_helper+helper_anchor,1)

# 必须插在资料提示层之前。#115 现场里东海寻珍底部橙色“立即前往”
# 会被 profile_overlay_present 的境界牌颜色规则误认；如果仍放在后面，
# 前一分支每轮 continue，活动海报关闭逻辑永远没有执行机会。
post_anchor='''                    # 资料提示层：点旁边暗处。\n'''
if post_anchor not in s:
    raise SystemExit("profile overlay anchor not found")

event_block='''                    # #111/#115 “东海寻珍”等带“今日不再提示”的活动海报：\n                    # 必须优先于人物资料层处理，避免海报按钮被误认成境界牌。\n                    ep_chk=today_no_remind_point(shot)\n                    ep=None\n                    if ep_chk and time.time() >= last_click.get("event_poster_retry_after",0):\n                        ep=event_poster_close_point(shot)\n                    if ep:\n                        # 先勾本次不再提示，避免同一次登录里再次挡住洞府。\n                        page.mouse.click(ep_chk[0],ep_chk[1])\n                        time.sleep(0.8)\n                        before_close=screenshot_img(page)\n                        page.mouse.click(ep[0],ep[1])\n                        time.sleep(2)\n                        after_close=screenshot_img(page)\n                        change=scene_change_score(before_close,after_close)\n                        events.append({"t":round(time.time(),2),"action":"post_dongfu_event_poster_x",\n                                       "x":round(ep[0],1),"y":round(ep[1],1),\n                                       "checkbox_x":round(ep_chk[0],1),"checkbox_y":round(ep_chk[1],1),\n                                       "scene_change":round(change,2)})\n                        print("[VISION]",events[-1],flush=True)\n                        if change >= 2.0:\n                            clear_count+=1\n                            clean_frames=0\n                            time.sleep(4)\n                            continue\n                        last_click["event_poster_retry_after"]=time.time()+15\n                        page.screenshot(path=str(OUT/"event_poster_stuck.png"),full_page=True)\n\n'''
s=s.replace(post_anchor,event_block+post_anchor,1)

# 第二道硬保护：只要当前画面存在“今日不再提示”复选框，就不允许
# profile_overlay_present 抢先吞掉它。这样即使以后海报 X 轻微换皮，
# 也不会再出现 #115 那种连续 officer_profile_advance 空点。
profile_old='''                    if profile_overlay_present(shot):\n'''
profile_new='''                    if not today_no_remind_point(shot) and profile_overlay_present(shot):\n'''
if profile_old not in s:
    raise SystemExit("profile overlay branch not found")
s=s.replace(profile_old,profile_new,1)

p.write_text(s,encoding="utf-8")
print("patched #115 prioritized event-poster close before profile overlay")