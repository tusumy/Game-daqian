from pathlib import Path

p=Path("v2/probe_popup.py")
s=p.read_text(encoding="utf-8")

# #111/#115/#117/#121 现场：活动海报底部常带“今日不再提示”，
# 右上关闭 X 会换皮：东海寻珍是米黄色，归墟战场则是偏白金色。
# #121 又证明复选框在已经勾过后会改变外观，today_no_remind_point 可能识别不到，
# 因此“检测到复选框”不能再作为关闭海报的前置条件；应优先认严格位置的 X，
# 复选框能找到就顺手勾，找不到也照样关海报。
helper_anchor="def modal_close_point(img):"
if helper_anchor not in s:
    raise SystemExit("modal helper anchor not found")

event_helper=r'''def event_poster_close_point(img):
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)

    # 第一类：#111/#115 “东海寻珍”的米黄色 X，约 24x24，中心 (631,235)。
    x0,y0,x1,y1=600,190,660,260
    roi=hsv[y0:y1,x0:x1]
    if roi.size == 0:
        return None
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
    if candidates:
        candidates.sort(key=lambda z:(z[0],z[1]))
        return candidates[0][2]

    # 第二类：#117/#121 “归墟战场”等白金色 X。
    # 位置和尺寸保持严格，避免把海报内容或普通 UI 高亮误当关闭键。
    x0,y0,x1,y1=610,190,680,260
    roi=hsv[y0:y1,x0:x1]
    pale=cv2.inRange(roi,np.array([0,0,180]),np.array([180,120,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(pale)
    candidates=[]
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
        ratio=w/float(max(1,h))
        if not (100 <= area <= 500 and 14 <= w <= 34 and 14 <= h <= 34):
            continue
        if not (0.55 <= ratio <= 1.60):
            continue
        if not (645 <= cx <= 666 and 214 <= cy <= 240):
            continue
        score=abs(w-h)*2.0 + abs(cx-655.0)*0.4 + abs(cy-227.0)*0.4
        candidates.append((score,-area,(cx,cy)))
    if not candidates:
        return None
    candidates.sort(key=lambda z:(z[0],z[1]))
    return candidates[0][2]


'''
s=s.replace(helper_anchor,event_helper+helper_anchor,1)

# 必须插在资料提示层之前。活动海报中的彩色按钮可能被
# profile_overlay_present 的境界牌颜色规则误认；如果放在后面，
# 前一分支每轮 continue，活动海报关闭逻辑永远没有执行机会。
post_anchor='''                    # 资料提示层：点旁边暗处。\n'''
if post_anchor not in s:
    raise SystemExit("profile overlay anchor not found")

event_block='''                    # 换皮活动海报：先严格识别右上关闭 X。\n                    # “今日不再提示”能识别到就顺手勾；已经勾过导致复选框变样时，\n                    # 也不能阻止关闭海报。#121 就是卡在这个状态。\n                    ep_chk=today_no_remind_point(shot)\n                    ep=None\n                    if time.time() >= last_click.get("event_poster_retry_after",0):\n                        ep=event_poster_close_point(shot)\n                    if ep:\n                        if ep_chk:\n                            page.mouse.click(ep_chk[0],ep_chk[1])\n                            time.sleep(0.8)\n                        before_close=screenshot_img(page)\n                        page.mouse.click(ep[0],ep[1])\n                        time.sleep(2)\n                        after_close=screenshot_img(page)\n                        change=scene_change_score(before_close,after_close)\n                        events.append({"t":round(time.time(),2),"action":"post_dongfu_event_poster_x",\n                                       "x":round(ep[0],1),"y":round(ep[1],1),\n                                       "checkbox_x":round(ep_chk[0],1) if ep_chk else None,\n                                       "checkbox_y":round(ep_chk[1],1) if ep_chk else None,\n                                       "scene_change":round(change,2)})\n                        print("[VISION]",events[-1],flush=True)\n                        if change >= 2.0:\n                            clear_count+=1\n                            clean_frames=0\n                            time.sleep(4)\n                            continue\n                        last_click["event_poster_retry_after"]=time.time()+15\n                        page.screenshot(path=str(OUT/"event_poster_stuck.png"),full_page=True)\n\n'''
s=s.replace(post_anchor,event_block+post_anchor,1)

# 第二道硬保护：只要严格位置的活动海报 X 还在，或者仍能识别到
# “今日不再提示”，就不允许 profile_overlay_present 抢先吞掉它。
profile_old='''                    if profile_overlay_present(shot):\n'''
profile_new='''                    if not event_poster_close_point(shot) and not today_no_remind_point(shot) and profile_overlay_present(shot):\n'''
if profile_old not in s:
    raise SystemExit("profile overlay branch not found")
s=s.replace(profile_old,profile_new,1)

p.write_text(s,encoding="utf-8")
print("patched #121 event-poster close independent of checkbox state + profile guard")