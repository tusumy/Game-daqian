from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

# #142 新现场：“玄境修行”竹叶绿活动海报。它的右上关闭 X 约在 (655,212)。
# 旧的白金 X 阈值会和浅绿色海报背景连成一整块，所以单独用更严格的
# 低饱和高亮掩码 + 小窗口识别，并把这段插到旧活动海报检测器的第二类之前。
poster_anchor = '''    # 第二类：#117/#121 “归墟战场”等白金色 X。\n'''
if poster_anchor not in s:
    raise SystemExit("event poster helper anchor not found")

xuanjing_block = r'''    # 第三类：#142 “玄境修行”竹叶绿海报，X 中心约 (655,212)。
    x0,y0,x1,y1=638,195,670,230
    roi=hsv[y0:y1,x0:x1]
    if roi.size:
        bright=cv2.inRange(roi,np.array([0,0,220]),np.array([180,70,255]))
        n,labels,stats,cent=cv2.connectedComponentsWithStats(bright)
        candidates=[]
        for i in range(1,n):
            x,y,w,h,area=stats[i]
            cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
            ratio=w/float(max(1,h))
            if not (150 <= area <= 320 and 18 <= w <= 28 and 20 <= h <= 30):
                continue
            if not (0.65 <= ratio <= 1.25):
                continue
            if not (650 <= cx <= 660 and 206 <= cy <= 218):
                continue
            score=abs(w-h)*2.0 + abs(cx-655.0) + abs(cy-212.0)
            candidates.append((score,-area,(cx,cy)))
        if candidates:
            candidates.sort(key=lambda z:(z[0],z[1]))
            return candidates[0][2]

'''
s = s.replace(poster_anchor, xuanjing_block + poster_anchor, 1)

start_marker = '''        # 内层清弹窗窗口结束后，仍可能晚到一张新的活动海报（如“修罗战场”）。\n'''
end_marker = '''        # 每日活动弹窗是常规分支：看到“今日不再提示”就勾上，再关右上角 X。\n'''
start = s.find(start_marker)
end = s.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit("outer modal block not found")

replacement = r'''        # 外层晚到活动海报必须优先走专用海报 X。
        # #138 现场：东海寻珍真实 X 在约 (631,235)，专用检测器可稳定命中；
        # 通用 modal_close_point 却误报 (676,229)，点击后画面几乎不变。
        # #142 又新增“玄境修行”X 约 (655,212)。只要专用活动海报还在，
        # 就绝不允许通用 X 抢先。
        if not action and not main_dongfu_point(img):
            ep = event_poster_close_point(img)
            if ep:
                if now-last_click.get("outer_event_poster",0) >= 8:
                    before_close = img
                    page.mouse.click(ep[0],ep[1])
                    last_click["outer_event_poster"] = now
                    time.sleep(2)
                    after_close = screenshot_img(page)
                    change = scene_change_score(before_close,after_close)
                    events.append({"t":round(now,2),"action":"outer_event_poster_x",
                                   "x":round(ep[0],1),"y":round(ep[1],1),
                                   "scene_change":round(change,2)})
                    print("[VISION]",events[-1],flush=True)
                    action = "outer_event_poster_x"
                    if change < 2.0:
                        page.screenshot(path=str(OUT/"outer_event_poster_stuck.png"),full_page=True)
                    time.sleep(2)
                else:
                    action = "outer_event_poster_wait"
                    time.sleep(1)
            else:
                mp=modal_close_point(img)
                if mp:
                    before_close=img
                    page.mouse.click(mp[0],mp[1])
                    time.sleep(2)
                    after_close=screenshot_img(page)
                    change=scene_change_score(before_close,after_close)
                    events.append({"t":round(now,2),"action":"outer_modal_x",
                                   "x":round(mp[0],1),"y":round(mp[1],1),
                                   "scene_change":round(change,2)})
                    print("[VISION]",events[-1],flush=True)
                    if change >= 2.0:
                        action="outer_modal_x"
                        time.sleep(2)
                    else:
                        page.screenshot(path=str(OUT/"outer_stuck_modal_x.png"),full_page=True)

'''

s = s[:start] + replacement + s[end:]

# #178: Festival monthly-card promotion hides the cave entrance.
# Its *white* X is centred near (629,310), not the older yellow promo X (660,302).
# Require the card's warm palette AND a tightly located white X; do not click purchase UI.
festival_anchor = "def promo_yellow_x_point(img):\n"
festival_helper = r'''def festival_month_card_x_point(img):
    """Recognize the 30-day orange monthly-card popup by independent visual cues."""
    if img is None or img.shape[0] < 920 or img.shape[1] < 1000:
        return None
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    warm=hsv[380:465,320:650]
    warm_mask=cv2.inRange(warm,np.array([0,90,100]),np.array([22,255,255]))
    if cv2.countNonZero(warm_mask)/float(warm.shape[0]*warm.shape[1]) < 0.50:
        return None
    heading=hsv[230:350,355:560]
    heading_mask=cv2.inRange(heading,np.array([0,80,90]),np.array([23,255,255]))
    if cv2.countNonZero(heading_mask)/float(heading.shape[0]*heading.shape[1]) < 0.32:
        return None
    x0,y0,x1,y1=608,289,650,332
    close=hsv[y0:y1,x0:x1]
    white=cv2.inRange(close,np.array([0,0,190]),np.array([180,90,255]))
    count,labels,stats,centers=cv2.connectedComponentsWithStats(white)
    for i in range(1,count):
        x,y,w,h,area=[int(v) for v in stats[i]]
        cx=float(centers[i][0]+x0)
        cy=float(centers[i][1]+y0)
        if 130 <= area <= 380 and 17 <= w <= 33 and 18 <= h <= 36 and 620 <= cx <= 639 and 300 <= cy <= 322:
            return (cx,cy)
    return None

'''
if s.count(festival_anchor) != 1:
    raise SystemExit("festival promo helper anchor missing or repeated")
