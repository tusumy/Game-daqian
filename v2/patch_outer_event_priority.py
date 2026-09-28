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
p.write_text(s, encoding="utf-8")
print("patched #142 xuanjing poster detector + outer event priority")
