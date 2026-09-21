import time, json
from pathlib import Path
import cv2, numpy as np
from playwright.sync_api import sync_playwright
import recorder

OUT=Path("v2/popup-probe")
OUT.mkdir(parents=True,exist_ok=True)
AUTH="/tmp/xddq19/storage_state.json"
HOME_URL="https://www.wanyiwan.top/home"
TEMPLATES={
    "enter_game_tpl": ("v2/templates/enter_game_small.jpg", 0.80),
    "notice_x": ("v2/templates/notice_x.png", 0.86),
    "event_x": ("v2/templates/event_x.png", 0.86),
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
    # “连接失败，返回登陆界面”的橙黄色“确定”按钮。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=350,560,600,700
    roi=hsv[y0:y1,x0:x1]
    mask=cv2.inRange(roi,np.array([5,80,100]),np.array([35,255,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(mask)
    best=None
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        if area < 1800 or w < 80 or h < 30:
            continue
        if best is None or area>best[0]:
            best=(area,(float(cent[i][0]+x0),float(cent[i][1]+y0)))
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

    launched=recorder.enter_xddq_from_portal(page)
    if launched:
        page=launched
    elif "/game/xddq" in page.url:
        # 入口已经切到寻道页面，只是游戏 iframe / WebSocket 还没来得及建立。
        # 这里继续等待，不能过早判失败。
        print("[+] 已进入 /game/xddq，继续等待游戏本体加载",flush=True)
    else:
        page.screenshot(path=str(OUT/"launch_failed.png"),full_page=True)
        raise RuntimeError("已登录首页，但未能进入寻道大千页面")
    time.sleep(12)

    events=[]
    clicked_dongfu=False
    deadline=time.time()+600
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
                    page.goto(HOME_URL,wait_until="domcontentloaded",timeout=60000)
                    time.sleep(8)
                    relaunched=recorder.enter_xddq_from_portal(page)
                    if relaunched:
                        page=relaunched
                        time.sleep(12)
                        events.append({"t":round(time.time(),2),"action":"relaunch_after_connection_failure"})
                        print("[VISION]",events[-1],flush=True)
                except Exception as e:
                    print("[!] 重连恢复失败:",repr(e),flush=True)

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

        # 启动画面“踏入仙途”改用模板匹配，避免公告页/加载页误触。
        if not action and now-last_click.get("enter_game_tpl",0) >= 15:
            info=matches.get("enter_game_tpl")
            if info and info["score"] >= info["threshold"]:
                page.mouse.click(info["x"],info["y"])
                last_click["enter_game_tpl"]=now
                action="enter_game_tpl"
                events.append({"t":round(now,2),"action":"enter_game_tpl","score":round(info["score"],4),"x":round(info["x"],1),"y":round(info["y"],1)})
                print("[VISION]",events[-1],flush=True)
                time.sleep(12)

        # 真正进入主界面后，点击底部“洞府”。
        if not action:
            dp=main_dongfu_point(img)
            if dp:
                page.mouse.click(dp[0],dp[1])
                last_click["dongfu_main"]=now
                action="dongfu_main"
                clicked_dongfu=True
                events.append({"t":round(now,2),"action":"dongfu_main","x":dp[0],"y":dp[1]})
                print("[VISION]",events[-1],flush=True)
                time.sleep(10)

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
