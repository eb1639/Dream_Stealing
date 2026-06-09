"""最终把 jpg 转成的 33x39 矩阵写入 map_snow.json (只留 matrix, 删掉顶层冗余字段)."""
import json
from PIL import Image
from collections import Counter

IMG = r"d:\pycharm\pythonProject\Dream_Stealing\雪地地图.jpg"
OUT = r"d:\pycharm\pythonProject\Dream_Stealing\world\config\map_snow.json"
COLS, ROWS = 33, 39

PALETTE = {
    0: (224, 224, 224),
    1: (224, 192,  96),
    2: ( 64,  64,  64),
    3: ( 32,  96, 192),
    4: (192,  32,  32),
    5: ( 96, 224,  64),
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


im = Image.open(IMG).convert("RGB")
W, H = im.size
cw, ch = W / COLS, H / ROWS

matrix = []
for r in range(ROWS):
    row = []
    for c in range(COLS):
        x0 = int(c * cw); y0 = int(r * ch)
        x1 = int((c+1) * cw); y1 = int((r+1) * ch)
        sx0 = x0 + (x1-x0)//4; sy0 = y0 + (y1-y0)//4
        sx1 = x0 + 3*(x1-x0)//4; sy1 = y0 + 3*(y1-y0)//4
        crop = im.crop((sx0, sy0, sx1, sy1))
        px = list(crop.getdata())
        ar = sum(p[0] for p in px) / len(px)
        ag = sum(p[1] for p in px) / len(px)
        ab = sum(p[2] for p in px) / len(px)
        row.append(nearest((ar, ag, ab)))
    matrix.append(row)

cnt = Counter(v for row in matrix for v in row)
print("新矩阵统计:", dict(cnt), "总数:", sum(cnt.values()))

with open(OUT, "r", encoding="utf-8") as f:
    data = json.load(f)

data["matrix"] = matrix
data["grid_width"]  = COLS
data["grid_height"] = ROWS

# 用户要求: 只用矩阵, 删掉顶层冗余字段
data.pop("door_pairs", None)
data.pop("spawn_points", None)
data.pop("path_cells", None)
data.pop("fountain", None)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"已写入: {OUT}")
