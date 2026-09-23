from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

# patch_grid_harvest.py 会先把丹界点击点从 575 右移到 625，
# 所以这里不能死盯旧 return 文本。两种运行时形态都接受，最终统一保留 625。
needle_575 = '''    lf=pale_frac(left)\n    rf=pale_frac(right_bottom)\n    if lf >= 0.65 and rf >= 0.45:\n        # 当前固定 1280x960 画布中，“丹界”卡片中心约为 (575,785)。\n        return (575.0,785.0,lf,rf)\n'''
needle_625 = '''    lf=pale_frac(left)\n    rf=pale_frac(right_bottom)\n    if lf >= 0.65 and rf >= 0.45:\n        # 当前固定 1280x960 画布中，“丹界”卡片中心约为 (575,785)。\n        return (625.0,785.0,lf,rf)\n'''
replacement = '''    lf=pale_frac(left)\n    rf=pale_frac(right_bottom)\n    # #99 现场证明“公告”大白页会同时把左列和右下判成浅色，\n    # 从而被误认成洞府菜单。真洞府菜单的右侧中段是游戏背景，几乎不浅；\n    # 公告正文在同一区域则接近整片灰白。用这个结构差异做硬排除。\n    right_mid=hsv[250:700,480:680]\n    mf=pale_frac(right_mid)\n    if lf >= 0.65 and rf >= 0.45 and mf <= 0.30:\n        # 丹界点击点右移以避开黄色引导手。\n        return (625.0,785.0,lf,rf)\n'''

if needle_625 in s:
    s = s.replace(needle_625, replacement, 1)
elif needle_575 in s:
    s = s.replace(needle_575, replacement, 1)
else:
    raise SystemExit("dongfu menu detector block not found in 575/625 form")

p.write_text(s, encoding="utf-8")
print("patched strict dongfu-menu guard; reject announcement white page; keep x=625")
