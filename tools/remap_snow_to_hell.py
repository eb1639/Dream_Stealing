"""把 雪地地图像素版.png 里的色块重映射成炼狱风格, 输出 炼狱地图像素版.png.

色块重映射规则 (与 炼狱地图像素版_初版.png 保持一致, 紫色用 (128, 0, 128)):
    白色 (255, 255, 255) — 走廊  → 紫色 (128, 0, 128)
    绿色 ( 76, 175,  80) — 出生点 → 白色 (255, 255, 255)
    其余色 (墙/房间/门/红格箭头/网格/背景) 保持不变
"""
from PIL import Image

SRC = r"d:\pycharm\pythonProject\Dream_Stealing\雪地地图像素版.png"
DST = r"d:\pycharm\pythonProject\Dream_Stealing\炼狱地图像素版.png"

# 原图调色板 (RGB) — 与 tools/render_snow_map.py 一致
SRC_PALETTE = {
    (255, 255, 255): "corridor",   # 0 走廊
    (255, 235,  59): "room",       # 1 房间
    (  0,   0,   0): "wall",       # 2 墙体
    ( 33, 150, 243): "door",       # 3 蓝格门
    (244,  67,  54): "arrow",      # 4 红格箭头
    ( 76, 175,  80): "spawn",      # 5 出生点
    (200, 200, 200): "grid",       # 网格线
    (245, 245, 245): "bg",         # 画布外边距
}

# 输出调色板
DST_PALETTE = {
    "corridor": (128,   0, 128),   # 走廊 -> 紫色
    "room":     (255, 235,  59),   # 房间 -> 黄
    "wall":     (  0,   0,   0),   # 墙体 -> 黑
    "door":     ( 33, 150, 243),   # 蓝格门 -> 蓝
    "arrow":    (244,  67,  54),   # 红格箭头 -> 红
    "spawn":    (255, 255, 255),   # 出生点 -> 白
    "grid":     (200, 200, 200),
    "bg":       (245, 245, 245),
}


def nearest_key(rgb):
    """找到与 rgb 距离最近的 SRC_PALETTE 键."""
    r, g, b = rgb
    best, best_d = None, 1 << 30
    for key in SRC_PALETTE:
        kr, kg, kb = key
        d = (r - kr) ** 2 + (g - kg) ** 2 + (b - kb) ** 2
        if d < best_d:
            best_d = d
            best = key
    return best


def main() -> None:
    img = Image.open(SRC).convert("RGB")
    W, H = img.size
    print(f"原图: {SRC}  size={W}x{H}")

    out = Image.new("RGB", (W, H))
    src_px = img.load()
    dst_px = out.load()

    counts = {}
    for y in range(H):
        for x in range(W):
            src_rgb = src_px[x, y]
            key = nearest_key(src_rgb)
            name = SRC_PALETTE[key]
            new_rgb = DST_PALETTE[name]
            dst_px[x, y] = new_rgb
            counts[name] = counts.get(name, 0) + 1

    out.save(DST, "PNG")
    print(f"已保存: {DST}  size={W}x{H}")
    print("色块统计 (重映射后):")
    for name, cnt in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {name:8s}  {cnt:>7d}")


if __name__ == "__main__":
    main()
