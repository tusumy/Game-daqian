# explicit V2 probe rerun after maintenance
import time, json
from pathlib import Path
import cv2, numpy as np
from playwright.sync_api import sync_playwright

OUT=Path("v2/popup-probe")
OUT.mkdir(parents=True,exist_ok=True)
AUTH="/tmp/xddq29/storage_state.json"
HOME_URL="https://www.wanyiwan.top/home"
GAME_URL="https://www.wanyiwan.top/game/xddq"
TEMPLATES={
    "notice_x": ("v2/templates/notice_x.png", 0.86),
    "event_x": ("v2/templates/event_x.png", 0.86),
    "daily_no_remind": ("v2/templates/daily_no_remind.png", 0.78),
    "officer_no_remind": ("v2/templates/officer_no_remind.png", 0.80),
}

def best_match(img, tpl_path):
    tpl=cv2.imread(tpl_path, cv2.IMREAD_COLOR)
    if tpl is None: return None
    if img.shape[0] < tpl.shape[0] or img.shape[1] < tpl.shape[1]: return None
    res=cv2.matchTemplate(img,tpl,cv2.TM_CCOEFF_NORMED)
    _,score,_,loc=cv2.minMaxLoc(res)
    h,w=tpl.shape[:2]
    return score,(loc[0]+w/2,loc[1]+h/2)

def screenshot_img(page):
    raw=page.screenshot(full_page=True)
    return cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)

def reward_overlay_present(img):
    # 真正的“恭喜获得”奖励层在游戏区域中部有一整块宽大的棕金色横板。
    # 活动海报（造化灵植/鬼修来袭等）虽然也有金色字，但不会有这块大棕板。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    roi=hsv[350:530,228:710]
    brown=cv2.inRange(roi,np.array([5,40,40]),np.array([35,220,210]))
    frac=cv2.countNonZero(brown)/float(roi.shape[0]*roi.shape[1])
    return frac > 0.60

