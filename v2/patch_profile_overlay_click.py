from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

# #137 现场证明实验坐标 (500,735) 会在“天仙第一人/星宿福泽”人物覆盖层上
# 原地重复点击，连续十几次都无法推进。#125 使用旧的安全背景点 (250,700)
# 曾成功穿过同类人物覆盖层并最终进入丹界。
# 这里仅撤回点击坐标，不触碰“本次登录不再提示”，继续保留奖励安全保护。
old_click = "page.mouse.click(500,735)"
old_event = '"action":"officer_profile_task_advance","x":500.0,"y":735.0'

if old_click not in s:
    raise SystemExit("#137 profile click anchor not found")
if old_event not in s:
    raise SystemExit("#137 profile event anchor not found")

s = s.replace(old_click, "page.mouse.click(250,700)", 1)
s = s.replace(old_event, '"action":"officer_profile_advance","x":250.0,"y":700.0', 1)

p.write_text(s, encoding="utf-8")
print("patched #137 profile overlay click: revert 500,735 -> proven 250,700; keep no-remind untouched")
