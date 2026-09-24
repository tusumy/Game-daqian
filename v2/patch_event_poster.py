from pathlib import Path

p=Path("v2/probe_popup.py")
s=p.read_text(encoding="utf-8")

# #111 现场：仙官/奖励层都清完并重试洞府后，出现“东海寻珍”海报。
# 这类海报底部稳定带“今日不再提示”复选框，右上关闭键是米黄色 X，
# 既不是普通白 X，也不是黄色充值 X。用“复选框 + 米黄 X”组合识别，
# 避免放宽通用 modal_close_point 又把 #108 的假 X 引回来。
helper_anchor="def modal_close_point(img):"
if helper_anchor not in s:
    raise SystemExit("modal helper anchor not found")

event_helper=r'''def event_poster_close_point(img):
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=600,190,660,260
    roi=hsv[y0:y1,x0:x1]
    if roi.size == 0:
        return None

    # #111 的米黄 X：约 24x24，中心 (631,235)。
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

post_anchor='''                    # #109 的“节日欢庆豪礼”购买层：右上粉蓝交叉图标关闭。\n'''
if post_anchor not in s:
    raise SystemExit("post-dongfu festival anchor not found; run patch_entry_menu_guard.py first")

event_block='''                    # #111 “东海寻珍”等带“今日不再提示”的活动海报：\n                    # 用底部复选框确认这是活动海报，再点其右上米黄色 X。\n                    ep_chk=today_no_remind_point(shot)\n                    ep=None\n                    if ep_chk and time.time() >= last_click.get("event_poster_retry_after",0):\n                        ep=event_poster_close_point(shot)\n                    if ep:\n                        # 先勾本次不再提示，避免同一次登录里再次挡住洞府。\n                        page.mouse.click(ep_chk[0],ep_chk[1])\n                        time.sleep(0.8)\n                        before_close=screenshot_img(page)\n                        page.mouse.click(ep[0],ep[1])\n                        time.sleep(2)\n                        after_close=screenshot_img(page)\n                        change=scene_change_score(before_close,after_close)\n                        events.append({"t":round(time.time(),2),"action":"post_dongfu_event_poster_x",\n                                       "x":round(ep[0],1),"y":round(ep[1],1),\n                                       "checkbox_x":round(ep_chk[0],1),"checkbox_y":round(ep_chk[1],1),\n                                       "scene_change":round(change,2)})\n                        print("[VISION]",events[-1],flush=True)\n                        if change >= 2.0:\n                            clear_count+=1\n                            clean_frames=0\n                            time.sleep(4)\n                            continue\n                        last_click["event_poster_retry_after"]=time.time()+15\n                        page.screenshot(path=str(OUT/"event_poster_stuck.png"),full_page=True)\n\n'''
s=s.replace(post_anchor,event_block+post_anchor,1)

p.write_text(s,encoding="utf-8")
print("patched #111 guarded event-poster close: checkbox + beige X")
