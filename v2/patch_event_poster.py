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


def profile_no_remind_confirm_cancel_point(img):
    # #123：勾“本次登录不再提示”后会弹确认框，明确警告“无法获得对应奖励”。
    # 这类确认框必须点左侧“取消”，绝不能自动确认。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)

    def button(x0,y0,x1,y1,lo,hi,cx_lo,cx_hi,cy_lo,cy_hi):
        roi=hsv[y0:y1,x0:x1]
        if roi.size == 0:
            return None
        mask=cv2.inRange(roi,np.array(lo),np.array(hi))
        n,labels,stats,cent=cv2.connectedComponentsWithStats(mask)
        best=None
        for i in range(1,n):
            x,y,w,h,area=stats[i]
            cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
            if area < 1400 or w < 75 or h < 24:
                continue
            if not (cx_lo <= cx <= cx_hi and cy_lo <= cy <= cy_hi):
                continue
            if best is None or area > best[0]:
                best=(area,(cx,cy))
        return best[1] if best else None

    left=button(285,560,465,635,[0,70,90],[30,255,255],340,410,585,620)
    right=button(485,560,665,635,[35,45,80],[100,255,255],535,615,585,620)
    if not left or not right:
        return None

    # 再要求标题栏右上存在这一确认框特有的浅金 X，避免把网络“重启/继续”误认。
    x0,y0,x1,y1=645,390,692,445
    roi=hsv[y0:y1,x0:x1]
    bright=cv2.inRange(roi,np.array([0,0,150]),np.array([45,180,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(bright)
    has_x=False
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
        if 30 <= area <= 700 and 8 <= w <= 38 and 8 <= h <= 38 and 655 <= cx <= 682 and 402 <= cy <= 430:
            has_x=True
            break
    if not has_x:
        return None
    return left


'''
s=s.replace(helper_anchor,event_helper+helper_anchor,1)

# 必须插在资料提示层之前。活动海报中的彩色按钮可能被
# profile_overlay_present 的境界牌颜色规则误认；如果放在后面，
# 前一分支每轮 continue，活动海报关闭逻辑永远没有执行机会。
post_anchor='''                    # 资料提示层：点旁边暗处。\n'''
if post_anchor not in s:
    raise SystemExit("profile overlay anchor not found")

event_block='''                    # #123 “不再提示会失去奖励”的确认框：始终点取消。\n                    pc=profile_no_remind_confirm_cancel_point(shot)\n                    if pc:\n                        page.mouse.click(pc[0],pc[1])\n                        events.append({"t":round(time.time(),2),"action":"profile_no_remind_confirm_cancel",\n                                       "x":round(pc[0],1),"y":round(pc[1],1)})\n                        print("[VISION]",events[-1],flush=True)\n                        clear_count+=1\n                        clean_frames=0\n                        time.sleep(3)\n                        continue\n\n                    # 换皮活动海报：先严格识别右上关闭 X。\n                    # “今日不再提示”能识别到就顺手勾；已经勾过导致复选框变样时，\n                    # 也不能阻止关闭海报。#121 就是卡在这个状态。\n                    ep_chk=today_no_remind_point(shot)\n                    ep=None\n                    if time.time() >= last_click.get("event_poster_retry_after",0):\n                        ep=event_poster_close_point(shot)\n                    if ep:\n                        if ep_chk:\n                            page.mouse.click(ep_chk[0],ep_chk[1])\n                            time.sleep(0.8)\n                        before_close=screenshot_img(page)\n                        page.mouse.click(ep[0],ep[1])\n                        time.sleep(2)\n                        after_close=screenshot_img(page)\n                        change=scene_change_score(before_close,after_close)\n                        events.append({"t":round(time.time(),2),"action":"post_dongfu_event_poster_x",\n                                       "x":round(ep[0],1),"y":round(ep[1],1),\n                                       "checkbox_x":round(ep_chk[0],1) if ep_chk else None,\n                                       "checkbox_y":round(ep_chk[1],1) if ep_chk else None,\n                                       "scene_change":round(change,2)})\n                        print("[VISION]",events[-1],flush=True)\n                        if change >= 2.0:\n                            clear_count+=1\n                            clean_frames=0\n                            time.sleep(4)\n                            continue\n                        last_click["event_poster_retry_after"]=time.time()+15\n                        page.screenshot(path=str(OUT/"event_poster_stuck.png"),full_page=True)\n\n'''
s=s.replace(post_anchor,event_block+post_anchor,1)

# 第二道硬保护：只要严格位置的活动海报 X 还在，或者仍能识别到
# “今日不再提示”，就不允许 profile_overlay_present 抢先吞掉它。
profile_old='''                    if profile_overlay_present(shot):\n'''
profile_new='''                    if not event_poster_close_point(shot) and not today_no_remind_point(shot) and profile_overlay_present(shot):\n'''
if profile_old not in s:
    raise SystemExit("profile overlay branch not found")
s=s.replace(profile_old,profile_new,1)

# #123 证明人物层的“不再提示”会触发“以后无法获得对应奖励”确认框。
# 所以人物层只关闭/推进，绝不再自动勾选该选项；检测坐标只保留在日志里便于诊断。
unsafe_profile='''                    if not event_poster_close_point(shot) and not today_no_remind_point(shot) and profile_overlay_present(shot):\n                        pnr=profile_no_remind_point(shot)\n                        if pnr:\n                            page.mouse.click(pnr[0],pnr[1])\n                            time.sleep(0.7)\n                        page.mouse.click(250,700)\n                        last_click["officer_flow_seen"]=time.time()\n                        events.append({"t":round(time.time(),2),"action":"officer_profile_advance","x":250.0,"y":700.0,\n                                       "no_remind_x":round(pnr[0],1) if pnr else None,\n                                       "no_remind_y":round(pnr[1],1) if pnr else None})\n                        print("[VISION]",events[-1],flush=True)\n                        time.sleep(4)\n                        continue\n'''
safe_profile='''                    if not event_poster_close_point(shot) and not today_no_remind_point(shot) and profile_overlay_present(shot):\n                        pnr=profile_no_remind_point(shot)\n                        page.mouse.click(250,700)\n                        last_click["officer_flow_seen"]=time.time()\n                        events.append({"t":round(time.time(),2),"action":"officer_profile_advance","x":250.0,"y":700.0,\n                                       "no_remind_x":round(pnr[0],1) if pnr else None,\n                                       "no_remind_y":round(pnr[1],1) if pnr else None,\n                                       "no_remind_clicked":False})\n                        print("[VISION]",events[-1],flush=True)\n                        time.sleep(4)\n                        continue\n'''
if unsafe_profile not in s:
    raise SystemExit("unsafe profile no-remind branch not found")
s=s.replace(unsafe_profile,safe_profile,1)

p.write_text(s,encoding="utf-8")
print("patched #123 reward-safe profile confirm cancel + event poster guard")