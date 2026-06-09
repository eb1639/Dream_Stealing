"""以 雪地地图像素版.png 为真源, 重建 map_snow.json 的 matrix.
   像素色 -> 矩阵值:
     (255,255,255) 0 走廊
     (255,235, 59) 1 房间
     (  0,  0,  0) 2 墙体
     ( 33,150,243) 3 蓝格门
     (244, 67, 54) 4 红格(进门箭头)
     ( 76,175, 80) 5 出生点
"""
import json
from PIL import Image
from collections import Counter

PNG = r"d:\pycharm\pythonProject\Dream_Stealing\雪地地图像素版.png"
OUT = r"d:\pycharm\pythonProject\Dream_Stealing\world\config\map_snow.json"
COLS, ROWS = 33, 39

# 渲染器用的精确色 (与 tools/render_snow_map.py 保持一致)
PALETTE = {
    0: (255, 255, 255),
    1: (255, 235,  59),
    2: (  0,   0,   0),
    3: ( 33, 150, 243),
    4: (244,  67,  54),
    5: ( 76, 175,  80),
}


def nearest(rgb):
    r, g, b = rgb
    best, best_d = None, 1e18
    for k, (pr, pg, pb) in PALETTE.items():
        d = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
        if d < best_d:
            best_d = d
            best = k
    return best


im = Image.open(PNG).convert("RGB")
W, H = im.size
print(f"PNG 尺寸: {W}x{H}  (期望 {COLS}x{ROWS} 网格)")

# 推断每格像素大小: PNG 中格子外有 PAD=20 边距, 单格 CELL=22
PAD, CELL = 20, 22
assert W == PAD * 2 + COLS * CELL, f"宽度不符: {W} vs {PAD*2 + COLS*CELL}"
assert H == PAD * 2 + ROWS * CELL, f"高度不符: {H} vs {PAD*2 + ROWS*CELL}"

matrix = []
for r in range(ROWS):
    row = []
    for c in range(COLS):
        x0 = PAD + c * CELL
        y0 = PAD + r * CELL
        x1 = x0 + CELL
        y1 = y0 + CELL
        # 中心 50% 区域采样, 避开网格线
        sx0 = x0 + CELL // 4
        sy0 = y0 + CELL // 4
        sx1 = x0 + 3 * CELL // 4
        sy1 = y0 + 3 * CELL // 4
        crop = im.crop((sx0, sy0, sx1, sy1))
        px = list(crop.getdata())
        ar = sum(p[0] for p in px) / len(px)
        ag = sum(p[1] for p in px) / len(px)
        ab = sum(p[2] for p in px) / len(px)
        row.append(nearest((ar, ag, ab)))
    matrix.append(row)

cnt = Counter(v for row in matrix for v in row)
print("矩阵统计:", dict(cnt), "总数:", sum(cnt.values()))

# 加载已有 JSON 保留其他字段, 只重写 matrix
with open(OUT, "r", encoding="utf-8") as f:
    data = json.load(f)

# 删掉顶层冗余字段(由 build_map 从矩阵自动生成)
data.pop("door_pairs", None)
data.pop("spawn_points", None)
data.pop("path_cells", None)
data.pop("fountain", None)

data["matrix"] = matrix
data["grid_width"]  = COLS
data["grid_height"] = ROWS

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"已重建: {OUT}")
