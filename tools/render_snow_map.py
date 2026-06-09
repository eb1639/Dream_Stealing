"""根据 map_snow.json 渲染雪地地图的像素网格可视化 PNG."""
import json
from PIL import Image, ImageDraw

JSON_PATH = r"d:\pycharm\pythonProject\Dream_Stealing\world\config\map_snow.json"
OUT_PATH = r"d:\pycharm\pythonProject\Dream_Stealing\雪地地图像素版.png"

# 颜色 (RGB) — 与新矩阵值一一对应
COLOR = {
    0: (255, 255, 255),  # 0 走廊  — 白
    1: (255, 235,  59),  # 1 房间  — 黄
    2: (  0,   0,   0),  # 2 墙体  — 黑
    3: ( 33, 150, 243),  # 3 蓝格门(初始) — 蓝
    4: (244,  67,  54),  # 4 红格(进门箭头) — 红
    5: ( 76, 175,  80),  # 5 猎梦者出生点 — 绿
}
GRID_LINE = (200, 200, 200)  # 浅灰网格线

CELL = 22  # 单格像素大小
PAD  = 20  # 画布外边距


def main() -> None:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    matrix = data["matrix"]
    rows = len(matrix)
    cols = len(matrix[0])
    print(f"地图规模: {cols} x {rows}  (grid_width={data.get('grid_width')}, "
          f"grid_height={data.get('grid_height')})")

    # 校验矩阵
    for i, row in enumerate(matrix):
        if len(row) != cols:
            raise ValueError(f"row {i} 列数 {len(row)} != {cols}")

    # 画布尺寸
    W = PAD * 2 + cols * CELL
    H = PAD * 2 + rows * CELL
    img = Image.new("RGB", (W, H), (245, 245, 245))
    draw = ImageDraw.Draw(img)

    # 填充像素 (值 0/1/2/3/4/5 直接映射颜色)
    for r, row in enumerate(matrix):
        for c, v in enumerate(row):
            x0 = PAD + c * CELL
            y0 = PAD + r * CELL
            x1 = x0 + CELL
            y1 = y0 + CELL
            color = COLOR.get(v, (128, 128, 128))
            draw.rectangle([x0, y0, x1, y1], fill=color)

    # 网格线
    for c in range(cols + 1):
        x = PAD + c * CELL
        draw.line([(x, PAD), (x, PAD + rows * CELL)], fill=GRID_LINE, width=1)
    for r in range(rows + 1):
        y = PAD + r * CELL
        draw.line([(PAD, y), (PAD + cols * CELL, y)], fill=GRID_LINE, width=1)

    # 图例
    legend = [
        ("墙体(2)",   COLOR[2]),
        ("房间(1)",   COLOR[1]),
        ("走廊(0)",   COLOR[0]),
        ("门(3)",     COLOR[3]),
        ("箭头(4)",   COLOR[4]),
        ("出生点(5)", COLOR[5]),
    ]
    lx, ly = PAD, PAD + rows * CELL + 10
    for name, col in legend:
        draw.rectangle([lx, ly, lx + 14, ly + 14], fill=col, outline=(0, 0, 0))
        draw.text((lx + 18, ly - 1), name, fill=(0, 0, 0))
        lx += 18 + 8 * len(name)

    img.save(OUT_PATH, "PNG")
    print(f"已保存: {OUT_PATH}  (尺寸 {W}x{H})")


if __name__ == "__main__":
    main()
