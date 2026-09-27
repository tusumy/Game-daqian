from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

start = s.find("def farm_plot_centers():")
end = s.find("\n\ndef local_plot_change_score", start)
if start < 0 or end < 0:
    raise SystemExit("farm_plot_centers block not found")

replacement = r'''def farm_plot_centers():
    # #134 现场重新校准：丹界 36 块地不是一个连续 6x6 菱形，
    # 而是四块彼此分开的 3x3 等距田。旧 6x6 公式有 9 个点落在
    # 田块间隙/邻格边缘，导致全空田最终只能稳定补到 27 格。
    # 以下四个顶点直接取自 before_full_plant.png 的真实裸地中心。
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

p.write_text(s, encoding="utf-8")
print("patched #134 real farm geometry: four separated 3x3 blocks / 36 centers")
