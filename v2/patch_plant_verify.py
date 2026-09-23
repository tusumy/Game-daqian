from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

# patch_panel_fix.py 会在 farm_plot_centers 前注入最终覆盖版的
# plant_panel_present / management_panel_present / vip_monthly_warning_present。
# 文件里还保留更早的旧 plant_panel_present，同名函数不能用 find() 抓第一处。
end_cls = s.find("def vip_monthly_warning_present(img):")
if end_cls < 0:
    raise SystemExit("final vip_monthly_warning_present not found; run patch_panel_fix.py first")
start_cls = s.rfind("def plant_panel_present(img):", 0, end_cls)
if start_cls < 0:
    raise SystemExit("final plant_panel_present not found before vip classifier")

classifiers = r'''def plant_panel_present(img):
    # 真空地点击后会出现真正的选种面板，顶部固定有一对并排标签：
    # 左侧黄色“灵植”，右侧青绿色“造化灵植”。
    # 多波灵植处于生长间隔时即使画面很秃，也只会打开倒计时/浇水/锄除管理面板，
    # 不会同时出现这对标签。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    left=hsv[535:585,245:385]
    right=hsv[535:585,370:515]
    if left.size == 0 or right.size == 0:
        return False

    yellow=cv2.inRange(left,np.array([15,80,170]),np.array([35,255,255]))
    teal=cv2.inRange(right,np.array([75,50,90]),np.array([110,220,230]))
    yellow_frac=cv2.countNonZero(yellow)/float(yellow.shape[0]*yellow.shape[1])
    teal_frac=cv2.countNonZero(teal)/float(teal.shape[0]*teal.shape[1])
    return yellow_frac >= 0.35 and teal_frac >= 0.35


def management_panel_present(img):
    # 仅供收获阶段避让管理面板；补种阶段不再依赖它判断是否种成功。
    if plant_panel_present(img):
        return False
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=240,540,710,850
    roi=hsv[y0:y1,x0:x1]
    if roi.size == 0:
        return False
    dark=cv2.inRange(roi,np.array([0,0,0]),np.array([180,255,130]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(dark)
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        if area >= 22000 and w >= 300 and h >= 95:
            return True
    return False


'''
s = s[:start_cls] + classifiers + s[end_cls:]

# #98 的第 9 块证明：棕色/裸地外观不能代表空地。
# 多波灵植收过一波后会进入倒计时，画面可能近似裸地，但地块仍然占用。
# 因此彻底废弃 empty_plot_candidates() 的视觉猜空逻辑：
# 逐格点击 6x6 的 36 个真实地块，只有游戏自己弹出“灵植/造化灵植”选种面板才补种。
start_fn = s.find("def probe_one_plant(page, events):")
end_fn = s.find("\ndef probe_existing_plant(page, events):", start_fn)
if start_fn < 0 or end_fn < 0:
    raise SystemExit("probe_one_plant block not found")

probe = r'''def probe_one_plant(page, events):
    planted=0
    empty_seen=0
    occupied_seen=0
    centers=farm_plot_centers()
    page.screenshot(path=str(OUT/"before_full_plant.png"),full_page=True)

    for plot_no,(x,y) in enumerate(centers,start=1):
        # 每一格都直接问游戏，不再看地面颜色。
        page.mouse.click(x,y)
        events.append({"t":round(time.time(),2),"action":"plant_grid_probe",
                       "plot_no":plot_no,"x":round(x,1),"y":round(y,1)})
        print("[VISION]",events[-1],flush=True)
        time.sleep(1.2)

        opened=screenshot_img(page)
        if not plant_panel_present(opened):
            # 已有灵植（包括“剩余1波”的生长间隔）、成熟菜单或其它占用状态。
            # 对补种而言都只需跳过。
            occupied_seen+=1
            events.append({"t":round(time.time(),2),"action":"plant_grid_occupied_skip",
                           "plot_no":plot_no,"x":round(x,1),"y":round(y,1)})
            print("[VISION]",events[-1],flush=True)
            page.mouse.click(470,430)
            time.sleep(0.5)
            continue

        empty_seen+=1
        events.append({"t":round(time.time(),2),"action":"plant_grid_empty_confirmed",
                       "plot_no":plot_no,"x":round(x,1),"y":round(y,1)})
        print("[VISION]",events[-1],flush=True)

        # 选种面板第一页任选已解锁灵植；此位置从 #83 起已经多轮实际种植验证。
        page.mouse.click(377,687)
        events.append({"t":round(time.time(),2),"action":"plant_choice_click",
                       "plant_no":planted+1,"plot_no":plot_no,
                       "x":377.0,"y":687.0})
        print("[VISION]",events[-1],flush=True)
        time.sleep(1.8)

        mid=screenshot_img(page)
        if plant_panel_present(mid):
            # 某些状态需要先选灵植、再点目标地块。
            page.mouse.click(x,y)
            events.append({"t":round(time.time(),2),"action":"plant_target_after_choice",
                           "plant_no":planted+1,"plot_no":plot_no,
                           "x":round(x,1),"y":round(y,1)})
            print("[VISION]",events[-1],flush=True)
            time.sleep(2.0)
        else:
            time.sleep(1.0)

        # 最终验收同样只问游戏：重新点该格。
        # 若仍弹“灵植/造化灵植”选种面板，说明它仍为空；
        # 只要不再弹选种面板，就说明地块已占用，不需要识别具体管理面板样式。
        page.mouse.click(x,y)
        time.sleep(1.2)
        verify=screenshot_img(page)
        still_empty=plant_panel_present(verify)
        events.append({"t":round(time.time(),2),"action":"plant_grid_reprobe_verify",
                       "plant_no":planted+1,"plot_no":plot_no,
                       "x":round(x,1),"y":round(y,1),
                       "plant_panel":bool(still_empty)})
        print("[VISION]",events[-1],flush=True)

        if still_empty:
            page.screenshot(path=str(OUT/"plant_verify_failed.png"),full_page=True)
            page.mouse.click(470,430)
            time.sleep(0.5)
            raise RuntimeError(f"第 {plot_no} 格确认空地后补种失败：回点仍出现选种面板")

        planted+=1
        page.mouse.click(470,430)
        time.sleep(0.5)
        if planted % 5 == 0:
            page.screenshot(path=str(OUT/f"plant_progress_{planted}.png"),full_page=True)

    page.screenshot(path=str(OUT/"after_full_plant.png"),full_page=True)
    events.append({"t":round(time.time(),2),"action":"full_plant_summary",
                   "planted":planted,"plots_probed":len(centers),
                   "empty_panels_seen":empty_seen,"occupied_skipped":occupied_seen,
                   "mode":"grid_6x6_ui_oracle"})
    print("[VISION]",events[-1],flush=True)

'''

s = s[:start_fn] + probe + s[end_fn:]
p.write_text(s, encoding="utf-8")
print("patched 6x6 UI-oracle planting; tan empty detector retired")
