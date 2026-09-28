from pathlib import Path

p = Path("v2/probe_popup.py")
s = p.read_text(encoding="utf-8")

anchor = '''    # 第二类：#117/#121 “归墟战场”等白金色 X。\n'''
if anchor not in s:
    raise SystemExit("event poster second-type anchor not found")

block = r'''    # 第三类：#142 “玄境修行”竹叶绿海报。右上 X 约 23x25，中心 (655,212)。
    # 这个海报的大面积浅绿背景会和旧的“白金色 X”阈值连成一块，
    # 所以这里用更严格的低饱和高亮掩码和更小的位置窗口单独识别。
    x0,y0,x1,y1=638,195,670,230
    roi=hsv[y0:y1,x0:x1]
    if roi.size:
        bright=cv2.inRange(roi,np.array([0,0,220]),np.array([180,70,255]))
        n,labels,stats,cent=cv2.connectedComponentsWithStats(bright)
        candidates=[]
        for i in range(1,n):
            x,y,w,h,area=stats[i]
            cx=float(cent[i][0]+x0); cy=float(cent[i][1]+y0)
            ratio=w/float(max(1,h))
            if not (150 <= area <= 320 and 18 <= w <= 28 and 20 <= h <= 30):
                continue
            if not (0.65 <= ratio <= 1.25):
                continue
            if not (650 <= cx <= 660 and 206 <= cy <= 218):
                continue
            score=abs(w-h)*2.0 + abs(cx-655.0) + abs(cy-212.0)
            candidates.append((score,-area,(cx,cy)))
        if candidates:
            candidates.sort(key=lambda z:(z[0],z[1]))
            return candidates[0][2]

'''

s = s.replace(anchor, block + anchor, 1)
p.write_text(s, encoding="utf-8")
print("patched #142 xuanjing poster X detector at ~655,212")
