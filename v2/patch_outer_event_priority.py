from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

start_marker = '''        # 内层清弹窗窗口结束后，仍可能晚到一张新的活动海报（如“修罗战场”）。\n'''
end_marker = '''        # 每日活动弹窗是常规分支：看到“今日不再提示”就勾上，再关右上角 X。\n'''
start = s.find(start_marker)
end = s.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit("outer modal block not found")

replacement = r'''        # 外层晚到活动海报必须优先走专用海报 X。
        # #138 现场：东海寻珍真实 X 在约 (631,235)，专用检测器可稳定命中；
        # 通用 modal_close_point 却误报 (676,229)，点击后画面几乎不变。
        # 只要专用活动海报还在，就绝不允许通用 X 抢先。
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
print("patched #138 outer event priority: known poster X before generic modal X")
