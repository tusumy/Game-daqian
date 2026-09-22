# V2 navigation baseline restored from proven-success run #56
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

def dongfu_menu_danjie_point(img):
    # 新版洞府不是直接出现“丹界药田”按钮，而是先展开一张米白色功能菜单。
    # 左侧长列与右下“丹界/仙途寻宝”两格同时出现时，才认为是真正的洞府菜单。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    left=hsv[210:875,270:475]
    right_bottom=hsv[740:875,480:680]
    if left.size == 0 or right_bottom.size == 0:
        return None
    def pale_frac(roi):
        pale=cv2.inRange(roi,np.array([0,0,140]),np.array([180,110,255]))
        return cv2.countNonZero(pale)/float(pale.size)
    lf=pale_frac(left)
    rf=pale_frac(right_bottom)
    if lf >= 0.65 and rf >= 0.45:
        # 当前固定 1280x960 画布中，“丹界”卡片中心约为 (575,785)。
        return (575.0,785.0,lf,rf)
    return None


def danjie_page_present(img):
    # 丹界药田页面中央大面积为青绿山水/药田，修罗战场、活动海报、主界面都不满足。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    roi=hsv[180:760,228:712]
    if roi.size == 0:
        return None
    green=cv2.inRange(roi,np.array([35,35,50]),np.array([100,255,255]))
    frac=cv2.countNonZero(green)/float(roi.shape[0]*roi.shape[1])
    if frac < 0.45:
        return None

    # 再要求顶部丹界区域也有明显青绿色背景，降低主界面误判。
    top=hsv[95:150,228:500]
    teal=cv2.inRange(top,np.array([60,20,40]),np.array([110,255,255]))
    top_frac=cv2.countNonZero(teal)/float(top.shape[0]*top.shape[1])
    if top_frac < 0.30:
        return None

    return (frac,top_frac)

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