def profile_overlay_present(img):
    # 点洞府后偶发“北斗星君 / 仙王后期 / 本次登录不再提示”覆盖层。
    # 只检测它下方中间那枚橙色境界按钮，避免把别的橙色 UI 当成覆盖层。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=400,700,550,780
    roi=hsv[y0:y1,x0:x1]
    mask=cv2.inRange(roi,np.array([0,70,100]),np.array([35,255,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(mask)
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
        if area >= 1200 and 85 <= w <= 140 and 28 <= h <= 60 and 450 <= cx <= 500 and 720 <= cy <= 760:
            return True
    return False

def main_dongfu_point(img):
    # 主界面底部中央有一枚很大的金色圆盘；这是比旧“洞府”小图标模板
    # 稳定得多的主界面锚点。只有识别到它，才点击左下“洞府”。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=390,800,560,950
    roi=hsv[y0:y1,x0:x1]
    gold=cv2.inRange(roi,np.array([12,60,90]),np.array([45,255,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(gold)
    best=None
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        if area < 2500 or w < 55 or h < 55:
            continue
        if best is None or area > best[0]:
            best=(area,w,h)
    if not best:
        return None
    # 当前 1280x960 页面中，洞府按钮中心约在 (368, 920)。
    return (368.0,920.0)

def enter_game_point(img):
    # “踏入仙途”只出现在启动画面的下部中间。
    h,w=img.shape[:2]
    if h < 850 or w < 800:
        return None
    x0,y0,x1,y1=360,740,600,830
    roi=img[y0:y1,x0:x1]
    hsv=cv2.cvtColor(roi,cv2.COLOR_BGR2HSV)
    green=cv2.inRange(hsv,np.array([35,35,150]),np.array([100,255,255]))
    white=cv2.inRange(hsv,np.array([0,0,190]),np.array([180,80,255]))
    score=int(cv2.countNonZero(green))+int(cv2.countNonZero(white))
    if score < 2200:
        return None
    return (480.0,790.0)

def network_continue_point(img):
    # 网络提示的两个按钮位置/尺寸很固定：
    # 左橙“重启”约 x=374,y=603；右绿“继续”约 x=575,y=603。
    # 同时命中这两个矩形才确认弹窗存在，避免把加载页颜色误判成按钮。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)

    def box_component(x0,y0,x1,y1,lo,hi):
        roi=hsv[y0:y1,x0:x1]
        mask=cv2.inRange(roi,np.array(lo),np.array(hi))
        n,labels,stats,cent=cv2.connectedComponentsWithStats(mask)
        best=None
        for i in range(1,n):
            x,y,w,h,area=stats[i]
            if not (70 <= w <= 170 and 24 <= h <= 65 and area >= 1500):
                continue
            cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
            if best is None or area>best[0]:
                best=(area,(cx,cy,w,h))
        return best

    orange=box_component(300,560,460,650,[0,70,90],[30,255,255])
    green=box_component(500,560,650,650,[35,45,70],[100,255,255])
    if not orange or not green:
        return None

    ox,oy,ow,oh=orange[1]
    gx,gy,gw,gh=green[1]
    if abs(oy-gy) > 18:
        return None
    if not (345 <= ox <= 420 and 540 <= gx <= 610 and 580 <= gy <= 625):
        return None
    return (gx,gy)

def connection_confirm_point(img):
    # “连接失败，返回登陆界面”的单独橙黄色“确定”按钮。
    # 它的中心在页面更靠右的位置；网络提示左侧“重启”在 x≈394，不能混淆。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=450,560,620,680
    roi=hsv[y0:y1,x0:x1]
    mask=cv2.inRange(roi,np.array([5,80,100]),np.array([35,255,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(mask)
    best=None
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        if area < 1500 or not (75 <= w <= 160 and 25 <= h <= 65):
            continue
        cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
        if not (480 <= cx <= 565 and 590 <= cy <= 645):
            continue
        if best is None or area>best[0]:
            best=(area,(cx,cy))
    return best[1] if best else None

def privacy_agree_point(img):
    # “个人信息保护提示”的绿色“同意”按钮位于游戏画面中下部。
    # 只在这块有限区域寻找大面积高饱和绿色矩形，避免误点游戏内其它元素。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=400,560,700,700
    roi=hsv[y0:y1,x0:x1]
    mask=cv2.inRange(roi,np.array([35,80,80]),np.array([95,255,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(mask)
    best=None
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        if area < 1800 or w < 80 or h < 30:
            continue
        score=area
        if best is None or score>best[0]:
            best=(score,(float(cent[i][0]+x0),float(cent[i][1]+y0)))
    return best[1] if best else None

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(storage_state=AUTH,viewport={"width":1280,"height":960})
    page=context.new_page()
    page.goto(HOME_URL,wait_until="domcontentloaded",timeout=60000)
    time.sleep(8)

    # 大厅轮播偶尔会错误打开其它游戏（例如 sc33t）。
    # 已有登录状态后不再赌轮播：先访问首页确认会话，再直达寻道大千固定 URL。
    page.goto(GAME_URL,wait_until="domcontentloaded",timeout=60000)
    print(f"[PAGE] 直达寻道大千 url={page.url} title={page.title()!r}",flush=True)
    if "/game/xddq" not in page.url:
        page.screenshot(path=str(OUT/"launch_failed.png"),full_page=True)
        raise RuntimeError(f"直达寻道大千失败，当前 url={page.url}")
    time.sleep(12)

    events=[]
    clicked_dongfu=False
    deadline=time.time()+1500
    last_click={}

    while time.time()<deadline and not clicked_dongfu:
        img=screenshot_img(page)
        now=time.time()
        matches={}
        for name,(path,thr) in TEMPLATES.items():
            m=best_match(img,path)
            if m:
                matches[name]={"score":float(m[0]),"x":float(m[1][0]),"y":float(m[1][1]),"threshold":thr}

        action=None

        # “网络状况不佳”优先处理；弹窗存在时绝不去点背后的公告叉。
        if not action and now-last_click.get("network_continue",0) >= 8:
            npnt=network_continue_point(img)
            if npnt:
                page.mouse.click(npnt[0],npnt[1])
                last_click["network_continue"]=now
                action="network_continue"
                events.append({"t":round(now,2),"action":"network_continue","x":round(npnt[0],1),"y":round(npnt[1],1)})
                print("[VISION]",events[-1],flush=True)
                time.sleep(8)

        # 连接失败提示可安全确认；确认后从已登录大厅重新启动一次。
        if not last_click.get("connection_confirm"):
            cp=connection_confirm_point(img)
            if cp:
                page.mouse.click(cp[0],cp[1])
                last_click["connection_confirm"]=now
                action="connection_confirm"
                events.append({"t":round(now,2),"action":"connection_confirm","x":round(cp[0],1),"y":round(cp[1],1)})
                print("[VISION]",events[-1],flush=True)
                time.sleep(6)
                try:
                    # 连接失败后直接回首页刷新会话，再直达寻道大千；
                    # 不再调用可能卡住且会打开错误游戏的大厅轮播逻辑。
                    page.goto(HOME_URL,wait_until="domcontentloaded",timeout=60000)
                    time.sleep(4)
                    page.goto(GAME_URL,wait_until="domcontentloaded",timeout=60000)
                    time.sleep(12)
                    events.append({"t":round(time.time(),2),"action":"relaunch_direct_xddq","url":page.url})
                    print("[VISION]",events[-1],flush=True)
                except Exception as e:
                    print("[!] 直达重连恢复失败:",repr(e),flush=True)

        # 用户已明确授权个人信息保护提示。仅在检测到指定绿色按钮时点击一次。
        if not last_click.get("privacy_agree"):
            p=privacy_agree_point(img)
            if p:
                page.mouse.click(p[0],p[1])
                last_click["privacy_agree"]=now
                action="privacy_agree"
                events.append({"t":round(now,2),"action":"privacy_agree","x":round(p[0],1),"y":round(p[1],1)})
                print("[VISION]",events[-1],flush=True)
                time.sleep(6)

        # 公告刚刚确认关闭后，当前页面就是“踏入仙途”落地页。
        # 只在这个状态下点固定按钮位置，避免公告页/加载页误触。
        if (not action and last_click.get("notice_closed_at")
                and not last_click.get("enter_after_notice")
                and now-last_click["notice_closed_at"] >= 3):
            page.mouse.click(480,790)
            last_click["enter_after_notice"]=now
            action="enter_after_notice"
            events.append({"t":round(now,2),"action":"enter_after_notice","x":480.0,"y":790.0})
            print("[VISION]",events[-1],flush=True)
            time.sleep(15)

        # 每日活动弹窗是常规分支：看到“今日不再提示”就勾上，再关右上角 X。
        if not action:
            di=matches.get("daily_no_remind")
            if di and di["score"] >= di["threshold"]:
                page.mouse.click(di["x"]-42, di["y"])
                time.sleep(1)
                page.mouse.click(655,230)
                last_click["daily_popup"]=now
                action="daily_popup"
                events.append({"t":round(now,2),"action":"daily_popup_no_remind",
                               "score":round(di["score"],4)})
                print("[VISION]",events[-1],flush=True)
                time.sleep(4)

        # 仙官发玉不是必经流程，只在真的出现时处理。
        # 不再勾“本次登录不再提示”：该勾选会弹出“无法获得对应奖励”的二次确认。
        # 让奖励动画完成后直接收掉仙官层，保留本次玉奖励。
        if not action:
            oi=matches.get("officer_no_remind")
            if oi and oi["score"] >= oi["threshold"]:
                time.sleep(4)
                page.mouse.click(690,420)
                last_click["officer_popup"]=now
                action="officer_popup"
                events.append({"t":round(now,2),"action":"officer_reward_dismiss",
                               "score":round(oi["score"],4)})
                print("[VISION]",events[-1],flush=True)
                time.sleep(4)

        # 真正进入主界面后，点击底部“洞府”。
        # 点下去之后不立刻判成功：先连续清掉活动/奖励/资料覆盖层，
        # 直到主界面的金色圆盘锚点消失，才说明页面真的离开主界面。
        if not action:
            dp=main_dongfu_point(img)
            if dp:
                page.mouse.click(dp[0],dp[1])
                last_click["dongfu_main"]=now
                action="dongfu_main"
                events.append({"t":round(now,2),"action":"dongfu_main","x":dp[0],"y":dp[1]})
                print("[VISION]",events[-1],flush=True)
                time.sleep(6)
                page.screenshot(path=str(OUT/"after_first_dongfu_click.png"),full_page=True)

                cleanup_deadline=time.time()+120
                last_dongfu_retry=time.time()
                clear_count=0
                clean_frames=0
                while time.time()<cleanup_deadline:
                    shot=screenshot_img(page)

                    # 洞府必须用正向锚点确认：只有“丹界药田”入口真的出现才算进入成功。
                    # 任何活动海报/确认框把主界面遮住，都不能再被误判成洞府。
                    cave=best_match(shot,"danjie_btn.png")
                    if cave and cave[0] >= 0.70:
                        page.screenshot(path=str(OUT/"actual_dongfu.png"),full_page=True)
                        events.append({"t":round(time.time(),2),"action":"dongfu_verified",
                                       "score":round(float(cave[0]),4),"cleared":clear_count})
                        print("[VISION]",events[-1],flush=True)
                        clicked_dongfu=True
                        break

                    # 每日活动弹窗：勾“今日不再提示”后关闭。
                    dm=best_match(shot,"v2/templates/daily_no_remind.png")
                    if dm and dm[0] >= 0.78:
                        page.mouse.click(dm[1][0]-42,dm[1][1])
                        time.sleep(1)
                        page.mouse.click(655,230)
                        clear_count+=1
                        clean_frames=0
                        events.append({"t":round(time.time(),2),"action":"post_dongfu_daily_no_remind"})
                        print("[VISION]",events[-1],flush=True)
                        time.sleep(4)
                        continue

                    # 仙官发玉：可选分支，先让玉正常发完，再收掉仙官层。
                    # 不勾“不再提示”，避免触发“无法获得对应奖励”的确认框。
                    om=best_match(shot,"v2/templates/officer_no_remind.png")
                    if om and om[0] >= 0.80:
                        time.sleep(4)
                        page.mouse.click(690,420)
                        clear_count+=1
                        clean_frames=0
                        events.append({"t":round(time.time(),2),"action":"post_dongfu_officer_reward_dismiss"})
                        print("[VISION]",events[-1],flush=True)
                        time.sleep(4)
                        continue

                    # 资料提示层：点旁边暗处。
                    if profile_overlay_present(shot):
                        page.mouse.click(250,700)
                        clear_count+=1
                        events.append({"t":round(time.time(),2),"action":"dismiss_profile_overlay","x":250.0,"y":700.0})
                        print("[VISION]",events[-1],flush=True)
                        time.sleep(4)
                        continue

                    # 真正的“恭喜获得”奖励层：点空白处关闭。
                    if reward_overlay_present(shot):
                        page.screenshot(path=str(OUT/"after_dongfu_before_reward_close.png"),full_page=True)
                        page.mouse.click(690,420)
                        clear_count+=1
                        events.append({"t":round(time.time(),2),"action":"dismiss_reward_overlay","x":690.0,"y":420.0})
                        print("[VISION]",events[-1],flush=True)
                        time.sleep(4)
                        continue

                    # 各类活动海报统一优先点右上 X。
                    closed=False
                    for pname in ("event_x","notice_x"):
                        ppath,thr=TEMPLATES[pname]
                        mm=best_match(shot,ppath)
                        if mm and mm[0] >= thr:
                            page.mouse.click(mm[1][0],mm[1][1])
                            clear_count+=1
                            events.append({"t":round(time.time(),2),"action":"post_dongfu_"+pname,
                                           "score":round(float(mm[0]),4),
                                           "x":round(float(mm[1][0]),1),"y":round(float(mm[1][1]),1)})
                            print("[VISION]",events[-1],flush=True)
                            time.sleep(4)
                            closed=True
                            break
                    if closed:
                        continue

                    # 还看得到主界面锚点，说明弹窗清完但洞府并未真正打开，再点一次。
                    still_main=main_dongfu_point(shot)
                    if still_main:
                        if time.time()-last_dongfu_retry >= 6:
                            page.mouse.click(still_main[0],still_main[1])
                            last_dongfu_retry=time.time()
                            events.append({"t":round(time.time(),2),"action":"dongfu_retry",
                                           "x":still_main[0],"y":still_main[1]})
                            print("[VISION]",events[-1],flush=True)
                            time.sleep(6)
                        else:
                            time.sleep(2)
                        continue

                    # 未看到主界面也未看到“丹界药田”时，只能说明有未知覆盖层/过渡画面。
                    # 绝不能再把“主界面消失”当成洞府成功。
                    clean_frames+=1
                    if clean_frames % 3 == 0:
                        page.screenshot(path=str(OUT/"dongfu_unverified.png"),full_page=True)
                        events.append({"t":round(time.time(),2),"action":"dongfu_unverified",
                                       "clean_frames":clean_frames,"cleared":clear_count})
                        print("[VISION]",events[-1],flush=True)
                    time.sleep(2)
                    continue

        # 之后再关其它弹窗、处理网络提示，最后进洞府。
        if not action:
          for name in ("notice_x","event_x"):
              info=matches.get(name)
              if not info or info["score"] < info["threshold"]:
                  continue
              if now-last_click.get(name,0) < 8:
                  continue
              page.mouse.click(info["x"],info["y"])
              last_click[name]=now
              action=name
              if name=="notice_x":
                  last_click["notice_closed_at"]=now
                  last_click.pop("enter_after_notice",None)
              events.append({"t":round(now,2),"action":name,"score":round(info["score"],4),"x":round(info["x"],1),"y":round(info["y"],1)})
              print("[VISION]",events[-1],flush=True)
              time.sleep(4 if name!="dongfu" else 10)
              if name=="dongfu":
                  clicked_dongfu=True
              break

        if not action:
            time.sleep(2)

    page.screenshot(path=str(OUT/"after_vision.png"),full_page=True)
    if clicked_dongfu:
        page.screenshot(path=str(OUT/"after_dongfu_dynamic.png"),full_page=True)
    (OUT/"vision_events.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8")
    context.storage_state(path=str(OUT/"storage_state.json"))
    browser.close()

    if not clicked_dongfu:
        raise RuntimeError("V2 Probe 未看到丹界药田入口，不能判定已进入洞府")
