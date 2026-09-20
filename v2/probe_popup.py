import time, json
from pathlib import Path
import cv2, numpy as np
from playwright.sync_api import sync_playwright
import recorder

OUT=Path("v2/popup-probe")
OUT.mkdir(parents=True,exist_ok=True)
AUTH="/tmp/xddq20/qr/storage_state.json"
HOME_URL="https://www.wanyiwan.top/home"
TEMPLATES={
    "notice_x": ("v2/templates/notice_x.png", 0.86),
    "event_x": ("v2/templates/event_x.png", 0.86),
    "continue": ("v2/templates/continue.png", 0.84),
    "dongfu": ("v2/templates/dongfu.png", 0.84),
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

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(storage_state=AUTH,viewport={"width":1280,"height":960})
    page=context.new_page()
    page.goto(HOME_URL,wait_until="domcontentloaded",timeout=60000)
    time.sleep(8)

    launched=recorder.enter_xddq_from_portal(page)
    if not launched:
        page.screenshot(path=str(OUT/"launch_failed.png"),full_page=True)
        raise RuntimeError("已登录首页，但未能从大厅启动寻道大千")
    page=launched
    time.sleep(12)

    events=[]
    clicked_dongfu=False
    deadline=time.time()+210
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
        # 弹窗优先关闭；网络提示其次；主界面最后进洞府。
        for name in ("notice_x","event_x","continue","dongfu"):
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