def sdk_restart_point(img):
    # “登录界面初始化失败，请尝试重启游戏！sdk”：
    # 中央白色提示框 + 下方绿色“重启”按钮。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    # 白色/浅灰大弹窗区域
    modal=hsv[360:670,240:700]
    if modal.size == 0:
        return None
    pale=cv2.inRange(modal,np.array([0,0,150]),np.array([180,80,255]))
    pale_frac=cv2.countNonZero(pale)/float(pale.shape[0]*pale.shape[1])
    if pale_frac < 0.45:
        return None

    # 绿色重启按钮
    x0,y0,x1,y1=390,560,560,650
    roi=hsv[y0:y1,x0:x1]
    green=cv2.inRange(roi,np.array([35,50,80]),np.array([95,255,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(green)
    best=None
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
        if area < 1800 or w < 80 or h < 25:
            continue
        if best is None or area > best[0]:
            best=(area,(cx,cy))
    return best[1] if best else None


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


def upgrade_cancel_point(img):
    # “感悟升级”覆盖层没有关闭 X，只有“取消 / 前往”双按钮。
    # 只有同时识别到左侧橙色和右侧绿色的大按钮时才返回“取消”中心，
    # 避免把普通界面里的单个彩色按钮误当成这个弹窗。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=280,700,680,790
    roi=hsv[y0:y1,x0:x1]
    if roi.size == 0:
        return None

    orange=cv2.inRange(roi,np.array([0,80,100]),np.array([20,255,255]))
    green=cv2.inRange(roi,np.array([35,50,100]),np.array([95,255,255]))

    def buttons(mask):
        n,labels,stats,cent=cv2.connectedComponentsWithStats(mask)
        out=[]
        for i in range(1,n):
            x,y,w,h,area=stats[i]
            cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
            if area < 2500 or w < 90 or h < 25:
                continue
            if not (720 <= cy <= 770):
                continue
            out.append((area,cx,cy,w,h))
        return out

    left=[b for b in buttons(orange) if 330 <= b[1] <= 420]
    right=[b for b in buttons(green) if 535 <= b[1] <= 625]
    if not left or not right:
        return None
    a=max(left,key=lambda b:b[0])
    b=max(right,key=lambda b:b[0])
    if abs(a[2]-b[2]) > 15:
        return None
    return (a[1],a[2])


def today_no_remind_point(img):
    # 活动弹窗右下“今日/当天不再提示”前的小方框。
    # 不同活动弹窗位置会有几十像素偏移，所以不能只盯一个 40x35 小框。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=470,760,630,875
    roi=hsv[y0:y1,x0:x1]
    if roi.size == 0:
        return None

    # 复选框通常是浅灰/米白/浅金的小方块，尺寸约 8~22 px。
    pale=cv2.inRange(roi,np.array([0,0,110]),np.array([180,150,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(pale)
    candidates=[]
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
        if not (7 <= w <= 24 and 7 <= h <= 24 and 20 <= area <= 320):
            continue
        if abs(w-h) > 7:
            continue
        # 复选框一般在弹窗底部右侧偏中间的位置。
        if not (500 <= cx <= 585 and 790 <= cy <= 855):
            continue
        fill=area/float(max(1,w*h))
        if fill < 0.18:
            continue
        candidates.append((area,abs(cx-537)+abs(cy-829),(cx,cy)))
    if not candidates:
        return None
    candidates.sort(key=lambda z:(z[1],-z[0]))
    return candidates[0][2]

def scene_change_score(a,b):
    # 判断点关闭键后主游戏区域是否真的发生明显变化。
    # 先缩小再比较，降低角色小动画/粒子动画造成的噪声。
    ra=a[120:900,228:712]
    rb=b[120:900,228:712]
    if ra.size == 0 or rb.size == 0 or ra.shape != rb.shape:
        return 999.0
    ga=cv2.cvtColor(ra,cv2.COLOR_BGR2GRAY)
    gb=cv2.cvtColor(rb,cv2.COLOR_BGR2GRAY)
    ga=cv2.resize(ga,(64,96),interpolation=cv2.INTER_AREA)
    gb=cv2.resize(gb,(64,96),interpolation=cv2.INTER_AREA)
    return float(np.mean(cv2.absdiff(ga,gb)))


def nested_page_back_point(img):
    # “天魔古域”等完整活动页不是弹窗，左上角有青白色返回箭头。
    # 这类页面若误入，直接返回主界面再继续洞府流程。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=235,95,300,145
    roi=hsv[y0:y1,x0:x1]
    if roi.size == 0:
        return None
    # 兼容青色/浅白箭头
    cyan=cv2.inRange(roi,np.array([75,20,130]),np.array([110,255,255]))
    pale=cv2.inRange(roi,np.array([0,0,180]),np.array([180,90,255]))
    mask=cv2.bitwise_or(cyan,pale)
    n,labels,stats,cent=cv2.connectedComponentsWithStats(mask)
    best=None
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
        if area < 80 or w < 18 or h < 10:
            continue
        if not (245 <= cx <= 275 and 105 <= cy <= 135):
            continue
        if best is None or area > best[0]:
            best=(area,(cx,cy))
    return best[1] if best else None


def promo_yellow_x_point(img):
    # “高额返利/充值”类推广弹窗：关闭键是右上偏下的黄色 X，
    # 位置约在页面 (675,300)，与普通活动海报的白色 X 不同。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=640,270,705,335
    roi=hsv[y0:y1,x0:x1]
    if roi.size == 0:
        return None
    yellow=cv2.inRange(roi,np.array([18,90,120]),np.array([42,255,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(yellow)
    best=None
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
        if area < 35 or w < 8 or h < 8:
            continue
        if not (660 <= cx <= 690 and 285 <= cy <= 315):
            continue
        if best is None or area > best[0]:
            best=(area,(cx,cy))
    return best[1] if best else None


def modal_close_point(img):
    # 洞府入口前的活动海报虽然样式会变，但右上关闭 X 基本固定在 x≈655,y≈230。
    # 只在这块很小的区域检测高亮 X，避免把活动海报遮住主界面误判成“已进洞府”。
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    x0,y0,x1,y1=630,205,685,260
    roi=hsv[y0:y1,x0:x1]
    if roi.size == 0:
        return None
    bright=cv2.inRange(roi,np.array([0,0,165]),np.array([180,255,255]))
    n,labels,stats,cent=cv2.connectedComponentsWithStats(bright)
    best=None
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
        if area < 20 or w < 6 or h < 6:
            continue
        if not (642 <= cx <= 675 and 215 <= cy <= 250):
            continue
        if best is None or area > best[0]:
            best=(area,(cx,cy))
    return best[1] if best else None

def probe_existing_plant(page, events):
    # 丹界验证成功后只收一株成熟灵植：先点成熟作物，再点弹出的左侧“收获”。
    # 绝不点击右侧“一键收获”，避免一次性收掉全部药田。
    x,y=451.0,526.0
    page.screenshot(path=str(OUT/"before_plant_probe.png"),full_page=True)
    page.mouse.click(x,y)
    events.append({"t":round(time.time(),2),"action":"mature_plant_probe_click","x":x,"y":y})
    print("[VISION]",events[-1],flush=True)
    time.sleep(3)
    page.screenshot(path=str(OUT/"after_plant_probe.png"),full_page=True)

    # 当前“特权”菜单：左侧“收获”按钮中心约在 (425,625)。
    hx,hy=425.0,625.0
    page.mouse.click(hx,hy)
    events.append({"t":round(time.time(),2),"action":"single_harvest_click","x":hx,"y":hy})
    print("[VISION]",events[-1],flush=True)
    time.sleep(4)
    page.screenshot(path=str(OUT/"after_single_harvest.png"),full_page=True)


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
    danjie_entry_clicked=False
    abort_reason=None
    deadline=time.time()+540
    last_click={}

    while time.time()<deadline and not clicked_dongfu and not abort_reason:
        img=screenshot_img(page)
        now=time.time()
        matches={}
        for name,(path,thr) in TEMPLATES.items():
            m=best_match(img,path)
            if m:
                matches[name]={"score":float(m[0]),"x":float(m[1][0]),"y":float(m[1][1]),"threshold":thr}

        action=None

        # SDK 登录初始化失败：优先点绿色“重启”，再等待游戏重新拉起。
        if not action and now-last_click.get("sdk_restart",0) >= 12:
            sp=sdk_restart_point(img)
            if sp:
                page.mouse.click(sp[0],sp[1])
                last_click["sdk_restart"]=now
                action="sdk_restart"
                events.append({"t":round(now,2),"action":"sdk_restart",
                               "x":round(sp[0],1),"y":round(sp[1],1)})
                print("[VISION]",events[-1],flush=True)
                time.sleep(15)

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

        # 如果洞府菜单已经打开，即使上一轮“清弹窗窗口”刚好超时，
        # 也要在外层主循环立刻接住它并进入丹界，不能眼睁睁停在菜单上。
        if not action and not danjie_entry_clicked:
            menu=dongfu_menu_danjie_point(img)
            if menu:
                page.screenshot(path=str(OUT/"actual_dongfu_menu_outer.png"),full_page=True)
                page.mouse.click(menu[0],menu[1])
                danjie_entry_clicked=True
                action="dongfu_menu_danjie_outer"
                events.append({"t":round(now,2),"action":"dongfu_menu_danjie_outer",
                               "x":menu[0],"y":menu[1],
                               "left_pale":round(menu[2],3),"right_pale":round(menu[3],3)})
                print("[VISION]",events[-1],flush=True)

                transition_deadline=time.time()+45
                transitioned=False
                while time.time()<transition_deadline:
                    time.sleep(3)
                    nxt=screenshot_img(page)
                    if danjie_page_present(nxt):
                        time.sleep(4)
                        page.screenshot(path=str(OUT/"after_danjie_transition.png"),full_page=True)
                        events.append({"t":round(time.time(),2),"action":"danjie_page_positive"})
                        print("[VISION]",events[-1],flush=True)
                        transitioned=True
                        break
                if not transitioned:
                    page.screenshot(path=str(OUT/"after_danjie_click_loading.png"),full_page=True)
                    abort_reason="点击丹界后 45 秒洞府菜单仍未消失；已保存加载现场"
                else:
                    page.screenshot(path=str(OUT/"actual_danjie.png"),full_page=True)
                    events.append({"t":round(time.time(),2),"action":"danjie_verified"})
                    print("[VISION]",events[-1],flush=True)
                    probe_existing_plant(page,events)
                    clicked_dongfu=True
                continue

        # 明确的“恭喜获得”奖励层优先收掉；这是固定覆盖层，不做泛化返回。
        if not action and reward_overlay_present(img):
            page.mouse.click(690,420)
            action="outer_reward_dismiss"
            events.append({"t":round(now,2),"action":"outer_reward_dismiss","x":690.0,"y":420.0})
            print("[VISION]",events[-1],flush=True)
            time.sleep(4)

        # “2500%高额返利”等充值推广：黄色 X 在普通关闭区域更下方。
        if not action:
            yp=promo_yellow_x_point(img)
            if yp:
                page.mouse.click(yp[0],yp[1])
                action="promo_yellow_x"
                events.append({"t":round(now,2),"action":"promo_yellow_x",
                               "x":round(yp[0],1),"y":round(yp[1],1)})
                print("[VISION]",events[-1],flush=True)
                time.sleep(3)

        # 内层清弹窗窗口结束后，仍可能晚到一张新的活动海报（如“修罗战场”）。
        # 外层只在“当前不是主界面”时启用通用右上 X，避免把主页亮点误当关闭键。
        if not action and not main_dongfu_point(img):
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

                cleanup_deadline=time.time()+90
                last_dongfu_retry=time.time()
                clear_count=0
                clean_frames=0
                while time.time()<cleanup_deadline:
                    shot=screenshot_img(page)

                    # 先识别新版洞府菜单；当前 UI 需要在菜单右下再点一次“丹界”。
                    menu=dongfu_menu_danjie_point(shot)
                    if menu and not danjie_entry_clicked:
                        page.screenshot(path=str(OUT/"actual_dongfu_menu.png"),full_page=True)
                        page.mouse.click(menu[0],menu[1])
                        danjie_entry_clicked=True
                        events.append({"t":round(time.time(),2),"action":"dongfu_menu_danjie",
                                       "x":menu[0],"y":menu[1],
                                       "left_pale":round(menu[2],3),"right_pale":round(menu[3],3)})
                        print("[VISION]",events[-1],flush=True)

                        # 点中丹界后会出现加载圈，旧版固定 sleep 10 秒会截到半途。
                        # 最多等 45 秒，直到真正识别到青绿色丹界药田页，再保存下一页真实画面。
                        transition_deadline=time.time()+45
                        transitioned=False
                        while time.time()<transition_deadline:
                            time.sleep(3)
                            nxt=screenshot_img(page)
                            if danjie_page_present(nxt):
                                time.sleep(4)
                                page.screenshot(path=str(OUT/"after_danjie_transition.png"),full_page=True)
                                events.append({"t":round(time.time(),2),"action":"danjie_page_positive"})
                                print("[VISION]",events[-1],flush=True)
                                transitioned=True
                                break
                        if not transitioned:
                            page.screenshot(path=str(OUT/"after_danjie_click_loading.png"),full_page=True)
                            abort_reason="点击丹界后 45 秒洞府菜单仍未消失；已保存加载现场"
                        else:
                            page.screenshot(path=str(OUT/"actual_danjie.png"),full_page=True)
                            events.append({"t":round(time.time(),2),"action":"danjie_verified"})
                            print("[VISION]",events[-1],flush=True)
                            probe_existing_plant(page,events)
                            clicked_dongfu=True
                        break

                    # 兼容旧 UI：若旧“丹界药田”模板仍能命中，也允许作为正向锚点。
                    cave=best_match(shot,"danjie_btn.png")
                    if cave and cave[0] >= 0.70:
                        page.screenshot(path=str(OUT/"actual_dongfu.png"),full_page=True)
                        events.append({"t":round(time.time(),2),"action":"dongfu_verified_legacy",
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

                    # 充值推广类黄色 X。
                    yp=promo_yellow_x_point(shot)
                    if yp:
                        page.mouse.click(yp[0],yp[1])
                        clear_count+=1
                        clean_frames=0
                        events.append({"t":round(time.time(),2),"action":"post_dongfu_promo_yellow_x",
                                       "x":round(yp[0],1),"y":round(yp[1],1)})
                        print("[VISION]",events[-1],flush=True)
                        time.sleep(3)
                        continue

                    # 各类活动海报优先处理；如果海报底部有“今日不再提示”，
                    # 先勾上再关 X，避免同一批活动层反复出现。
                    closed=False
                    for pname in ("event_x","notice_x"):
                        ppath,thr=TEMPLATES[pname]
                        mm=best_match(shot,ppath)
                        if mm and mm[0] >= thr:
                            chk=today_no_remind_point(shot) if pname=="event_x" else None
                            if chk:
                                page.mouse.click(chk[0],chk[1])
                                time.sleep(0.8)
                            before_close=screenshot_img(page)
                            page.mouse.click(mm[1][0],mm[1][1])
                            clear_count+=1
                            time.sleep(2)
                            after_close=screenshot_img(page)
                            change=scene_change_score(before_close,after_close)
                            events.append({"t":round(time.time(),2),"action":"post_dongfu_"+pname,
                                           "score":round(float(mm[0]),4),
                                           "x":round(float(mm[1][0]),1),"y":round(float(mm[1][1]),1),
                                           "today_no_remind":bool(chk),"scene_change":round(change,2)})
                            print("[VISION]",events[-1],flush=True)
                            if change < 2.0:
                                page.screenshot(path=str(OUT/"stuck_event_close.png"),full_page=True)
                                abort_reason=f"{pname} 点击关闭后画面未变化"
                                events.append({"t":round(time.time(),2),"action":"popup_close_stuck",
                                               "kind":pname,"scene_change":round(change,2)})
                                print("[VISION]",events[-1],flush=True)
                            closed=True
                            break
                    if abort_reason:
                        break
                    if closed:
                        if clear_count >= 12:
                            page.screenshot(path=str(OUT/"popup_chain_limit.png"),full_page=True)
                            abort_reason="洞府前弹窗链超过 12 层，停止继续盲点"
                            break
                        continue

                    # “感悟升级”没有关闭 X；检测到橙/绿双按钮时点左侧“取消”。
                    up=upgrade_cancel_point(shot)
                    if up:
                        page.mouse.click(up[0],up[1])
                        clear_count+=1
                        clean_frames=0
                        events.append({"t":round(time.time(),2),"action":"post_dongfu_upgrade_cancel",
                                       "x":round(up[0],1),"y":round(up[1],1)})
                        print("[VISION]",events[-1],flush=True)
                        time.sleep(4)
                        continue

                    # 一旦主界面锚点已经恢复，说明前置弹窗都清完了。
                    # 必须优先重试“洞府”，绝不能再让通用 X 去扫描主界面上的亮点。
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

                    # 只有主界面锚点不存在时，才允许使用通用右上 X。
                    # 这样可处理“东海寻珍”等无模板海报，同时避免把主页亮点误当关闭键。
                    mp=modal_close_point(shot)
                    if mp:
                        before_close=shot
                        page.mouse.click(mp[0],mp[1])
                        clear_count+=1
                        clean_frames=0
                        time.sleep(2)
                        after_close=screenshot_img(page)
                        change=scene_change_score(before_close,after_close)
                        events.append({"t":round(time.time(),2),"action":"post_dongfu_modal_x",
                                       "x":round(mp[0],1),"y":round(mp[1],1),
                                       "scene_change":round(change,2)})
                        print("[VISION]",events[-1],flush=True)
                        if change < 2.0:
                            page.screenshot(path=str(OUT/"stuck_modal_x.png"),full_page=True)
                            abort_reason="通用关闭 X 点击后画面未变化"
                            events.append({"t":round(time.time(),2),"action":"popup_close_stuck",
                                           "kind":"modal_x","scene_change":round(change,2)})
                            print("[VISION]",events[-1],flush=True)
                            break
                        if clear_count >= 12:
                            page.screenshot(path=str(OUT/"popup_chain_limit.png"),full_page=True)
                            abort_reason="洞府前弹窗链超过 12 层，停止继续盲点"
                            break
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
              if name=="event_x":
                  chk=today_no_remind_point(img)
                  if chk:
                      page.mouse.click(chk[0],chk[1])
                      time.sleep(0.8)
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

    if abort_reason:
        raise RuntimeError(abort_reason)
    if not clicked_dongfu:
        raise RuntimeError("V2 Probe 未看到丹界药田入口，不能判定已进入洞府")
