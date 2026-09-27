from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

# #135：最后一格实际已经种上，回点后出现的是“浇灵/锄除”管理面板，
# 但结构化 plant_panel_present 把它误认成选种面板，导致 36/36 被假报失败。
# 初次找空地继续使用结构识别；最终验收则只认真正选种面板顶部稳定的
# 黄色“灵植” + 青绿色“造化灵植”双标签，避免把管理面板当空地。
verify_helper = r'''def strict_seed_panel_present(img):
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    left=hsv[535:585,245:385]
    right=hsv[535:585,370:515]
    if left.size == 0 or right.size == 0:
        return False
    yellow=cv2.inRange(left,np.array([15,80,170]),np.array([35,255,255]))
    teal=cv2.inRange(right,np.array([75,50,90]),np.array([110,220,230]))
    yellow_frac=cv2.countNonZero(yellow)/float(left.shape[0]*left.shape[1])
    teal_frac=cv2.countNonZero(teal)/float(right.shape[0]*right.shape[1])
    return yellow_frac >= 0.25 and teal_frac >= 0.25


'''
helper_anchor = "def farm_plot_centers():"
if "def strict_seed_panel_present(img):" not in s:
    if helper_anchor not in s:
        raise SystemExit("farm_plot_centers anchor not found")
    s = s.replace(helper_anchor, verify_helper + helper_anchor, 1)

start = s.find("def farm_plot_centers():")
end = s.find("\n\ndef local_plot_change_score", start)
if start < 0 or end < 0:
    raise SystemExit("farm_plot_centers block not found")

replacement = r'''def farm_plot_centers():
    # #134 现场重新校准：丹界 36 块地不是一个连续 6x6 菱形，
    # 而是四块彼此分开的 3x3 等距田。旧 6x6 公式有 9 个点落在
    # 田块间隙/邻格边缘，导致全空田最终只能稳定补到 27 格。
    blocks = [
        (479.6, 476.8),  # 上方 3x3
        (365.0, 529.6),  # 左侧 3x3
        (597.6, 532.6),  # 右侧 3x3
        (489.1, 585.4),  # 下方 3x3
    ]
    dx, dy = 33.45, 14.90
    pts = []
    for base_x, base_y in blocks:
        for i in range(3):
            for j in range(3):
                pts.append((base_x + dx * (i-j), base_y + dy * (i+j)))
    pts.sort(key=lambda p: (p[1], p[0]))
    return pts
'''

s = s[:start] + replacement + s[end:]
s = s.replace('"mode":"grid_6x6_ui_oracle"', '"mode":"four_3x3_ui_oracle"')
s = s.replace('"mode":"grid_6x6"', '"mode":"four_3x3"')

needle = "still_empty=plant_panel_present(verify)"
if needle not in s:
    raise SystemExit("plant verification anchor not found")
s = s.replace(needle, "still_empty=strict_seed_panel_present(verify)", 1)

p.write_text(s, encoding="utf-8")
print("patched #135 four 3x3 geometry + strict final seed-panel verification")
