from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

needle = '''    lf=pale_frac(left)\n    rf=pale_frac(right_bottom)\n    if lf >= 0.65 and rf >= 0.45:\n        # 当前固定 1280x960 画布中，“丹界”卡片中心约为 (575,785)。\n        return (575.0,785.0,lf,rf)\n'''
replacement = '''    lf=pale_frac(left)\n    rf=pale_frac(right_bottom)\n    # #99 现场证明“公告”大白页会同时把左列和右下判成浅色，\n    # 从而被误认成洞府菜单。真洞府菜单的右侧中段是游戏背景，几乎不浅；\n    # 公告正文在同一区域则接近整片灰白。用这个结构差异做硬排除。\n    right_mid=hsv[250:700,480:680]\n    mf=pale_frac(right_mid)\n    if lf >= 0.65 and rf >= 0.45 and mf <= 0.30:\n        # 当前固定 1280x960 画布中，“丹界”卡片中心约为 (575,785)。\n        return (575.0,785.0,lf,rf)\n'''

if needle not in s:
    raise SystemExit("dongfu menu detector block not found")

s = s.replace(needle, replacement, 1)
p.write_text(s, encoding="utf-8")
print("patched strict dongfu-menu guard; reject announcement white page")