s=s.replace(festival_anchor,festival_helper+festival_anchor,1)

# The popup may arrive before the first cave click, or afterwards inside cleanup.
outer_anchor="        action=None\n"
outer_block=r'''        # Close only this known monthly-card overlay before attempting cave navigation.
        if not action:
            fx=festival_month_card_x_point(img)
            if fx:
                page.mouse.click(fx[0],fx[1])
                time.sleep(2)
                after_festival=screenshot_img(page)
                still_festival=festival_month_card_x_point(after_festival) is not None
                events.append({"t":round(time.time(),2),"action":"festival_card_close",
                               "x":round(fx[0],1),"y":round(fx[1],1),
                               "scene_change":round(scene_change_score(img,after_festival),2),
                               "still_visible":still_festival})
                print("[VISION]",events[-1],flush=True)
                if still_festival:
                    page.screenshot(path=str(OUT/"festival_card_stuck.png"),full_page=True)
                    abort_reason="节日月卡关闭后仍然可见，已停止重试"
                continue

'''
if s.count(outer_anchor) != 1:
    raise SystemExit("outer action anchor missing or repeated")
s=s.replace(outer_anchor,outer_anchor+outer_block,1)

inner_anchor="                while time.time()<cleanup_deadline:\n                    shot=screenshot_img(page)\n"
inner_block=r'''                    # This popup overlays the cave menu. Close and re-check once,
                    # instead of repeatedly clicking a wrong yellow-X coordinate.
                    fx=festival_month_card_x_point(shot)
                    if fx:
                        page.mouse.click(fx[0],fx[1])
                        time.sleep(2)
                        after_festival=screenshot_img(page)
                        still_festival=festival_month_card_x_point(after_festival) is not None
                        events.append({"t":round(time.time(),2),"action":"post_dongfu_festival_card_close",
                                       "x":round(fx[0],1),"y":round(fx[1],1),
                                       "scene_change":round(scene_change_score(shot,after_festival),2),
                                       "still_visible":still_festival})
                        print("[VISION]",events[-1],flush=True)
                        if still_festival:
                            page.screenshot(path=str(OUT/"festival_card_stuck.png"),full_page=True)
                            abort_reason="节日月卡关闭后仍然可见，已停止重试"
                            break
                        clear_count+=1
                        clean_frames=0
                        continue

'''
if s.count(inner_anchor) != 1:
    raise SystemExit("inner cave cleanup anchor missing or repeated")
s=s.replace(inner_anchor,inner_anchor+inner_block,1)

# #220: the officer reward/profile overlay can cover the MAIN screen before
# the first Dongfu click.  The existing profile detector was only used inside
# the post-Dongfu cleanup loop; re-use that strict detector on the outer loop.
# Do not tick "本次登录不再提示": it can forfeit the login reward.
outer_officer_anchor='''        # SDK 登录初始化失败：优先点绿色“重启”，再等待游戏重新拉起。
'''
outer_officer_block=r'''        # #220: 仙官发玉/北斗星君人物层在洞府入口之前出现。
        # 只在既有的严格人物层检测命中时，点 #125 已验证的安全背景位置；
        # 不勾选“本次登录不再提示”，避免错过发玉奖励。
        if not action and profile_overlay_present(img):
            page.screenshot(path=str(OUT/"before_outer_officer_profile.png"),full_page=True)
            before_officer=img
            page.mouse.click(250,700)
            time.sleep(4)
            after_officer=screenshot_img(page)
            still_visible=bool(profile_overlay_present(after_officer))
            change=scene_change_score(before_officer,after_officer)
            attempts=last_click.get("outer_officer_profile_attempts",0)+1
            stalled=(last_click.get("outer_officer_profile_stalled",0)+1
                     if still_visible and change < 2.0 else 0)
            last_click["outer_officer_profile_attempts"]=attempts if still_visible else 0
            last_click["outer_officer_profile_stalled"]=stalled
            page.screenshot(path=str(OUT/"after_outer_officer_profile.png"),full_page=True)
            events.append({"t":round(time.time(),2),"action":"outer_officer_profile_advance",
                           "x":250.0,"y":700.0,"attempt":attempts,
                           "scene_change":round(change,2),"still_visible":still_visible,
                           "no_remind_clicked":False})
            print("[VISION]",events[-1],flush=True)
            if still_visible and (stalled >= 3 or attempts >= 8):
                page.screenshot(path=str(OUT/"outer_officer_profile_stuck.png"),full_page=True)
                abort_reason="仙官发玉人物层安全点击后仍未消失，已停止盲点"
            continue

'''
if s.count(outer_officer_anchor) != 1:
    raise SystemExit("outer officer profile anchor not found or repeated")
if "def profile_overlay_present(img):" not in s:
    raise SystemExit("strict officer profile detector is missing")
s=s.replace(outer_officer_anchor,outer_officer_block+outer_officer_anchor,1)

p.write_text(s, encoding="utf-8")
print("patched #142 xuanjing poster detector + outer event priority")
