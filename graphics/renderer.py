"""
程序化像素纹理生成 + 地图/实体/建筑绘制
"""
import pygame
import math
from core.config import *
import core.config as _cfg
from entities.entities import *

# ── 纹理缓存: 避免每帧为相同纹理重建Surface ──
_tex_cache = {}


def draw_pixel_texture(surface, x, y, w, h, draw_func, cache_key=None):
    """在(x,y)处创建w×h的子surface并调用draw_func绘制
    cache_key: 若提供则缓存纹理, 相同key直接blit缓存结果
    """
    if cache_key is not None:
        cached = _tex_cache.get(cache_key)
        if cached is not None:
            surface.blit(cached, (x, y))
            return
    sub = pygame.Surface((w, h), pygame.SRCALPHA)
    draw_func(sub, w, h)
    if cache_key is not None:
        _tex_cache[cache_key] = sub
    surface.blit(sub, (x, y))


# ═══════════════════════════════════════
#  纹理生成函数
# ═══════════════════════════════════════

def draw_floor_tile(surf, w, h):
    """浅蓝色砖块纹理(房间地板, 一格一砖)"""
    # 浅蓝主色
    surf.fill((140, 195, 230))
    # 左上高光(从浅到主色的渐变)
    pygame.draw.line(surf, (180, 220, 240), (0, 0), (w - 1, 0), 1)
    pygame.draw.line(surf, (180, 220, 240), (0, 0), (0, h - 1), 1)
    # 右下阴影
    pygame.draw.line(surf, (90, 145, 185), (0, h - 1), (w - 1, h - 1), 1)
    pygame.draw.line(surf, (90, 145, 185), (w - 1, 0), (w - 1, h - 1), 1)
    # 砖块外描边
    pygame.draw.rect(surf, (60, 115, 160), (0, 0, w, h), 1)
    # 中心微高光
    pygame.draw.circle(surf, (200, 230, 250), (w // 2, h // 2), 1)


def draw_wall_tile(surf, w, h):
    """灰色像素砖块纹理, 简洁无苔藓"""
    surf.fill(GRAY)
    brick_h = h // 3
    for row_idx in range(3):
        offset = (row_idx % 2) * (w // 4)
        yr = row_idx * brick_h
        for col_idx in range(4):
            xr = col_idx * (w // 2) + offset
            if xr >= w:
                xr -= w
            # 砖块主体
            brick_rect = (xr + 1, yr + 1, w // 2 - 2, brick_h - 2)
            # 砖块颜色变化(深浅交错)
            if (row_idx + col_idx) % 2 == 0:
                brick_color = (150, 150, 155)
                brick_hi = (180, 180, 185)
            else:
                brick_color = (110, 110, 115)
                brick_hi = (140, 140, 145)
            pygame.draw.rect(surf, brick_color, brick_rect)
            pygame.draw.rect(surf, DARK_GRAY, brick_rect, 1)
            # 砖块高光(顶部)
            pygame.draw.line(surf, brick_hi, (xr + 1, yr + 1), (xr + w // 2 - 3, yr + 1), 1)
            # 砖块阴影(底部)
            pygame.draw.line(surf, (55, 55, 60), (xr + 1, yr + brick_h - 2),
                             (xr + w // 2 - 3, yr + brick_h - 2), 1)


def draw_corridor_tile(surf, w, h):
    """木质地板: 横向木板 + 木纹 + 深浅交错 + 竖向接缝"""
    # 底色
    surf.fill((170, 125, 75))
    # 木板(横向, 每板 8 像素)
    plank_h = 8
    for row in range(0, h, plank_h):
        # 深浅交替
        if (row // plank_h) % 2 == 0:
            base = (180, 135, 85)
            dark = (130, 90, 50)
        else:
            base = (155, 110, 65)
            dark = (110, 75, 40)
        pygame.draw.rect(surf, base, (0, row, w, plank_h))
        # 板间阴影
        pygame.draw.line(surf, dark, (0, row + plank_h - 1), (w, row + plank_h - 1), 1)
        # 木纹细节(横向细纹)
        for y_off in range(1, plank_h, 3):
            pygame.draw.line(surf, dark, (0, row + y_off), (w, row + y_off), 1)
    # 木板竖向接缝(不规则位置, 上下错开)
    seam_rows = [(10, 0, 2), (22, 2, 3), (4, 3, 3)]
    for sx, r_start, r_end in seam_rows:
        y0 = r_start * plank_h
        y1 = min(h, (r_start + r_end) * plank_h)
        pygame.draw.line(surf, (90, 60, 30), (sx, y0), (sx, y1), 1)
    # 顶部高光
    pygame.draw.line(surf, (210, 170, 120), (0, 0), (w, 0), 1)


def draw_corridor_moss(surf, w, h):
    """苔藓走廊: 绿色草地+泥土+小草点缀"""
    # 泥土底色
    surf.fill((85, 110, 60))
    # 草地斑块(深浅交错)
    for row in range(0, h, 8):
        if (row // 8) % 2 == 0:
            base = (75, 130, 55)
        else:
            base = (95, 145, 65)
        pygame.draw.rect(surf, base, (0, row, w, 8))
        # 草纹
        for y_off in range(1, 8, 2):
            pygame.draw.line(surf, (55, 95, 40), (0, row + y_off), (w, row + y_off), 1)
    # 泥土接缝
    for sx in (10, 22):
        pygame.draw.line(surf, (60, 80, 40), (sx, 0), (sx, h), 1)
    # 小草点缀
    for gx, gy in [(5, 12), (18, 6), (28, 22)]:
        pygame.draw.line(surf, (50, 160, 60), (gx, gy), (gx - 1, gy - 3), 1)
        pygame.draw.line(surf, (50, 160, 60), (gx, gy), (gx + 1, gy - 3), 1)
    # 顶部高光
    pygame.draw.line(surf, (120, 175, 90), (0, 0), (w, 0), 1)


def draw_corridor_snow(surf, w, h):
    """冰雪走廊: 白色雪地+冰晶+蓝色阴影"""
    # 雪地底色
    surf.fill((225, 235, 245))
    # 雪纹(深浅交错)
    for row in range(0, h, 8):
        if (row // 8) % 2 == 0:
            base = (235, 242, 250)
        else:
            base = (215, 228, 240)
        pygame.draw.rect(surf, base, (0, row, w, 8))
        # 雪纹细线
        for y_off in range(1, 8, 3):
            pygame.draw.line(surf, (200, 215, 230), (0, row + y_off), (w, row + y_off), 1)
    # 冰晶反光
    for ix, iy in [(8, 5), (22, 18), (4, 24)]:
        pygame.draw.line(surf, (255, 255, 255), (ix - 1, iy), (ix + 1, iy), 1)
        pygame.draw.line(surf, (255, 255, 255), (ix, iy - 1), (ix, iy + 1), 1)
    # 蓝色阴影边
    pygame.draw.line(surf, (180, 200, 225), (0, h - 1), (w, h - 1), 1)
    # 顶部高光
    pygame.draw.line(surf, (250, 252, 255), (0, 0), (w, 0), 1)


def draw_corridor_lava(surf, w, h):
    """炼狱走廊: 暗红熔岩+裂纹+橙色发光"""
    # 熔岩底色
    surf.fill((60, 25, 20))
    # 熔岩纹理(深浅交错)
    for row in range(0, h, 8):
        if (row // 8) % 2 == 0:
            base = (70, 30, 22)
        else:
            base = (55, 22, 18)
        pygame.draw.rect(surf, base, (0, row, w, 8))
        # 裂纹发光
        for y_off in range(2, 8, 3):
            pygame.draw.line(surf, (90, 35, 25), (0, row + y_off), (w, row + y_off), 1)
    # 熔岩裂纹(橙色)
    for lx, ly, lx2, ly2 in [(3, 8, 12, 14), (18, 4, 25, 12), (8, 20, 20, 28)]:
        pygame.draw.line(surf, (200, 80, 20), (lx, ly), (lx2, ly2), 1)
        pygame.draw.line(surf, (255, 140, 40), (lx, ly), (lx2, ly2), 1)
    # 发光点
    for gx, gy in [(10, 10), (24, 20), (6, 26)]:
        pygame.draw.circle(surf, (255, 120, 30), (gx, gy), 2)
        pygame.draw.circle(surf, (255, 200, 80), (gx, gy), 1)
    # 顶部暗红高光
    pygame.draw.line(surf, (100, 40, 30), (0, 0), (w, 0), 1)


def draw_door(surf, w, h, level, door_type=DOOR_WOOD):
    """门渲染: 木门(0-4)/铁门(5-9)/金门(10-14), 共15级
    每种材质有独特外观，等级越高越精致"""
    # 阶段等级(0-4对应每种材质的1-5级)
    stage_level = level % 5

    if door_type == DOOR_WOOD:
        _draw_wood_door(surf, w, h, stage_level)
    elif door_type == DOOR_IRON:
        _draw_iron_door(surf, w, h, stage_level)
    else:  # DOOR_GOLD
        _draw_gold_door(surf, w, h, stage_level)


def _draw_wood_door(surf, w, h, stage_level):
    """木门: 木板+铁条+铆钉，棕色系"""
    # 底色(深色门框阴影)
    surf.fill((35, 22, 15))

    # 木板底色
    plank_colors = [(110, 70, 35), (95, 60, 30), (120, 78, 40), (88, 56, 28)]
    plank_w = 5
    for i in range(0, w, plank_w):
        c = plank_colors[(i // plank_w) % len(plank_colors)]
        pygame.draw.rect(surf, c, (i, 2, plank_w - 1, h - 4))
    # 木板顶端/底端横木
    pygame.draw.rect(surf, (70, 45, 22), (0, 0, w, 2))
    pygame.draw.rect(surf, (70, 45, 22), (0, h - 2, w, 2))
    # 竖向木纹
    for x in range(2, w, 4):
        pygame.draw.line(surf, (60, 38, 20), (x, 4), (x, h - 4), 1)

    # 铁条加固(根据等级递增)
    iron_color = (75, 75, 82)
    iron_hi = (110, 110, 120)
    iron_lo = (45, 45, 52)
    pygame.draw.rect(surf, iron_color, (2, 2, w - 4, 3))
    pygame.draw.line(surf, iron_hi, (2, 2), (w - 2, 2), 1)
    pygame.draw.line(surf, iron_lo, (2, 4), (w - 2, 4), 1)
    pygame.draw.rect(surf, iron_color, (2, h - 5, w - 4, 3))
    pygame.draw.line(surf, iron_hi, (2, h - 5), (w - 2, h - 5), 1)
    pygame.draw.line(surf, iron_lo, (2, h - 3), (w - 2, h - 3), 1)

    bar_count = 1 + stage_level // 2
    for i in range(bar_count):
        y_bar = h * (i + 1) // (bar_count + 1)
        pygame.draw.rect(surf, iron_color, (2, y_bar - 1, w - 4, 2))
        pygame.draw.line(surf, iron_hi, (2, y_bar - 1), (w - 2, y_bar - 1), 1)
        pygame.draw.line(surf, iron_lo, (2, y_bar + 1), (w - 2, y_bar + 1), 1)

    # 铆钉
    rivet_color = (130, 130, 140)
    rivet_shade = (60, 60, 70)
    rivet_pos = [(5, 5), (w - 6, 5), (5, h - 6), (w - 6, h - 6)]
    if stage_level >= 2:
        rivet_pos.extend([(w // 2, 5), (w // 2, h - 6)])
    if stage_level >= 3:
        rivet_pos.extend([(5, h // 2), (w - 6, h // 2)])
    for rx, ry in rivet_pos:
        pygame.draw.circle(surf, rivet_color, (rx, ry), 2)
        pygame.draw.circle(surf, rivet_shade, (rx, ry), 2, 1)
        pygame.draw.circle(surf, (200, 200, 210), (rx - 1, ry - 1), 1)

    # 门锁/把手
    lock_x = w // 2
    lock_y = h // 2 + 1
    pygame.draw.rect(surf, (50, 50, 55), (lock_x - 4, lock_y - 3, 8, 8))
    pygame.draw.rect(surf, (90, 90, 100), (lock_x - 4, lock_y - 3, 8, 8), 1)
    pygame.draw.circle(surf, (15, 15, 15), (lock_x, lock_y), 2)
    pygame.draw.rect(surf, (15, 15, 15), (lock_x - 1, lock_y, 2, 3))
    if stage_level >= 1:
        handle_x = w - 7
        handle_y = h // 2
        pygame.draw.circle(surf, (160, 130, 30), (handle_x, handle_y), 2)
        pygame.draw.circle(surf, (220, 180, 40), (handle_x, handle_y), 1)

    if stage_level >= 3:
        for cx in (10, w - 11):
            pygame.draw.circle(surf, (140, 140, 150), (cx, 3), 2, 1)
            pygame.draw.circle(surf, (60, 60, 70), (cx, 3), 1)

    pygame.draw.rect(surf, (25, 18, 12), (0, 0, w, h), 1)


def _draw_iron_door(surf, w, h, stage_level):
    """铁门: 金属板+加固条+铆钉，银灰色系"""
    # 底色(金属灰)
    surf.fill((60, 60, 65))

    # 金属面板
    for i in range(0, w, 6):
        shade = 70 + (i // 6) % 3 * 8
        pygame.draw.rect(surf, (shade, shade, shade + 5), (i, 1, 5, h - 2))
    # 面板高光
    pygame.draw.line(surf, (120, 120, 130), (0, 1), (w, 1), 1)
    pygame.draw.line(surf, (40, 40, 45), (0, h - 2), (w, h - 2), 1)

    # 加固条(比木门更粗)
    bar_color = (90, 90, 95)
    bar_hi = (130, 130, 140)
    bar_lo = (55, 55, 60)
    # 上下粗条
    for y, thick in [(0, 4), (h - 5, 4)]:
        pygame.draw.rect(surf, bar_color, (0, y, w, thick))
        pygame.draw.line(surf, bar_hi, (0, y), (w, y), 1)
        pygame.draw.line(surf, bar_lo, (0, y + thick - 1), (w, y + thick - 1), 1)

    # 中间竖条(等级越多越多)
    vert_bars = 1 + stage_level // 2
    for i in range(vert_bars):
        x_bar = w * (i + 1) // (vert_bars + 1)
        pygame.draw.rect(surf, bar_color, (x_bar - 2, 0, 4, h))
        pygame.draw.line(surf, bar_hi, (x_bar - 2, 0), (x_bar - 2, h), 1)
        pygame.draw.line(surf, bar_lo, (x_bar + 2, 0), (x_bar + 2, h), 1)

    # 铆钉(更多更密)
    rivet_color = (140, 140, 150)
    rivet_shade = (70, 70, 80)
    rivet_pos = []
    for rx in [4, w // 2, w - 5]:
        for ry in [4, h // 2, h - 5]:
            rivet_pos.append((rx, ry))
    for rx, ry in rivet_pos[:4 + stage_level]:
        pygame.draw.circle(surf, rivet_color, (rx, ry), 2)
        pygame.draw.circle(surf, rivet_shade, (rx, ry), 2, 1)
        pygame.draw.circle(surf, (210, 210, 220), (rx - 1, ry - 1), 1)

    # 锁(铁门专用锁)
    lock_x = w // 2
    lock_y = h // 2 + 1
    pygame.draw.rect(surf, (40, 40, 45), (lock_x - 5, lock_y - 4, 10, 10))
    pygame.draw.rect(surf, (100, 100, 110), (lock_x - 5, lock_y - 4, 10, 10), 1)
    pygame.draw.circle(surf, (20, 20, 25), (lock_x, lock_y), 2)

    # 等级装饰
    if stage_level >= 2:
        # 焊接纹路
        for x in range(3, w - 3, 8):
            pygame.draw.line(surf, (100, 100, 105), (x, 2), (x + 3, 2), 1)

    if stage_level >= 4:
        # 警告标志
        pygame.draw.circle(surf, (200, 180, 40), (w - 8, 8), 3, 1)
        pygame.draw.line(surf, (200, 180, 40), (w - 8, 5), (w - 8, 11), 1)

    pygame.draw.rect(surf, (30, 30, 35), (0, 0, w, h), 1)


def _draw_gold_door(surf, w, h, stage_level):
    """金门: 金色面板+花纹+宝石，金色系"""
    # 底色(金色)
    surf.fill((180, 150, 30))

    # 金板纹理
    for i in range(0, w, 7):
        shade = 170 + (i // 7) % 3 * 15
        pygame.draw.rect(surf, (shade, shade - 30, 20), (i, 1, 6, h - 2))
    # 高光边框
    pygame.draw.rect(surf, (240, 210, 60), (0, 0, w, 2))
    pygame.draw.rect(surf, (240, 210, 60), (0, 0, 2, h))
    pygame.draw.rect(surf, (240, 210, 60), (w - 2, 0, 2, h))
    pygame.draw.rect(surf, (140, 110, 15), (0, h - 2, w, 2))

    # 花纹(等级越高越多)
    flower_count = 1 + stage_level
    for i in range(flower_count):
        fx = w * (i + 1) // (flower_count + 1)
        fy = h // 2
        # 金色花纹圈
        pygame.draw.circle(surf, (220, 190, 50), (fx, fy), 4, 1)
        pygame.draw.circle(surf, (240, 210, 60), (fx, fy), 2)

    # 宝石装饰(等级≥2开始有)
    if stage_level >= 2:
        gem_colors = [(200, 40, 40), (40, 100, 200), (40, 180, 40)]
        for i, (gx, gy) in enumerate([(5, 5), (w - 6, 5), (w // 2, h - 6)]):
            if i < stage_level - 1:
                gc = gem_colors[i % len(gem_colors)]
                pygame.draw.circle(surf, gc, (gx, gy), 3)
                pygame.draw.circle(surf, (255, 255, 255), (gx - 1, gy - 1), 1)

    # 金色锁
    lock_x = w // 2
    lock_y = h // 2 + 1
    pygame.draw.rect(surf, (200, 170, 40), (lock_x - 5, lock_y - 4, 10, 10))
    pygame.draw.rect(surf, (240, 210, 60), (lock_x - 5, lock_y - 4, 10, 10), 1)
    pygame.draw.circle(surf, (100, 80, 10), (lock_x, lock_y), 2)

    # 皇冠装饰(等级≥3)
    if stage_level >= 3:
        crown_y = 4
        for cx in range(w // 2 - 4, w // 2 + 5, 4):
            pygame.draw.polygon(surf, (240, 210, 60), [
                (cx, crown_y + 3), (cx - 2, crown_y), (cx + 2, crown_y)
            ])

    if stage_level >= 4:
        # 底部铭牌
        pygame.draw.rect(surf, (160, 130, 20), (w // 2 - 6, h - 8, 12, 5))
        pygame.draw.rect(surf, (220, 190, 40), (w // 2 - 5, h - 7, 10, 3))

    pygame.draw.rect(surf, (120, 90, 10), (0, 0, w, h), 1)


def draw_bed(surf, w, h, level, has_human=False, frame=0):
    """像素床: 床头板+被褥褶皱+枕头+阴影, 等级越高越豪华
    has_human=True 时画出躺平的小人(简化)"""
    # 底部阴影(地板投影)
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 80), (3, h - 6, w - 6, 4))
    surf.blit(shadow_surf, (0, 0))

    # 床的大小随等级变化
    scale = 0.7 + level * 0.08
    bw = int(w * scale)
    bh = int(h * scale * 0.85)
    bx = (w - bw) // 2
    by = (h - bh) // 2 + 2

    # ── 床头板(高耸, 木质感) ──
    headboard_h = 5 + level
    wood_dark = (90, 58, 28)
    wood_mid = (130, 85, 40)
    wood_light = (170, 120, 60)
    # 床头板
    pygame.draw.rect(surf, wood_mid, (bx, by - headboard_h, bw, headboard_h))
    pygame.draw.rect(surf, wood_dark, (bx, by - headboard_h, bw, headboard_h), 1)
    # 床头板顶饰
    pygame.draw.rect(surf, wood_light, (bx, by - headboard_h, bw, 1))
    # 床头板木纹
    for i in range(1, bw - 1, 4):
        pygame.draw.line(surf, wood_dark, (bx + i, by - headboard_h + 1),
                         (bx + i, by - 1), 1)

    # ── 床架主体 ──
    pygame.draw.rect(surf, wood_mid, (bx, by, bw, bh))
    pygame.draw.rect(surf, wood_dark, (bx, by, bw, bh), 1)
    # 床架底部加深
    pygame.draw.line(surf, wood_dark, (bx + 1, by + bh - 1), (bx + bw - 2, by + bh - 1), 1)

    # ── 床单(白色, 露出边沿) ──
    sheet_rect = (bx + 2, by + 2, bw - 4, 3)
    pygame.draw.rect(surf, (245, 240, 230), sheet_rect)
    pygame.draw.line(surf, (200, 195, 185), (bx + 2, by + 4), (bx + bw - 3, by + 4), 1)

    # ── 枕头(白色蓬松, 居中靠上) ──
    pillow_w = bw // 2 - 1
    pillow_h = 4
    pillow_x = bx + (bw - pillow_w) // 2
    pillow_y = by + 5
    pygame.draw.rect(surf, (255, 250, 240), (pillow_x, pillow_y, pillow_w, pillow_h))
    pygame.draw.rect(surf, (210, 200, 180), (pillow_x, pillow_y, pillow_w, pillow_h), 1)
    # 枕头鼓起的阴影
    pygame.draw.line(surf, (225, 215, 195), (pillow_x + 2, pillow_y + 1),
                     (pillow_x + pillow_w - 3, pillow_y + 1), 1)
    # 枕头中线
    pygame.draw.line(surf, (200, 188, 168), (pillow_x + pillow_w // 2, pillow_y + 1),
                     (pillow_x + pillow_w // 2, pillow_y + pillow_h - 1), 1)

    # ── 被子(带褶皱) ──
    if level < 2:
        blanket_color = (80, 130, 200)         # 蓝
        blanket_hi = (130, 175, 230)
        blanket_lo = (50, 90, 150)
    elif level < 3:
        blanket_color = (180, 80, 110)         # 玫红
        blanket_hi = (220, 130, 155)
        blanket_lo = (130, 50, 80)
    elif level < 4:
        blanket_color = (170, 90, 200)         # 紫
        blanket_hi = (215, 150, 235)
        blanket_lo = (115, 55, 145)
    else:
        blanket_color = (220, 175, 50)         # 金
        blanket_hi = (255, 220, 100)
        blanket_lo = (160, 120, 20)

    blanket_x = bx + 2
    blanket_y = pillow_y + pillow_h + 1
    blanket_w = bw - 4
    blanket_h = by + bh - blanket_y - 2
    if blanket_h > 0:
        pygame.draw.rect(surf, blanket_color, (blanket_x, blanket_y, blanket_w, blanket_h))
        # 顶部高光
        pygame.draw.line(surf, blanket_hi, (blanket_x, blanket_y),
                         (blanket_x + blanket_w, blanket_y), 1)
        # 底部阴影
        pygame.draw.line(surf, blanket_lo, (blanket_x, blanket_y + blanket_h - 1),
                         (blanket_x + blanket_w, blanket_y + blanket_h - 1), 1)
        # 褶皱线(竖向, 3条)
        for i in range(1, 4):
            fx = blanket_x + blanket_w * i // 4
            pygame.draw.line(surf, blanket_lo, (fx, blanket_y + 1),
                             (fx, blanket_y + blanket_h - 2), 1)
            pygame.draw.line(surf, blanket_hi, (fx + 1, blanket_y + 1),
                             (fx + 1, blanket_y + blanket_h - 2), 1)

    # ── 有人躺着的头部显示(简化版, 在枕头处) ──
    if has_human:
        # 头发(深色, 露出在枕头上)
        head_cx = pillow_x + pillow_w // 2
        head_cy = pillow_y + 1
        # 头发块
        pygame.draw.rect(surf, (50, 30, 20), (head_cx - 3, head_cy - 1, 6, 2))
        # 脸(肤色, 一小条)
        pygame.draw.rect(surf, (235, 200, 170), (head_cx - 2, head_cy + 1, 4, 1))
        # 闭眼(横线)
        pygame.draw.line(surf, (60, 40, 30), (head_cx - 1, head_cy + 1), (head_cx, head_cy + 1), 1)
        # 呼吸节拍(胸口轻微起伏, 用 1px 阴影线)
        breath_y = blanket_y + 2
        if frame == 0:
            pygame.draw.line(surf, blanket_hi, (blanket_x + 1, breath_y),
                             (blanket_x + blanket_w - 2, breath_y), 1)

    # ── 装饰: 等级3+ 床头板顶部皇冠 ──
    if level >= 3:
        cx = bx + bw // 2
        cy = by - headboard_h - 1
        pygame.draw.polygon(surf, (240, 200, 50), [
            (cx - 3, cy + 2), (cx - 3, cy), (cx - 1, cy - 2),
            (cx, cy), (cx + 1, cy - 2), (cx + 3, cy), (cx + 3, cy + 2),
        ])

    # ── 等级4+: 金边流苏 ──
    if level >= 4:
        pygame.draw.rect(surf, (240, 200, 50), (bx - 1, by - 1, bw + 2, bh + 2), 1)
        # 床尾流苏
        pygame.draw.circle(surf, (240, 200, 50), (bx + 2, by + bh - 2), 1)
        pygame.draw.circle(surf, (240, 200, 50), (bx + bw - 3, by + bh - 2), 1)


def draw_turret(surf, w, h, level, angle=None, firing=False):
    """炮塔: 三足底座+金属球+炮管, 随升级变粗壮变金
    angle: 炮管朝向角度(弧度), None 时使用默认 -π/4
    firing: True 时炮口有闪光
    """
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (4, h - 6, w - 8, 4))
    surf.blit(shadow_surf, (0, 0))

    cx, cy = w // 2, h // 2 + 2

    # ── 三足底座(向外伸出) ──
    base_dark = (55, 55, 65)
    base_mid = (90, 90, 100)
    base_hi = (130, 130, 145)
    leg_w = 3 + level // 2
    # 三条腿
    for ang_deg in (-30, 90, 210):
        ang = math.radians(ang_deg)
        lx = cx + int(math.cos(ang) * (w // 3))
        ly = cy + int(math.sin(ang) * (h // 4))
        pygame.draw.line(surf, base_mid, (cx, cy), (lx, ly), leg_w)
        pygame.draw.line(surf, base_hi, (cx, cy), (lx, ly), 1)
        # 脚垫
        pygame.draw.circle(surf, base_dark, (lx, ly), 2)

    # ── 底座转盘 ──
    base_r = w // 3 + level
    pygame.draw.circle(surf, base_dark, (cx, cy), base_r + 1)
    pygame.draw.circle(surf, base_mid, (cx, cy), base_r)
    pygame.draw.circle(surf, base_hi, (cx, cy), base_r, 1)
    # 底座铆钉
    for ang_deg in (45, 135, 225, 315):
        ang = math.radians(ang_deg)
        rx = cx + int(math.cos(ang) * (base_r - 3))
        ry = cy + int(math.sin(ang) * (base_r - 3))
        pygame.draw.circle(surf, (170, 170, 180), (rx, ry), 1)

    # ── 球形炮台舱 ──
    dome_r = base_r - 2
    if level >= 3:
        dome_color = (200, 165, 40)   # 金色
        dome_hi = (255, 220, 90)
        dome_lo = (130, 100, 15)
    elif level >= 1:
        dome_color = (110, 110, 120)
        dome_hi = (160, 160, 175)
        dome_lo = (60, 60, 70)
    else:
        dome_color = (80, 80, 90)
        dome_hi = (130, 130, 145)
        dome_lo = (40, 40, 50)

    pygame.draw.circle(surf, dome_lo, (cx, cy - 1), dome_r + 1)
    pygame.draw.circle(surf, dome_color, (cx, cy), dome_r)
    # 高光(左上)
    pygame.draw.circle(surf, dome_hi, (cx - dome_r // 3, cy - dome_r // 3),
                       max(1, dome_r // 3))
    # 舱窗(红色扫描光, 始终向右, 表示"扫描中")
    pygame.draw.circle(surf, (200, 30, 30), (cx + dome_r // 2 - 1, cy), 2)
    pygame.draw.circle(surf, (255, 80, 80), (cx + dome_r // 2 - 1, cy), 1)

    # ── 炮管(朝向最近猎梦者方向) ──
    if angle is None:
        angle = -math.pi / 4  # 默认右上
    barrel_color = (60, 60, 70) if level < 3 else (180, 150, 40)
    barrel_hi = (110, 110, 125) if level < 3 else (240, 210, 90)
    barrel_w = 4 + level
    barrel_len = w // 2 + level * 2
    ex = cx + int(barrel_len * math.cos(angle))
    ey = cy - int(barrel_len * math.sin(angle))  # y 翻转 (pygame y 向下)
    # 炮管阴影
    pygame.draw.line(surf, (30, 30, 35), (cx + 1, cy + 1),
                     (ex + 1, ey + 1), barrel_w)
    # 炮管主体
    pygame.draw.line(surf, barrel_color, (cx, cy), (ex, ey), barrel_w)
    pygame.draw.line(surf, barrel_hi, (cx, cy), (ex, ey), 1)
    # 炮口
    pygame.draw.circle(surf, (20, 20, 20), (ex, ey), barrel_w // 2 + 1)
    pygame.draw.circle(surf, (80, 80, 90), (ex, ey), barrel_w // 2)
    # 开火闪光
    if firing:
        # 炮口处黄色光芒
        for r, a in [(8, 200), (5, 255)]:
            glow = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 220, 80, a), (r, r), r)
            surf.blit(glow, (ex - r, ey - r))

    # ── 等级2+: 双管(略偏) ──
    if level >= 2:
        angle2 = angle - 0.15
        ex2 = cx + int(barrel_len * math.cos(angle2) * 0.85)
        ey2 = cy - int(barrel_len * math.sin(angle2) * 0.85)
        pygame.draw.line(surf, barrel_color, (cx, cy), (ex2, ey2), barrel_w - 1)
        pygame.draw.line(surf, barrel_hi, (cx, cy), (ex2, ey2), 1)
        pygame.draw.circle(surf, (20, 20, 20), (ex2, ey2), (barrel_w - 1) // 2 + 1)
        if firing:
            for r, a in [(7, 180), (4, 230)]:
                glow = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 200, 60, a), (r, r), r)
                surf.blit(glow, (ex2 - r, ey2 - r))

    # ── 等级3+: 顶部天线+小旗 ──
    if level >= 3:
        ax = cx
        ay = cy - dome_r - 1
        pygame.draw.line(surf, (180, 180, 200), (ax, ay), (ax, ay - 4), 1)
        # 旗
        pygame.draw.polygon(surf, (220, 30, 30), [(ax, ay - 4), (ax + 3, ay - 3), (ax, ay - 2)])


def draw_repair_station(surf, w, h):
    """维修台: 工作台+工具箱+绿色十字+扳手"""
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (3, h - 5, w - 6, 4))
    surf.blit(shadow_surf, (0, 0))

    cx, cy = w // 2, h // 2 + 2

    # ── 工具箱底座 ──
    box_color = (90, 130, 170)
    box_dark = (50, 80, 115)
    box_hi = (135, 175, 215)
    pygame.draw.rect(surf, box_dark, (cx - 11, cy + 1, 22, 9))
    pygame.draw.rect(surf, box_color, (cx - 10, cy, 20, 9))
    # 箱盖
    pygame.draw.rect(surf, box_dark, (cx - 11, cy - 1, 22, 2))
    pygame.draw.line(surf, box_hi, (cx - 10, cy), (cx + 9, cy), 1)
    # 箱角铆钉
    for rx in (cx - 9, cx + 8):
        pygame.draw.circle(surf, (60, 60, 70), (rx, cy + 8), 1)

    # ── 工具悬挂(左:扳手, 右:钳子) ──
    # 扳手
    pygame.draw.line(surf, (170, 170, 200), (cx - 7, cy - 5), (cx - 5, cy - 1), 2)
    pygame.draw.circle(surf, (170, 170, 200), (cx - 7, cy - 5), 2)
    pygame.draw.circle(surf, (90, 90, 110), (cx - 7, cy - 5), 1)
    # 钳子
    pygame.draw.line(surf, (200, 200, 220), (cx + 4, cy - 5), (cx + 6, cy - 1), 2)
    pygame.draw.line(surf, (200, 200, 220), (cx + 4, cy - 3), (cx + 7, cy - 3), 1)

    # ── 绿色十字医疗灯 ──
    cross_x, cross_y = cx, cy - 7
    # 光晕
    pygame.draw.circle(surf, (60, 220, 90, 80), (cross_x, cross_y), 5)
    # 十字本体
    pygame.draw.rect(surf, (20, 100, 40), (cross_x - 1, cross_y - 4, 2, 8))
    pygame.draw.rect(surf, (20, 100, 40), (cross_x - 4, cross_y - 1, 8, 2))
    pygame.draw.rect(surf, (80, 240, 110), (cross_x - 1, cross_y - 4, 2, 8))
    pygame.draw.rect(surf, (80, 240, 110), (cross_x - 4, cross_y - 1, 8, 2))


def draw_human_sprite(surf, w, h, color, is_bed=False, is_dead=False, frame=0):
    """像素小人:
    - 游荡: 头+身体+眼睛(呼吸动画)
    - 床上: 躺平姿态, 头侧偏, 闭眼
    - 死亡: 灰色 + 头顶墓碑 + 骷髅
    """
    surf.fill((0, 0, 0, 0))  # 透明
    cx, cy = w // 2, h // 2
    r = w // 3

    if is_dead:
        # ── 死亡状态: 灰白身体 + 骷髅头 + 墓碑 ──
        # 墓碑(在身体下方)
        tomb_x, tomb_y = cx, cy + r - 1
        pygame.draw.rect(surf, (90, 90, 95), (tomb_x - 4, tomb_y, 8, 7))
        pygame.draw.rect(surf, (60, 60, 65), (tomb_x - 4, tomb_y, 8, 7), 1)
        pygame.draw.rect(surf, (110, 110, 115), (tomb_x - 4, tomb_y, 8, 2))  # 顶
        # 墓碑文字
        pygame.draw.line(surf, (180, 180, 190), (tomb_x - 2, tomb_y + 2), (tomb_x + 1, tomb_y + 2), 1)
        pygame.draw.line(surf, (180, 180, 190), (tomb_x - 1, tomb_y + 4), (tomb_x + 2, tomb_y + 4), 1)
        # 倒下的身体(灰色)
        body_color = (
            int(color[0] * 0.45),
            int(color[1] * 0.45),
            int(color[2] * 0.45),
        )
        # 倒下的椭圆(横向)
        pygame.draw.ellipse(surf, body_color, (cx - r + 1, cy - 1, r * 2 - 2, r - 1))
        pygame.draw.ellipse(surf, (60, 60, 65), (cx - r + 1, cy - 1, r * 2 - 2, r - 1), 1)
        # 骷髅头(白色, 在身体一侧)
        skull_x = cx + r - 2
        skull_y = cy + 1
        pygame.draw.circle(surf, (235, 230, 220), (skull_x, skull_y), r // 2)
        pygame.draw.circle(surf, (140, 140, 140), (skull_x, skull_y), r // 2, 1)
        # 骷髅眼窝(黑色, 大圆)
        pygame.draw.circle(surf, (20, 20, 25), (skull_x - 1, skull_y - 1), 1)
        pygame.draw.circle(surf, (20, 20, 25), (skull_x + 1, skull_y - 1), 1)
        # 骷髅嘴(竖线)
        pygame.draw.line(surf, (40, 40, 45), (skull_x, skull_y + 1), (skull_x, skull_y + 2), 1)
        pygame.draw.line(surf, (40, 40, 45), (skull_x - 1, skull_y + 1), (skull_x - 1, skull_y + 2), 1)
        pygame.draw.line(surf, (40, 40, 45), (skull_x + 1, skull_y + 1), (skull_x + 1, skull_y + 2), 1)
        return

    if is_bed:
        # ── 床上状态: 躺平姿态, 头侧偏, 闭眼 ──
        # 身体(横向椭圆, 灰白色调, 表示睡眠)
        sleep_color = (
            int(color[0] * 0.6 + 60),
            int(color[1] * 0.6 + 60),
            int(color[2] * 0.6 + 60),
        )
        # 身体(覆盖在被子上, 露出上半身)
        pygame.draw.ellipse(surf, sleep_color, (cx - r, cy - r // 3, r * 2, r * 2 // 3))
        pygame.draw.ellipse(surf, (90, 90, 95), (cx - r, cy - r // 3, r * 2, r * 2 // 3), 1)
        # 头(在身体一侧, 偏右)
        head_x = cx + r - 2
        head_y = cy - 1
        head_color = (
            min(255, color[0] + 30),
            min(255, color[1] + 30),
            min(255, color[2] + 30),
        )
        pygame.draw.circle(surf, head_color, (head_x, head_y), r // 2)
        pygame.draw.circle(surf, (90, 90, 95), (head_x, head_y), r // 2, 1)
        # 闭眼(横线)
        pygame.draw.line(surf, (40, 40, 45), (head_x - 2, head_y - 1), (head_x, head_y - 1), 1)
        pygame.draw.line(surf, (40, 40, 45), (head_x + 1, head_y - 1), (head_x + 2, head_y - 1), 1)
        # 嘴(微张, 呼吸)
        pygame.draw.line(surf, (60, 60, 65), (head_x, head_y + 1), (head_x, head_y + 1), 1)
        return

    # ── 游荡状态: 站立小人(呼吸动画) ──
    # 呼吸节奏: frame 0/1 切换, 整体上下浮动 1px
    breath_offset = -1 if frame == 0 else 0
    head_r = r
    # 身体
    body_rect = (cx - r // 2 + 1, cy + 1 + breath_offset, r - 2, r - 1)
    pygame.draw.rect(surf, color, body_rect)
    # 头
    head_color = (
        min(255, color[0] + 40),
        min(255, color[1] + 40),
        min(255, color[2] + 40),
    )
    pygame.draw.circle(surf, head_color, (cx, cy - r // 2 + breath_offset), head_r)
    # 头阴影(下)
    pygame.draw.circle(surf, (
        max(0, color[0] - 30),
        max(0, color[1] - 30),
        max(0, color[2] - 30),
    ), (cx, cy - r // 2 + breath_offset), head_r, 1)
    # 眼睛(白色+黑色眼仁)
    eye_y = cy - r // 2 + breath_offset - 1
    pygame.draw.circle(surf, WHITE, (cx - head_r // 2, eye_y), 1)
    pygame.draw.circle(surf, WHITE, (cx + head_r // 2, eye_y), 1)
    pygame.draw.circle(surf, BLACK, (cx - head_r // 2, eye_y), 1)
    pygame.draw.circle(surf, BLACK, (cx + head_r // 2, eye_y), 1)
    # 身体高光
    pygame.draw.line(surf, (255, 255, 255, 80), (cx - r // 2 + 2, cy + 2 + breath_offset),
                     (cx - r // 2 + 2, cy + r - 2 + breath_offset), 1)


def draw_tombstone_marker(surf, x, y, game_time):
    """在死亡人类位置绘制墓碑粒子动画(飘散的小灰点)"""
    # 3个向上飘的小圆点, 透明度递减
    for i in range(3):
        phase = (game_time * 0.5 + i * 0.33) % 1.0
        if phase > 0.9:
            continue
        tx = x + (i - 1) * 4
        ty = y - 4 - int(phase * 16)
        alpha = max(0, int(200 * (1.0 - phase / 0.9)))
        # 小灰点
        pygame.draw.circle(surf, (140, 140, 150), (tx, ty), 1)
        # 半透明(用单像素近似)
        if alpha > 128:
            pygame.draw.circle(surf, (180, 180, 190), (tx, ty), 1)


# ═══════════════════════════════════════
#  新工具像素精灵（13 种）
# ═══════════════════════════════════════

def draw_gamemachine(surf, w, h, level):
    """游戏机: 街机样式 + 霓虹招牌 + 闪烁灯"""
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (3, h - 5, w - 6, 4))
    surf.blit(shadow_surf, (0, 0))

    cx, cy = w // 2, h // 2 + 1

    # ── 街机底座(梯形) ──
    pygame.draw.polygon(surf, (50, 50, 70), [
        (cx - 13, cy + 9), (cx + 13, cy + 9), (cx + 11, cy + 12), (cx - 11, cy + 12)
    ])
    pygame.draw.polygon(surf, (90, 90, 110), [
        (cx - 13, cy + 9), (cx + 13, cy + 9), (cx + 11, cy + 11), (cx - 11, cy + 11)
    ])

    # ── 街机主体 ──
    body_dark = (40, 40, 60)
    body_color = (75, 75, 100)
    body_hi = (110, 110, 140)
    pygame.draw.rect(surf, body_dark, (cx - 12, cy - 13, 24, 23))
    pygame.draw.rect(surf, body_color, (cx - 11, cy - 12, 22, 22))
    pygame.draw.line(surf, body_hi, (cx - 11, cy - 12), (cx + 10, cy - 12), 1)
    pygame.draw.line(surf, (50, 50, 70), (cx - 11, cy + 9), (cx + 10, cy + 9), 1)

    # ── 顶部霓虹招牌(根据等级变色) ──
    if level >= 2:
        sign_color = (255, 220, 50)
    elif level >= 1:
        sign_color = (50, 200, 255)
    else:
        sign_color = (220, 60, 60)
    pygame.draw.rect(surf, sign_color, (cx - 10, cy - 11, 20, 3))
    pygame.draw.line(surf, (255, 255, 200), (cx - 10, cy - 11), (cx + 9, cy - 11), 1)
    pygame.draw.line(surf, (140, 30, 30), (cx - 10, cy - 8), (cx + 9, cy - 8), 1)
    # 招牌字("ARCADE")
    for i, lx in enumerate(range(cx - 7, cx + 8, 3)):
        pygame.draw.rect(surf, (255, 255, 255), (lx, cy - 10, 1, 1))

    # ── 屏幕(发光效果) ──
    screen_bg = (50, 180, 220)
    screen_hi = (140, 230, 255)
    pygame.draw.rect(surf, (10, 60, 100), (cx - 8, cy - 6, 16, 9))
    pygame.draw.rect(surf, screen_bg, (cx - 7, cy - 5, 14, 8))
    # 屏幕内容: 简易像素图形
    pygame.draw.rect(surf, (200, 50, 200), (cx - 5, cy - 3, 2, 2))   # 飞船
    pygame.draw.rect(surf, (255, 255, 100), (cx - 1, cy - 2, 1, 1))  # 子弹
    pygame.draw.rect(surf, (255, 100, 100), (cx + 3, cy + 1, 2, 1))  # 敌
    # 屏幕高光
    pygame.draw.line(surf, screen_hi, (cx - 7, cy - 5), (cx + 6, cy - 5), 1)
    pygame.draw.line(surf, WHITE, (cx - 7, cy - 5), (cx - 7, cy + 2), 1)
    # 屏幕外框
    pygame.draw.rect(surf, (20, 20, 30), (cx - 8, cy - 6, 16, 9), 1)

    # ── 控制台: 摇杆 + 按钮 ──
    ctrl_y = cy + 4
    # 摇杆(左)
    pygame.draw.circle(surf, (40, 40, 50), (cx - 5, ctrl_y + 1), 3)
    pygame.draw.circle(surf, (180, 30, 30), (cx - 5, ctrl_y), 2)
    pygame.draw.circle(surf, (255, 100, 100), (cx - 5, ctrl_y), 1)
    # 按钮(右排)
    btn_colors = [(255, 220, 50), (80, 220, 80), (80, 160, 255)]
    for i, bc in enumerate(btn_colors):
        bx = cx + 1 + i * 3
        pygame.draw.circle(surf, (20, 20, 30), (bx, ctrl_y + 1), 2)
        pygame.draw.circle(surf, bc, (bx, ctrl_y), 1)

    # ── 升级闪烁灯(顶部左右) ──
    if level >= 1:
        pygame.draw.circle(surf, (60, 255, 100), (cx + 9, cy - 8), 2)
        pygame.draw.circle(surf, (180, 255, 200), (cx + 9, cy - 8), 1)
    if level >= 2:
        pygame.draw.circle(surf, (255, 220, 50), (cx - 9, cy - 8), 2)
        pygame.draw.circle(surf, (255, 240, 180), (cx - 9, cy - 8), 1)
    if level >= 3:
        pygame.draw.circle(surf, (255, 100, 220), (cx, cy - 13), 2)
        pygame.draw.circle(surf, (255, 200, 240), (cx, cy - 13), 1)


def draw_mine(surf, w, h, level, frame=0):
    """矿坑: 4级强差异化
    - 铜矿: 棕色岩石+铜绿色锈斑+镐头
    - 银矿: 银灰岩石+金属反光高光
    - 金矿: 金黄岩石+金尖刺+闪光
    - 钻石矿: 冰蓝棱面+旋转高光+持续星点
    """
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (3, h - 5, w - 6, 4))
    surf.blit(shadow_surf, (0, 0))

    cx, cy = w // 2, h // 2 + 1

    # ── 矿洞地形(深棕梯形, 各种矿通用) ──
    pygame.draw.polygon(surf, (90, 65, 40), [
        (cx - 14, cy + 10), (cx + 14, cy + 10), (cx + 14, cy + 4),
        (cx + 12, cy - 2), (cx + 8, cy - 6), (cx - 8, cy - 6),
        (cx - 12, cy - 2), (cx - 14, cy + 4)
    ])
    pygame.draw.polygon(surf, (60, 40, 25), [
        (cx - 14, cy + 10), (cx + 14, cy + 10), (cx + 14, cy + 9),
        (cx - 14, cy + 9)
    ])
    # 矿洞入口阴影
    pygame.draw.ellipse(surf, (30, 20, 10), (cx - 9, cy - 2, 18, 12))
    pygame.draw.ellipse(surf, (20, 12, 5), (cx - 7, cy + 1, 14, 8))

    # ── 矿石主体(按等级) ──
    if level == 0:  # 铜矿: 棕色岩石+铜绿锈斑
        # 主矿石(5块, 棕铜色)
        ore_main = (200, 110, 50)
        ore_hi = (240, 160, 80)
        ore_lo = (140, 70, 20)
        ore_pos = [(cx - 6, cy - 2), (cx + 4, cy - 4), (cx + 6, cy + 2),
                   (cx - 4, cy + 4), (cx - 1, cy + 1)]
        for ox, oy in ore_pos:
            pygame.draw.polygon(surf, ore_main, [(ox, oy - 2), (ox - 2, oy), (ox, oy + 2), (ox + 2, oy)])
            pygame.draw.polygon(surf, ore_hi, [(ox, oy - 2), (ox - 1, oy - 1), (ox, oy), (ox - 1, oy - 1)])
            pygame.draw.line(surf, ore_lo, (ox, oy - 1), (ox, oy + 1), 1)
        # 铜绿色锈斑(2-3个小点)
        for sx, sy in [(cx - 5, cy - 1), (cx + 5, cy + 1), (cx + 2, cy - 3)]:
            pygame.draw.circle(surf, (100, 180, 130), (sx, sy), 1)
            pygame.draw.circle(surf, (60, 130, 90), (sx, sy), 1, 1)

    elif level == 1:  # 银矿: 银灰+金属反光
        # 银矿石(菱形, 银灰色)
        ore_main = (210, 210, 220)
        ore_hi = (245, 245, 255)
        ore_lo = (140, 140, 160)
        ore_pos = [(cx - 6, cy - 2), (cx + 4, cy - 4), (cx + 6, cy + 2),
                   (cx - 4, cy + 4), (cx - 1, cy + 1)]
        for ox, oy in ore_pos:
            # 菱形主体
            pygame.draw.polygon(surf, ore_lo, [(ox, oy - 3), (ox + 2, oy), (ox, oy + 3), (ox - 2, oy)])
            pygame.draw.polygon(surf, ore_main, [(ox, oy - 2), (ox + 2, oy), (ox, oy + 2), (ox - 2, oy)])
            # 顶部高光(强反光)
            pygame.draw.polygon(surf, ore_hi, [(ox, oy - 2), (ox - 1, oy - 1), (ox, oy - 1)])
            pygame.draw.line(surf, WHITE, (ox, oy - 1), (ox + 1, oy), 1)
        # 整体环境光(更亮一圈)
        glow = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.circle(glow, (200, 200, 255, 30), (12, 12), 12)
        surf.blit(glow, (cx - 12, cy - 12))

    elif level == 2:  # 金矿: 金黄+金尖刺+闪光
        # 金矿石(带尖刺)
        ore_main = (255, 215, 0)
        ore_hi = (255, 240, 120)
        ore_lo = (180, 130, 0)
        ore_pos = [(cx - 6, cy - 2), (cx + 4, cy - 4), (cx + 6, cy + 2),
                   (cx - 4, cy + 4), (cx - 1, cy + 1)]
        for ox, oy in ore_pos:
            # 矿石带尖刺(顶部尖角)
            pygame.draw.polygon(surf, ore_main, [
                (ox, oy - 3),  # 尖顶
                (ox + 2, oy - 1),
                (ox + 3, oy + 1),
                (ox + 1, oy + 3),
                (ox - 1, oy + 3),
                (ox - 3, oy + 1),
                (ox - 2, oy - 1),
            ])
            pygame.draw.line(surf, ore_lo, (ox, oy - 3), (ox, oy + 3), 1)
            pygame.draw.polygon(surf, ore_hi, [(ox, oy - 3), (ox - 1, oy - 1), (ox, oy - 1)])
        # 闪光(每3秒一次, 用 frame 控制)
        if (frame // 2) % 4 == 0:
            sx, sy = cx - 3, cy - 5
            pygame.draw.line(surf, WHITE, (sx - 2, sy), (sx + 2, sy), 1)
            pygame.draw.line(surf, WHITE, (sx, sy - 2), (sx, sy + 2), 1)
            pygame.draw.line(surf, (255, 255, 200), (sx - 1, sy - 1), (sx + 1, sy + 1), 1)
            pygame.draw.line(surf, (255, 255, 200), (sx - 1, sy + 1), (sx + 1, sy - 1), 1)
        # 金色环境光
        glow = pygame.Surface((28, 28), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 220, 80, 40), (14, 14), 14)
        surf.blit(glow, (cx - 14, cy - 14))

    else:  # 钻石矿: 冰蓝棱面+旋转高光+持续星点
        # 钻石(八面体棱面)
        ore_main = (180, 240, 255)
        ore_hi = (230, 250, 255)
        ore_lo = (120, 180, 220)
        ore_pos = [(cx - 5, cy - 1), (cx + 4, cy - 3), (cx + 5, cy + 2),
                   (cx - 3, cy + 4), (cx - 1, cy + 1)]
        for ox, oy in ore_pos:
            # 菱形钻石(4个棱面)
            # 上面
            pygame.draw.polygon(surf, ore_hi, [
                (ox, oy - 2),
                (ox + 2, oy - 1),
                (ox, oy),
                (ox - 2, oy - 1),
            ])
            # 下面
            pygame.draw.polygon(surf, ore_main, [
                (ox, oy),
                (ox + 2, oy - 1),
                (ox + 2, oy + 1),
                (ox, oy + 2),
            ])
            # 阴影面
            pygame.draw.polygon(surf, ore_lo, [
                (ox, oy),
                (ox - 2, oy - 1),
                (ox - 2, oy + 1),
                (ox, oy + 2),
            ])
            pygame.draw.line(surf, (100, 150, 200), (ox, oy - 2), (ox, oy + 2), 1)
        # 旋转高光(根据 frame 改变位置)
        rot_offset = (frame % 8)
        rx = cx + (rot_offset - 4) // 2 - 1
        ry = cy - 3
        pygame.draw.line(surf, WHITE, (rx - 1, ry), (rx + 1, ry), 1)
        pygame.draw.line(surf, WHITE, (rx, ry - 1), (rx, ry + 1), 1)
        # 持续星点
        for sx, sy in [(cx - 6, cy - 4), (cx + 5, cy - 5), (cx - 7, cy + 2),
                       (cx + 6, cy + 3), (cx, cy - 6)]:
            phase = (frame + sx + sy) % 6
            if phase < 3:  # 半周期闪烁
                pygame.draw.line(surf, WHITE, (sx - 1, sy), (sx + 1, sy), 1)
                pygame.draw.line(surf, WHITE, (sx, sy - 1), (sx, sy + 1), 1)
        # 蓝色地面光晕
        glow = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(glow, (140, 220, 255, 50), (15, 15), 15)
        surf.blit(glow, (cx - 15, cy - 10))

    # ── 镐头(右下角, 4级都有) ──
    pick_color = WHITE if level == 3 else (140, 140, 145)
    # 镐头金属
    pygame.draw.line(surf, pick_color, (cx - 13, cy + 4), (cx - 8, cy - 1), 2)
    pygame.draw.line(surf, WHITE, (cx - 13, cy + 4), (cx - 8, cy - 1), 1)
    # 镐柄
    pygame.draw.line(surf, (100, 60, 30), (cx - 8, cy - 1), (cx - 4, cy + 5), 2)
    pygame.draw.line(surf, (140, 90, 50), (cx - 8, cy - 1), (cx - 4, cy + 5), 1)


def draw_fridge(surf, w, h):
    """冰箱: 圆润白色箱体+蓝色霜雾+雪花"""
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (4, h - 5, w - 8, 4))
    surf.blit(shadow_surf, (0, 0))

    cx, cy = w // 2, h // 2 + 1

    # ── 主体(圆润) ──
    body_dark = (170, 195, 220)
    body_color = (230, 240, 250)
    body_hi = (255, 255, 255)
    # 阴影
    pygame.draw.rect(surf, body_dark, (cx - 12, cy - 14, 24, 28), border_radius=3)
    # 主体
    pygame.draw.rect(surf, body_color, (cx - 11, cy - 14, 22, 27), border_radius=3)
    # 高光(左上)
    pygame.draw.line(surf, body_hi, (cx - 10, cy - 13), (cx + 9, cy - 13), 1)
    pygame.draw.line(surf, body_hi, (cx - 10, cy - 13), (cx - 10, cy - 3), 1)

    # ── 上下门分割 ──
    pygame.draw.line(surf, body_dark, (cx - 10, cy), (cx + 9, cy), 1)
    pygame.draw.line(surf, (200, 215, 235), (cx - 10, cy + 1), (cx + 9, cy + 1), 1)

    # ── 把手(右侧长条) ──
    pygame.draw.rect(surf, (80, 80, 90), (cx + 6, cy - 11, 2, 7))
    pygame.draw.rect(surf, (130, 130, 140), (cx + 6, cy - 11, 1, 7))
    pygame.draw.rect(surf, (80, 80, 90), (cx + 6, cy + 2, 2, 7))
    pygame.draw.rect(surf, (130, 130, 140), (cx + 6, cy + 2, 1, 7))

    # ── 雪花图标(冷光) ──
    # 光晕
    glow = pygame.Surface((20, 20), pygame.SRCALPHA)
    pygame.draw.circle(glow, (140, 220, 255, 60), (10, 10), 9)
    surf.blit(glow, (cx - 10, cy - 14))
    # 雪花主体
    sx, sy = cx - 4, cy - 5
    pygame.draw.line(surf, (40, 160, 220), (sx - 4, sy), (sx + 4, sy), 2)
    pygame.draw.line(surf, (40, 160, 220), (sx, sy - 4), (sx, sy + 4), 2)
    pygame.draw.line(surf, (40, 160, 220), (sx - 3, sy - 3), (sx + 3, sy + 3), 1)
    pygame.draw.line(surf, (40, 160, 220), (sx - 3, sy + 3), (sx + 3, sy - 3), 1)
    # 中心点
    pygame.draw.circle(surf, (220, 245, 255), (sx, sy), 1)

    # ── 底部散热栅 ──
    for i in range(3):
        pygame.draw.line(surf, body_dark, (cx - 6 + i * 4, cy + 11),
                         (cx - 6 + i * 4, cy + 12), 1)


def draw_shield(surf, w, h, active=False):
    """能量罩: 蓝紫色护盾图标+光晕"""
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 80), (4, h - 5, w - 8, 4))
    surf.blit(shadow_surf, (0, 0))

    cx, cy = w // 2, h // 2 + 1

    if active:
        # 激活: 金色发光的盾
        # 光晕
        glow = pygame.Surface((36, 36), pygame.SRCALPHA)
        for r, a in [(18, 60), (15, 90), (12, 120)]:
            pygame.draw.circle(glow, (255, 230, 80, a), (18, 18), r)
        surf.blit(glow, (cx - 18, cy - 17))
        # 盾体
        pygame.draw.polygon(surf, (220, 180, 30), [
            (cx, cy - 14), (cx + 12, cy - 6), (cx + 10, cy + 6),
            (cx, cy + 14), (cx - 10, cy + 6), (cx - 12, cy - 6)
        ])
        pygame.draw.polygon(surf, (255, 220, 100), [
            (cx, cy - 13), (cx + 10, cy - 6), (cx + 9, cy + 5),
            (cx, cy + 12), (cx - 9, cy + 5), (cx - 10, cy - 6)
        ])
        pygame.draw.polygon(surf, WHITE, [
            (cx, cy - 14), (cx + 12, cy - 6), (cx + 10, cy + 6),
            (cx, cy + 14), (cx - 10, cy + 6), (cx - 12, cy - 6)
        ], 2)
    else:
        # 未激活: 蓝紫盾
        # 光晕
        glow = pygame.Surface((36, 36), pygame.SRCALPHA)
        for r, a in [(18, 40), (15, 60), (12, 80)]:
            pygame.draw.circle(glow, (140, 100, 220, a), (18, 18), r)
        surf.blit(glow, (cx - 18, cy - 17))
        # 盾体
        pygame.draw.polygon(surf, (60, 40, 130), [
            (cx, cy - 14), (cx + 12, cy - 6), (cx + 10, cy + 6),
            (cx, cy + 14), (cx - 10, cy + 6), (cx - 12, cy - 6)
        ])
        pygame.draw.polygon(surf, (110, 70, 200), [
            (cx, cy - 13), (cx + 10, cy - 6), (cx + 9, cy + 5),
            (cx, cy + 12), (cx - 9, cy + 5), (cx - 10, cy - 6)
        ])
        pygame.draw.polygon(surf, (180, 150, 255), [
            (cx, cy - 14), (cx + 12, cy - 6), (cx + 10, cy + 6),
            (cx, cy + 14), (cx - 10, cy + 6), (cx - 12, cy - 6)
        ], 2)

    # 中心光点
    pygame.draw.circle(surf, WHITE, (cx, cy), 2)
    pygame.draw.circle(surf, (255, 255, 200), (cx - 1, cy - 1), 1)


def draw_trap(surf, w, h):
    """诱捕网: 方形木框+交错网线+红心"""
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (3, h - 5, w - 6, 4))
    surf.blit(shadow_surf, (0, 0))

    cx, cy = w // 2, h // 2 + 1

    # ── 木框 ──
    wood_dark = (90, 60, 30)
    wood_color = (130, 90, 50)
    wood_hi = (170, 130, 80)
    pygame.draw.rect(surf, wood_color, (cx - 13, cy - 13, 26, 26))
    pygame.draw.rect(surf, wood_dark, (cx - 13, cy - 13, 26, 26), 2)
    # 高光
    pygame.draw.line(surf, wood_hi, (cx - 12, cy - 12), (cx + 12, cy - 12), 1)
    pygame.draw.line(surf, wood_hi, (cx - 12, cy - 12), (cx - 12, cy + 12), 1)
    # 木纹
    for x in (cx - 7, cx + 4):
        pygame.draw.line(surf, wood_dark, (x, cy - 11), (x, cy - 4), 1)
        pygame.draw.line(surf, wood_dark, (x, cy + 4), (x, cy + 11), 1)
    # 四角铆钉
    for rx, ry in [(cx - 10, cy - 10), (cx + 10, cy - 10),
                   (cx - 10, cy + 10), (cx + 10, cy + 10)]:
        pygame.draw.circle(surf, (60, 60, 70), (rx, ry), 1)

    # ── 网(交错对角线) ──
    net_color = (200, 200, 210)
    net_color2 = (150, 150, 160)
    for i in range(-3, 4):
        pygame.draw.line(surf, net_color,
                         (cx + i * 3, cy - 11), (cx + 11, cy + i * 3), 1)
        pygame.draw.line(surf, net_color2,
                         (cx - 11, cy - i * 3), (cx - i * 3, cy + 11), 1)

    # ── 中心红心(陷阱触发) ──
    pygame.draw.circle(surf, (180, 30, 30), (cx, cy), 3)
    pygame.draw.circle(surf, (255, 80, 80), (cx, cy), 2)
    pygame.draw.circle(surf, (255, 200, 200), (cx - 1, cy - 1), 1)


def draw_guillotine(surf, w, h):
    """断头台: 木质支架+金属刀片+血滴"""
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (3, h - 5, w - 6, 4))
    surf.blit(shadow_surf, (0, 0))

    cx, cy = w // 2, h // 2 + 1

    # ── 立柱 ──
    wood_dark = (90, 60, 30)
    wood_color = (130, 90, 50)
    wood_hi = (170, 130, 80)
    pygame.draw.rect(surf, wood_dark, (cx - 11, cy - 14, 3, 28))
    pygame.draw.rect(surf, wood_color, (cx - 10, cy - 13, 2, 26))
    pygame.draw.line(surf, wood_hi, (cx - 10, cy - 13), (cx - 10, cy + 12), 1)
    pygame.draw.rect(surf, wood_dark, (cx + 8, cy - 14, 3, 28))
    pygame.draw.rect(surf, wood_color, (cx + 9, cy - 13, 2, 26))
    pygame.draw.line(surf, wood_hi, (cx + 9, cy - 13), (cx + 9, cy + 12), 1)

    # ── 顶横梁 ──
    pygame.draw.rect(surf, wood_dark, (cx - 12, cy - 14, 24, 4))
    pygame.draw.rect(surf, wood_color, (cx - 11, cy - 13, 22, 3))
    pygame.draw.line(surf, wood_hi, (cx - 11, cy - 13), (cx + 10, cy - 13), 1)

    # ── 刀片(宽大金属刀) ──
    blade_dark = (160, 160, 180)
    blade_color = (200, 200, 220)
    blade_hi = (240, 240, 255)
    # 刀刃主体
    pygame.draw.polygon(surf, blade_dark, [
        (cx - 9, cy - 3), (cx + 9, cy - 3), (cx + 7, cy + 3), (cx - 7, cy + 3)
    ])
    pygame.draw.polygon(surf, blade_color, [
        (cx - 8, cy - 2), (cx + 8, cy - 2), (cx + 6, cy + 2), (cx - 6, cy + 2)
    ])
    pygame.draw.line(surf, blade_hi, (cx - 8, cy - 2), (cx + 8, cy - 2), 1)
    # 刀刃锐边
    pygame.draw.line(surf, WHITE, (cx - 7, cy + 2), (cx + 7, cy + 2), 1)

    # ── 顶部绳索(吊刀用) ──
    pygame.draw.line(surf, (200, 180, 100), (cx, cy - 14), (cx, cy - 3), 1)

    # ── 血滴(刀下) ──
    pygame.draw.circle(surf, (160, 20, 20), (cx, cy + 8), 2)
    pygame.draw.circle(surf, (220, 50, 50), (cx, cy + 8), 1)

    # ── 底座木槽(放头) ──
    pygame.draw.rect(surf, wood_dark, (cx - 6, cy + 11, 12, 2))
    pygame.draw.rect(surf, wood_color, (cx - 5, cy + 11, 10, 1))


def draw_grass(surf, w, h, big=False):
    """小草: 一根 / 一盆(枝叶+露珠, 鲜艳绿)"""
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 80), (3, h - 4, w - 6, 3))
    surf.blit(shadow_surf, (0, 0))

    cx, cy = w // 2, h // 2 + 1

    if big:
        # ── 陶土花盆 ──
        pot_dark = (90, 50, 25)
        pot_color = (140, 80, 45)
        pot_hi = (190, 130, 80)
        pygame.draw.rect(surf, pot_dark, (cx - 10, cy + 3, 20, 10))
        pygame.draw.rect(surf, pot_color, (cx - 9, cy + 3, 18, 9))
        # 盆口
        pygame.draw.rect(surf, pot_hi, (cx - 10, cy + 3, 20, 2))
        pygame.draw.line(surf, pot_dark, (cx - 10, cy + 5), (cx + 10, cy + 5), 1)
        # 高光
        pygame.draw.line(surf, pot_hi, (cx - 8, cy + 4), (cx - 8, cy + 11), 1)

        # ── 多株小草(深浅绿) ──
        leaf_colors = [(60, 180, 80), (90, 200, 100), (40, 150, 60)]
        for i, (lx, ly, lh, lw) in enumerate([
            (cx - 5, cy - 2, 12, 4),
            (cx + 1, cy - 6, 16, 4),
            (cx + 5, cy - 1, 11, 4),
        ]):
            color = leaf_colors[i]
            # 茎
            pygame.draw.line(surf, (40, 120, 50), (lx, cy + 3), (lx, ly + lh - 2), 1)
            # 叶
            pygame.draw.ellipse(surf, color, (lx - lw // 2, ly, lw, lh))
            pygame.draw.ellipse(surf, (140, 230, 160), (lx - lw // 2 + 1, ly, 1, lh - 2))
            # 叶尖高光
            pygame.draw.circle(surf, (180, 250, 180), (lx, ly), 1)

        # 露珠
        pygame.draw.circle(surf, (200, 240, 255), (cx + 2, cy - 1), 1)
        pygame.draw.circle(surf, WHITE, (cx + 2, cy - 1), 1)
    else:
        # ── 单株小草(3片叶) ──
        # 茎
        pygame.draw.line(surf, (50, 140, 60), (cx, cy + 8), (cx, cy - 2), 2)
        # 中央叶
        pygame.draw.ellipse(surf, (90, 210, 110), (cx - 4, cy - 10, 8, 12))
        pygame.draw.ellipse(surf, (140, 240, 160), (cx - 2, cy - 8, 3, 6))
        # 左侧叶
        pygame.draw.ellipse(surf, (60, 180, 80), (cx - 7, cy - 4, 6, 8))
        pygame.draw.ellipse(surf, (110, 220, 130), (cx - 6, cy - 3, 2, 4))
        # 右侧叶
        pygame.draw.ellipse(surf, (60, 180, 80), (cx + 1, cy - 4, 6, 8))
        pygame.draw.ellipse(surf, (110, 220, 130), (cx + 2, cy - 3, 2, 4))
        # 露珠
        pygame.draw.circle(surf, WHITE, (cx - 1, cy - 6), 1)
        pygame.draw.circle(surf, (200, 240, 255), (cx - 1, cy - 6), 1)


def draw_mirror(surf, w, h, hunter_near=False, frame=0, burning=False):
    """镜子: 菱形镜面+金框+底座+反光
    hunter_near: 是否有猎梦者接近(8格内), 此时镜面波动
    burning: 灼热红光激活中, 镜面整体红色"""
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 80), (4, h - 4, w - 8, 3))
    surf.blit(shadow_surf, (0, 0))

    cx, cy = w // 2, h // 2

    # ── 底座(金球+柱) ──
    pygame.draw.rect(surf, (130, 100, 20), (cx - 2, cy + 10, 4, 4))
    pygame.draw.rect(surf, (220, 180, 30), (cx - 3, cy + 9, 6, 2))
    pygame.draw.ellipse(surf, (255, 220, 100), (cx - 5, cy + 13, 10, 3))
    pygame.draw.ellipse(surf, (200, 160, 30), (cx - 5, cy + 14, 10, 2))

    # ── 镜框(菱形) ──
    frame_outer = (180, 140, 30)
    frame_color = (240, 200, 50)
    frame_hi = (255, 235, 130)
    pygame.draw.polygon(surf, frame_outer, [
        (cx, cy - 14), (cx + 11, cy), (cx, cy + 14), (cx - 11, cy)
    ])
    pygame.draw.polygon(surf, frame_color, [
        (cx, cy - 13), (cx + 10, cy), (cx, cy + 13), (cx - 10, cy)
    ])
    pygame.draw.polygon(surf, frame_hi, [
        (cx, cy - 13), (cx + 9, cy), (cx, cy + 12), (cx - 9, cy)
    ])

    # ── 镜面(蓝色渐变+反光, 灼热时变红) ──
    if burning:
        mirror_dark = (200, 80, 60)
        mirror_color = (240, 120, 100)
        mirror_hi = (255, 200, 180)
        # 红色光晕
        glow = pygame.Surface((28, 28), pygame.SRCALPHA)
        for r, a in [(14, 60), (10, 90), (6, 130)]:
            pygame.draw.circle(glow, (255, 80, 60, a), (14, 14), r)
        surf.blit(glow, (cx - 14, cy - 14))
    else:
        mirror_dark = (130, 170, 200)
        mirror_color = (190, 220, 240)
        mirror_hi = (240, 250, 255)
        # 接近时镜面波动(径向扰动)
        if hunter_near:
            # 镜面有微弱的蓝色光晕
            glow = pygame.Surface((24, 24), pygame.SRCALPHA)
            for r, a in [(12, 30), (9, 50), (6, 80)]:
                pulse = abs((frame % 12) - 6) / 6.0
                pygame.draw.circle(glow, (140, 200, 255, int(a * pulse)), (12, 12), r)
            surf.blit(glow, (cx - 12, cy - 12))

    pygame.draw.polygon(surf, mirror_dark, [
        (cx, cy - 10), (cx + 7, cy), (cx, cy + 10), (cx - 7, cy)
    ])
    pygame.draw.polygon(surf, mirror_color, [
        (cx, cy - 9), (cx + 6, cy), (cx, cy + 9), (cx - 6, cy)
    ])
    # 反光高光(灼热时变金色)
    if burning:
        pygame.draw.line(surf, (255, 255, 100), (cx - 4, cy - 6), (cx + 2, cy - 8), 2)
        pygame.draw.line(surf, (255, 200, 100), (cx - 3, cy + 4), (cx + 1, cy + 2), 1)
    else:
        pygame.draw.line(surf, mirror_hi, (cx - 4, cy - 6), (cx + 2, cy - 8), 2)
        pygame.draw.line(surf, mirror_hi, (cx - 3, cy + 4), (cx + 1, cy + 2), 1)
    # 中心高光点
    pygame.draw.circle(surf, WHITE, (cx - 1, cy - 1), 1)

    # ── 接近时的"波纹"扰动(2-3条短横线) ──
    if hunter_near and not burning:
        for i in range(2):
            wy = cy - 4 + i * 6
            phase = (frame + i * 4) % 6
            if phase < 3:
                pygame.draw.line(surf, (180, 220, 255),
                                 (cx - 4 + phase, wy), (cx + 4 - phase, wy), 1)


def draw_garlic(surf, w, h, active=False, frame=0):
    """大蒜: 饱满蒜头+蒜瓣纹+根须+驱散气场(激活时)
    active=True 时显示绿色波纹气场"""
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 80), (4, h - 4, w - 8, 3))
    surf.blit(shadow_surf, (0, 0))

    cx, cy = w // 2, h // 2 + 1

    # ── 驱散气场(激活时扩散波纹) ──
    if active:
        # 3层波纹, 错开帧
        for i in range(3):
            phase = (frame + i * 6) % 18
            if phase < 12:
                ring_r = 6 + phase
                ring_alpha = max(0, int(120 * (1.0 - phase / 12)))
                glow = pygame.Surface((ring_r * 2, ring_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow, (100, 220, 100, ring_alpha),
                                   (ring_r, ring_r), ring_r, 1)
                surf.blit(glow, (cx - ring_r, cy - ring_r))
        # 中央绿光
        glow = pygame.Surface((24, 24), pygame.SRCALPHA)
        for r, a in [(12, 40), (9, 60), (6, 90)]:
            pygame.draw.circle(glow, (120, 230, 130, a), (12, 12), r)
        surf.blit(glow, (cx - 12, cy - 12))

    # ── 根须 ──
    for rx, ry, rrx, rry in [
        (cx - 3, cy + 12, cx - 4, cy + 15),
        (cx + 0, cy + 13, cx + 1, cy + 16),
        (cx + 3, cy + 12, cx + 4, cy + 15),
    ]:
        pygame.draw.line(surf, (180, 150, 100), (rx, ry), (rrx, rry), 1)

    # ── 蒜头顶部尖角 ──
    pygame.draw.polygon(surf, (210, 200, 170), [(cx, cy - 14), (cx - 4, cy - 4), (cx + 4, cy - 4)])
    pygame.draw.polygon(surf, (240, 230, 200), [(cx, cy - 13), (cx - 2, cy - 4), (cx + 2, cy - 4)])

    # ── 蒜头主体(饱满) ──
    body_color = (248, 245, 230)
    body_hi = (255, 255, 245)
    body_shade = (210, 200, 175)
    pygame.draw.ellipse(surf, body_shade, (cx - 9, cy - 3, 18, 18))
    pygame.draw.ellipse(surf, body_color, (cx - 8, cy - 4, 16, 17))
    # 高光
    pygame.draw.ellipse(surf, body_hi, (cx - 6, cy - 2, 4, 6))
    # 蒜瓣分隔线
    for i in range(-1, 2):
        sx = cx + i * 4
        pygame.draw.line(surf, (190, 180, 155), (sx, cy - 2), (sx, cy + 10), 1)
    # 整体描边
    pygame.draw.ellipse(surf, (180, 165, 130), (cx - 8, cy - 4, 16, 17), 1)

    # ── 顶部嫩芽(2片绿叶) ──
    pygame.draw.ellipse(surf, (60, 160, 70), (cx - 4, cy - 9, 3, 6))
    pygame.draw.ellipse(surf, (90, 200, 100), (cx + 1, cy - 9, 3, 6))

    # ── 驱散状态的"熏烟"小粒子(向上飘) ──
    if active:
        for i in range(2):
            phase = (frame + i * 9) % 18
            if phase < 14:
                ty = cy - 6 - phase // 2
                tx = cx + (i * 4 - 2)
                alpha = max(0, int(150 * (1.0 - phase / 14)))
                # 用单像素近似透明度
                pygame.draw.circle(surf, (140, 220, 150), (tx, ty), 1)


def draw_frog(surf, w, h, frame=0, tongue_target=None):
    """蛤蟆: 绿皮+大眼+红舌(可眨眼/吐舌动画)
    frame: 0/1 切换, 眼睛睁开/闭眼
    tongue_target: (x, y) 舌头伸出方向"""
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (3, h - 4, w - 6, 3))
    surf.blit(shadow_surf, (0, 0))

    cx, cy = w // 2, h // 2 + 1

    # ── 后腿(深绿, 在身体下方) ──
    leg_color = (30, 90, 45)
    pygame.draw.ellipse(surf, leg_color, (cx - 12, cy + 2, 8, 8))
    pygame.draw.ellipse(surf, leg_color, (cx + 4, cy + 2, 8, 8))

    # ── 蛙身(绿色渐变+高光) ──
    body_color = (60, 160, 85)
    body_hi = (110, 210, 130)
    body_dark = (30, 100, 50)
    pygame.draw.ellipse(surf, body_dark, (cx - 11, cy - 6, 22, 16))
    pygame.draw.ellipse(surf, body_color, (cx - 11, cy - 7, 22, 16))
    # 背部高光
    pygame.draw.ellipse(surf, body_hi, (cx - 6, cy - 6, 12, 4))
    # 背部斑点
    pygame.draw.circle(surf, body_dark, (cx - 4, cy - 2), 1)
    pygame.draw.circle(surf, body_dark, (cx + 3, cy - 4), 1)
    pygame.draw.circle(surf, body_dark, (cx + 5, cy + 1), 1)

    # ── 鼓眼泡(根据 frame 闭眼) ──
    eye_y = cy - 8
    if frame == 0:  # 睁眼
        for ex in (cx - 5, cx + 5):
            pygame.draw.circle(surf, body_dark, (ex, eye_y + 1), 4)
            pygame.draw.circle(surf, body_color, (ex, eye_y), 4)
            pygame.draw.circle(surf, body_hi, (ex, eye_y), 3)
            # 眼仁
            pygame.draw.circle(surf, WHITE, (ex, eye_y), 3)
            pygame.draw.circle(surf, BLACK, (ex, eye_y), 2)
            pygame.draw.circle(surf, WHITE, (ex - 1, eye_y - 1), 1)
    else:  # 闭眼(横线)
        for ex in (cx - 5, cx + 5):
            pygame.draw.circle(surf, body_dark, (ex, eye_y), 4, 1)
            pygame.draw.line(surf, body_dark, (ex - 3, eye_y), (ex + 3, eye_y), 1)
            # 睫毛
            pygame.draw.line(surf, body_dark, (ex - 3, eye_y), (ex - 4, eye_y - 1), 1)
            pygame.draw.line(surf, body_dark, (ex + 3, eye_y), (ex + 4, eye_y - 1), 1)

    # ── 嘴(根据 frame 一张一合) ──
    if frame == 0:
        # 张嘴(显示红色内部)
        pygame.draw.arc(surf, body_dark, (cx - 6, cy - 1, 12, 6), 3.14, 6.28, 1)
        pygame.draw.rect(surf, (200, 60, 80), (cx - 4, cy + 1, 8, 2))
    else:
        # 闭嘴
        pygame.draw.arc(surf, body_dark, (cx - 6, cy + 1, 12, 4), 0, 3.14, 1)

    # ── 红舌(根据 tongue_target 伸出) ──
    if tongue_target is not None:
        tx, ty = tongue_target
        # 舌头从嘴部到目标
        pygame.draw.line(surf, (220, 30, 60), (cx, cy + 2), (tx, ty), 2)
        # 舌尖(箭头状)
        pygame.draw.circle(surf, (240, 60, 90), (tx, ty), 2)
        pygame.draw.circle(surf, (255, 150, 170), (tx - 1, ty - 1), 1)


def draw_fridge(surf, w, h, frame=0):
    """冰箱: 圆润白色箱体+蓝色霜雾+雪花+飘落冷气粒子"""
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (4, h - 5, w - 8, 4))
    surf.blit(shadow_surf, (0, 0))

    cx, cy = w // 2, h // 2 + 1

    # ── 主体(圆润) ──
    body_dark = (170, 195, 220)
    body_color = (230, 240, 250)
    body_hi = (255, 255, 255)
    # 阴影
    pygame.draw.rect(surf, body_dark, (cx - 12, cy - 14, 24, 28), border_radius=3)
    # 主体
    pygame.draw.rect(surf, body_color, (cx - 11, cy - 14, 22, 27), border_radius=3)
    # 高光(左上)
    pygame.draw.line(surf, body_hi, (cx - 10, cy - 13), (cx + 9, cy - 13), 1)
    pygame.draw.line(surf, body_hi, (cx - 10, cy - 13), (cx - 10, cy - 3), 1)

    # ── 上下门分割 ──
    pygame.draw.line(surf, body_dark, (cx - 10, cy), (cx + 9, cy), 1)
    pygame.draw.line(surf, (200, 215, 235), (cx - 10, cy + 1), (cx + 9, cy + 1), 1)

    # ── 把手(右侧长条) ──
    pygame.draw.rect(surf, (80, 80, 90), (cx + 6, cy - 11, 2, 7))
    pygame.draw.rect(surf, (130, 130, 140), (cx + 6, cy - 11, 1, 7))
    pygame.draw.rect(surf, (80, 80, 90), (cx + 6, cy + 2, 2, 7))
    pygame.draw.rect(surf, (130, 130, 140), (cx + 6, cy + 2, 1, 7))

    # ── 雪花图标(冷光) ──
    # 光晕
    glow = pygame.Surface((20, 20), pygame.SRCALPHA)
    pygame.draw.circle(glow, (140, 220, 255, 60), (10, 10), 9)
    surf.blit(glow, (cx - 10, cy - 14))
    # 雪花主体
    sx, sy = cx - 4, cy - 5
    pygame.draw.line(surf, (40, 160, 220), (sx - 4, sy), (sx + 4, sy), 2)
    pygame.draw.line(surf, (40, 160, 220), (sx, sy - 4), (sx, sy + 4), 2)
    pygame.draw.line(surf, (40, 160, 220), (sx - 3, sy - 3), (sx + 3, sy + 3), 1)
    pygame.draw.line(surf, (40, 160, 220), (sx - 3, sy + 3), (sx + 3, sy - 3), 1)
    # 中心点
    pygame.draw.circle(surf, (220, 245, 255), (sx, sy), 1)

    # ── 底部散热栅 ──
    for i in range(3):
        pygame.draw.line(surf, body_dark, (cx - 6 + i * 4, cy + 11),
                         (cx - 6 + i * 4, cy + 12), 1)

    # ── 飘落雪花粒子(3片, 错开帧) ──
    for i in range(3):
        phase = (frame + i * 5) % 20
        if phase < 18:
            sx_p = cx - 8 + (i * 6)
            sy_p = cy - 12 + phase
            # 雪花十字
            pygame.draw.line(surf, (180, 220, 255), (sx_p - 1, sy_p), (sx_p + 1, sy_p), 1)
            pygame.draw.line(surf, (180, 220, 255), (sx_p, sy_p - 1), (sx_p, sy_p + 1), 1)

    # ── 底部冷气横线(向上飘的冷气) ──
    for i in range(2):
        phase = (frame + i * 8) % 16
        if phase < 12:
            ay = cy + 14 - phase
            ax = cx - 4 + (i * 4)
            pygame.draw.line(surf, (200, 230, 250), (ax, ay), (ax + 2, ay - 1), 1)


def draw_bear_bed(surf, w, h, level, dead_count=0, frame=0):
    """小熊睡床: 床+小熊抱枕+金边+呼噜泡
    dead_count: 队友死亡数, 决定小熊表情(0=平静, 1=微笑, 2+=大笑)和头顶星星"""
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (3, h - 5, w - 6, 4))
    surf.blit(shadow_surf, (0, 0))

    cx, cy = w // 2, h // 2 + 2
    scale = 0.7 + level * 0.08
    bw = int(22 * scale)
    bh = int(16 * scale)
    bx, by = cx - bw // 2, cy - bh // 2 + 2

    # ── 床架 ──
    wood_dark = (90, 60, 30)
    wood_color = (130, 90, 50)
    wood_hi = (170, 130, 80)
    pygame.draw.rect(surf, wood_color, (bx, by, bw, bh))
    pygame.draw.rect(surf, wood_dark, (bx, by, bw, bh), 1)
    pygame.draw.line(surf, wood_hi, (bx, by), (bx + bw - 1, by), 1)

    # ── 金色被褥 ──
    blanket_color = (255, 220, 80)
    blanket_hi = (255, 240, 160)
    blanket_lo = (200, 150, 30)
    pygame.draw.rect(surf, blanket_color, (bx + 1, by + 2, bw - 2, bh - 5))
    pygame.draw.line(surf, blanket_hi, (bx + 1, by + 2), (bx + bw - 2, by + 2), 1)
    pygame.draw.line(surf, blanket_lo, (bx + 1, by + bh - 4), (bx + bw - 2, by + bh - 4), 1)
    # 褶皱
    for fx in (bx + bw // 3, bx + 2 * bw // 3):
        pygame.draw.line(surf, blanket_lo, (fx, by + 3), (fx, by + bh - 5), 1)

    # ── 枕头 ──
    pygame.draw.rect(surf, WHITE, (bx + 2, by + 1, 4, 3))
    pygame.draw.rect(surf, (220, 215, 200), (bx + 2, by + 1, 4, 3), 1)

    # ── 小熊(抱枕样式) ──
    bear_x = bx + bw - 7
    bear_y = by + 3
    bear_color = (150, 100, 55)
    bear_dark = (100, 65, 30)
    bear_hi = (190, 140, 80)
    # 头
    pygame.draw.circle(surf, bear_color, (bear_x, bear_y), 4)
    pygame.draw.circle(surf, bear_dark, (bear_x, bear_y), 4, 1)
    pygame.draw.circle(surf, bear_hi, (bear_x - 1, bear_y - 1), 1)
    # 耳朵
    pygame.draw.circle(surf, bear_color, (bear_x - 2, bear_y - 3), 1)
    pygame.draw.circle(surf, bear_color, (bear_x + 2, bear_y - 3), 1)
    pygame.draw.circle(surf, bear_dark, (bear_x - 2, bear_y - 3), 1, 1)
    pygame.draw.circle(surf, bear_dark, (bear_x + 2, bear_y - 3), 1, 1)

    # 眼睛(根据 dead_count 显示不同表情)
    if dead_count == 0:
        # 闭眼睡觉
        pygame.draw.line(surf, BLACK, (bear_x - 2, bear_y), (bear_x - 1, bear_y), 1)
        pygame.draw.line(surf, BLACK, (bear_x + 1, bear_y), (bear_x + 2, bear_y), 1)
    elif dead_count == 1:
        # 微笑眼(弯月)
        pygame.draw.arc(surf, BLACK, (bear_x - 2, bear_y - 1, 2, 2), 3.14, 6.28, 1)
        pygame.draw.arc(surf, BLACK, (bear_x, bear_y - 1, 2, 2), 3.14, 6.28, 1)
    else:
        # 星星眼(dead_count >= 2)
        for ex in (bear_x - 2, bear_x + 1):
            pygame.draw.line(surf, BLACK, (ex, bear_y - 1), (ex + 1, bear_y), 1)
            pygame.draw.line(surf, BLACK, (ex + 1, bear_y - 1), (ex, bear_y), 1)

    # 鼻子
    pygame.draw.circle(surf, BLACK, (bear_x, bear_y + 1), 1)
    # 嘴(根据 dead_count)
    if dead_count == 0:
        pygame.draw.arc(surf, BLACK, (bear_x - 1, bear_y + 1, 2, 2), 3.14, 6.28, 1)
    elif dead_count == 1:
        pygame.draw.arc(surf, BLACK, (bear_x - 2, bear_y + 1, 4, 2), 0, 3.14, 1)
    else:
        # 大笑
        pygame.draw.arc(surf, BLACK, (bear_x - 2, bear_y + 1, 4, 3), 0, 3.14, 1)
        # 舌头
        pygame.draw.line(surf, (220, 80, 80), (bear_x - 1, bear_y + 3), (bear_x + 1, bear_y + 3), 1)

    # ── 呼噜泡(根据 dead_count 大小) ──
    bubble_r = 2 + min(dead_count, 3)
    pygame.draw.circle(surf, (220, 240, 255, 100), (bear_x + 4, bear_y - 4), bubble_r)
    pygame.draw.circle(surf, WHITE, (bear_x + 4, bear_y - 4), bubble_r, 1)
    pygame.draw.circle(surf, WHITE, (bear_x + 5, bear_y - 7), 1)

    # ── 金边 ──
    pygame.draw.rect(surf, (240, 200, 50), (bx - 1, by - 1, bw + 2, bh + 2), 1)

    # ── 头顶星星(dead_count 越多星星越多, 最多 5 个) ──
    if dead_count > 0:
        star_count = min(dead_count, 5)
        for i in range(star_count):
            # 星星位置在小熊上方, 错开
            phase = (frame + i * 2) % 8
            sx_s = bear_x - 3 + (i - 2) * 2
            sy_s = bear_y - 9 - abs(phase - 4) // 2
            # 黄色小十字(代表星星)
            pygame.draw.line(surf, (255, 220, 80), (sx_s - 1, sy_s), (sx_s + 1, sy_s), 1)
            pygame.draw.line(surf, (255, 220, 80), (sx_s, sy_s - 1), (sx_s, sy_s + 1), 1)
            pygame.draw.line(surf, (255, 255, 200), (sx_s, sy_s), (sx_s, sy_s), 1)


def draw_sword(surf, w, h, frame=0, casting=False):
    """屠龙刀: 剑身+护手+握柄+宝石+剑鞘
    casting=True 时整体金色外发光, 表示刚发动攻击"""
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (4, h - 4, w - 8, 3))
    surf.blit(shadow_surf, (0, 0))

    # 激活时金色外发光
    if casting:
        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        for r, a in [(16, 40), (12, 70), (8, 100)]:
            pygame.draw.circle(glow, (255, 220, 80, a), (w // 2, h // 2), r)
        surf.blit(glow, (0, 0))

    cx, cy = w // 2, h // 2

    # 剑身角度(轻微摆动)
    angle = math.radians(-35 + frame * 8)
    cos_a, sin_a = math.cos(angle), math.sin(angle)

    def _rot(dx, dy):
        return cx + int(dx * cos_a - dy * sin_a), cy + int(dx * sin_a + dy * cos_a)

    # ── 剑鞘(底部, 红色) ──
    scabbard_top = _rot(-12, 10)
    scabbard_bot = _rot(-16, 16)
    pygame.draw.line(surf, (120, 20, 30), scabbard_top, scabbard_bot, 3)
    pygame.draw.line(surf, (180, 50, 60), scabbard_top, scabbard_bot, 1)
    # 鞘口金边
    scabbard_mouth = _rot(-13, 11)
    pygame.draw.circle(surf, GOLD, scabbard_mouth, 2)
    pygame.draw.circle(surf, (255, 240, 130), scabbard_mouth, 1)

    # ── 剑身(从护手到剑尖) ──
    blade_dark = (180, 180, 200)
    blade_color = (220, 225, 245)
    blade_hi = WHITE if casting else (255, 255, 255)
    blade_p1 = _rot(0, -10)
    blade_p2 = _rot(2, -10)
    blade_p3 = _rot(0, 10)
    blade_p4 = _rot(-2, -10)
    blade_p5 = _rot(15, -2)  # 剑尖
    pygame.draw.polygon(surf, blade_dark, [blade_p1, blade_p2, blade_p5, blade_p3, blade_p4])
    pygame.draw.polygon(surf, blade_color, [_rot(1, -8), _rot(1, 8), _rot(14, -2), _rot(0, 8), _rot(0, -8)])
    # 剑身高光(激活时变金白)
    pygame.draw.line(surf, blade_hi, _rot(0, -7), _rot(13, -1), 1)
    # 血槽
    pygame.draw.line(surf, (150, 150, 170), _rot(2, 0), _rot(10, 0), 1)

    # ── 护手(金色横条) ──
    guard_color = (200, 160, 30)
    guard_hi = (255, 220, 100)
    pygame.draw.line(surf, guard_color, _rot(-5, 0), _rot(3, 0), 3)
    pygame.draw.line(surf, guard_hi, _rot(-5, 0), _rot(3, 0), 1)
    # 护手宝石
    pygame.draw.circle(surf, (200, 30, 30), _rot(-1, 0), 2)
    pygame.draw.circle(surf, (255, 100, 100), _rot(-1, 0), 1)

    # ── 握柄(金线缠绕) ──
    handle_color = (90, 50, 25)
    handle_hi = (140, 90, 50)
    pygame.draw.line(surf, handle_color, _rot(-13, 0), _rot(-5, 0), 4)
    # 金线
    for i in range(3):
        p1 = _rot(-13 + i * 3, 0)
        p2 = _rot(-12 + i * 3, 0)
        pygame.draw.line(surf, GOLD, p1, p2, 1)
    pygame.draw.line(surf, handle_hi, _rot(-12, -1), _rot(-6, -1), 1)

    # ── 剑首(红宝石) ──
    pommel = _rot(-14, 0)
    pygame.draw.circle(surf, (160, 30, 30), pommel, 3)
    pygame.draw.circle(surf, (220, 60, 60), pommel, 2)
    pygame.draw.circle(surf, (255, 200, 200), _rot(-15, -1), 1)


def draw_sword_animated(surf, w, h, slash_angle=0.0, frame=0):
    """屠龙刀动画版: 以指定角度(度数)绘制整把刀, 用于飞行/砍击动画
    slash_angle: 刀的旋转角度(度), 0=竖直(剑尖朝上), -90=横放(平砍)"""
    # 底部阴影
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 60), (4, h - 4, w - 8, 3))
    surf.blit(shadow_surf, (0, 0))

    # 飞行/砍击时金色外发光
    glow = pygame.Surface((w, h), pygame.SRCALPHA)
    for r, a in [(20, 50), (15, 80), (10, 120)]:
        pygame.draw.circle(glow, (255, 220, 80, a), (w // 2, h // 2), r)
    surf.blit(glow, (0, 0))

    cx, cy = w // 2, h // 2
    # 基础角度 + 动画角度
    base_angle = math.radians(-35 + frame * 4)
    anim_angle = math.radians(slash_angle)
    total_angle = base_angle + anim_angle
    cos_a, sin_a = math.cos(total_angle), math.sin(total_angle)

    def _rot(dx, dy):
        return cx + int(dx * cos_a - dy * sin_a), cy + int(dx * sin_a + dy * cos_a)

    # ── 剑鞘(底部, 红色) ──
    scabbard_top = _rot(-12, 10)
    scabbard_bot = _rot(-16, 16)
    pygame.draw.line(surf, (120, 20, 30), scabbard_top, scabbard_bot, 3)
    pygame.draw.line(surf, (180, 50, 60), scabbard_top, scabbard_bot, 1)
    scabbard_mouth = _rot(-13, 11)
    pygame.draw.circle(surf, GOLD, scabbard_mouth, 2)
    pygame.draw.circle(surf, (255, 240, 130), scabbard_mouth, 1)

    # ── 剑身 ──
    blade_dark = (180, 180, 200)
    blade_color = (220, 225, 245)
    blade_hi = (255, 255, 255)  # 动画时剑身始终高亮
    blade_p1 = _rot(0, -10)
    blade_p2 = _rot(2, -10)
    blade_p3 = _rot(0, 10)
    blade_p4 = _rot(-2, -10)
    blade_p5 = _rot(15, -2)  # 剑尖
    pygame.draw.polygon(surf, blade_dark, [blade_p1, blade_p2, blade_p5, blade_p3, blade_p4])
    pygame.draw.polygon(surf, blade_color, [_rot(1, -8), _rot(1, 8), _rot(14, -2), _rot(0, 8), _rot(0, -8)])
    pygame.draw.line(surf, blade_hi, _rot(0, -7), _rot(13, -1), 1)
    pygame.draw.line(surf, (150, 150, 170), _rot(2, 0), _rot(10, 0), 1)

    # ── 护手(金色横条) ──
    guard_color = (200, 160, 30)
    guard_hi = (255, 220, 100)
    pygame.draw.line(surf, guard_color, _rot(0, -8), _rot(0, 8), 3)
    pygame.draw.line(surf, guard_hi, _rot(0, -7), _rot(0, -7), 1)
    pygame.draw.line(surf, (140, 100, 10), _rot(0, 8), _rot(0, 8), 1)
    gem = _rot(0, 0)
    pygame.draw.circle(surf, (180, 30, 30), gem, 2)
    pygame.draw.circle(surf, (255, 80, 80), gem, 1)

    # ── 握柄(缠绕金线) ──
    handle_color = (110, 65, 25)
    handle_hi = (160, 100, 50)
    pygame.draw.line(surf, handle_color, _rot(-2, -8), _rot(-12, -8), 3)
    pygame.draw.line(surf, handle_color, _rot(-2, 8), _rot(-12, 8), 3)
    pygame.draw.line(surf, handle_color, _rot(-2, -8), _rot(-2, 8), 3)
    pygame.draw.line(surf, handle_color, _rot(-12, -8), _rot(-12, 8), 3)
    pygame.draw.line(surf, handle_hi, _rot(-2, -7), _rot(-12, -7), 1)
    pygame.draw.line(surf, handle_hi, _rot(-2, 7), _rot(-12, 7), 1)
    for i in range(3):
        p1 = _rot(-13 + i * 3, 0)
        p2 = _rot(-12 + i * 3, 0)
        pygame.draw.line(surf, GOLD, p1, p2, 1)
    pygame.draw.line(surf, handle_hi, _rot(-12, -1), _rot(-6, -1), 1)

    # ── 剑首(红宝石) ──
    pommel = _rot(-14, 0)
    pygame.draw.circle(surf, (160, 30, 30), pommel, 3)
    pygame.draw.circle(surf, (220, 60, 60), pommel, 2)
    pygame.draw.circle(surf, (255, 200, 200), _rot(-15, -1), 1)

    # ── 砍击瞬间的金色弧线轨迹 ──
    if slash_angle > -85:  # 砍下过程的中后段才显示
        trail = pygame.Surface((w, h), pygame.SRCALPHA)
        # 弧线: 从左上到右下
        arc_alpha = int(180 * (1.0 - abs(slash_angle) / 90.0))
        pygame.draw.arc(trail, (255, 230, 120, max(50, arc_alpha)),
                        (4, 4, w - 8, h - 8),
                        math.radians(135), math.radians(135 + (90 + slash_angle)))
        pygame.draw.arc(trail, (255, 250, 200, max(80, arc_alpha + 30)),
                        (8, 8, w - 16, h - 16),
                        math.radians(135), math.radians(135 + (90 + slash_angle)))
        surf.blit(trail, (0, 0))


def draw_hunter_sprite(surf, w, h, level, hunter_type=0, berserk=False,
                       clone_alpha=255, frame=0, extra_state=None):
    """像素猎梦者: 5 种类型强差异化
    - HUNTER_SUNNY 晴天娃娃: 白色圆形身体+黑眼睛+悬挂线+狂暴时火焰
    - HUNTER_BIGHEAD 大头: 头部占70%+2根呆毛+大嘴咀嚼+狂暴时头发竖起
    - HUNTER_GRANDMA 孙婆婆: 白头发盘髻+深色衣服+皱纹
    - HUNTER_BANDAGE 绷带: 全身绷带+绿眼+回血时绿色脉冲
    - HUNTER_REDDRESS 红裙小女孩: 红色连衣裙+黑色头发+苍白脸
    clone_alpha: 分身透明度(255=本体, 160=分身)
    extra_state: 额外状态 dict, 如 {'healing': True, 'tongue_firing': True}"""
    surf.fill((0, 0, 0, 0))
    cx, cy = w // 2, h // 2
    body_r = w // 3 + level // 2

    extra = extra_state or {}

    # 摆动偏移(用于"飘"的感觉, 每 0.3s 切换)
    sway = 1 if (frame // 3) % 2 == 0 else -1

    # ── 种类配色方案 ──
    type_colors = {
        HUNTER_SUNNY:    ((245, 240, 225), (170, 165, 150), (255, 252, 240)),  # 布偶白
        HUNTER_BIGHEAD:  ((190, 60, 60),   (130, 30, 30),   (230, 110, 110)),  # 大头红
        HUNTER_GRANDMA:  ((140, 80, 160),  (90, 40, 110),   (190, 140, 210)),  # 紫袍
        HUNTER_BANDAGE:  ((225, 215, 195), (170, 160, 140), (248, 245, 230)),  # 绷带白
        HUNTER_REDDRESS: ((210, 40, 70),   (140, 15, 35),   (245, 90, 110)),   # 红裙
    }
    body_color, body_dark, body_hi = type_colors.get(hunter_type,
        ((100 + level * 10, 15, 150 + level * 8), (40, 5, 80), (160, 50, 200)))

    # 分身颜色: 比本体淡 30%
    if clone_alpha < 200:
        body_color = (
            min(255, body_color[0] + 60),
            min(255, body_color[1] + 60),
            min(255, body_color[2] + 60),
        )
        body_dark = (
            min(255, body_dark[0] + 40),
            min(255, body_dark[1] + 40),
            min(255, body_dark[2] + 40),
        )

    # 狂暴时整体偏红
    if berserk:
        body_color = (min(255, body_color[0] + 60), max(0, body_color[1] - 30), max(0, body_color[2] - 30))
        body_hi = (255, min(255, body_hi[1] + 40), min(255, body_hi[2] + 40))

    # ── 光晕(威慑) ──
    aura = pygame.Surface((body_r * 4, body_r * 4), pygame.SRCALPHA)
    if berserk:
        aura_color = (255, 60, 60, 80)
    elif hunter_type == HUNTER_BANDAGE and extra.get('healing'):
        aura_color = (100, 255, 120, 70)  # 回血时绿色光晕
    else:
        aura_color = (140, 30, 200, 25)
    for r, a in [(body_r * 2, aura_color[3]), (body_r * 1, aura_color[3] + 15)]:
        pygame.draw.circle(aura, aura_color[:3] + (a,),
                           (body_r * 2, body_r * 2), r)
    surf.blit(aura, (cx - body_r * 2, cy - body_r * 2))

    # ── 各类专属绘制(分支调度) ──
    if hunter_type == HUNTER_SUNNY:
        # 晴天娃娃(布偶扫晴娘)
        # 顶部悬挂线
        pygame.draw.line(surf, (160, 140, 100), (cx, cy - body_r - 6), (cx, cy - body_r), 1)
        # 悬挂环
        pygame.draw.circle(surf, (160, 140, 100), (cx, cy - body_r - 6), 2, 1)

        # 圆头(白色, 比身体大)
        head_r_sunny = body_r + 1
        # 摆动(头部随 frame 左右偏移)
        head_cx = cx + sway
        pygame.draw.circle(surf, body_dark, (head_cx, cy - 2), head_r_sunny)
        pygame.draw.circle(surf, body_color, (head_cx, cy - 2), head_r_sunny - 1)
        # 高光
        pygame.draw.circle(surf, body_hi, (head_cx - 2, cy - 5), head_r_sunny // 3)
        # 红色脸颊(晴天娃娃标志性)
        pygame.draw.circle(surf, (240, 130, 130), (head_cx - 3, cy + 1), 1)
        pygame.draw.circle(surf, (240, 130, 130), (head_cx + 3, cy + 1), 1)

        # 三角布身体(头部下方, 也随摆动偏移)
        body_top_y = cy + head_r_sunny - 3
        body_bot_y = cy + head_r_sunny + 6 + level
        pygame.draw.polygon(surf, body_dark, [
            (head_cx - body_r - 2, body_top_y),
            (head_cx + body_r + 2, body_top_y),
            (head_cx, body_bot_y + 2)
        ])
        pygame.draw.polygon(surf, body_color, [
            (head_cx - body_r, body_top_y + 1),
            (head_cx + body_r, body_top_y + 1),
            (head_cx, body_bot_y)
        ])
        # 布身中线(缝合线)
        pygame.draw.line(surf, body_dark, (head_cx, body_top_y + 1), (head_cx, body_bot_y), 1)

        # 表情
        eye_y = cy - 3
        if not berserk:
            # 默认: 黑眼睛小圆点
            pygame.draw.circle(surf, BLACK, (head_cx - 3, eye_y), 1)
            pygame.draw.circle(surf, BLACK, (head_cx + 3, eye_y), 1)
            # 微笑弧线
            pygame.draw.arc(surf, BLACK, (head_cx - 3, eye_y, 6, 5), 3.14, 6.28, 1)
        else:
            # 狂暴: 怒目红眼
            pygame.draw.circle(surf, (255, 30, 30), (head_cx - 3, eye_y), 2)
            pygame.draw.circle(surf, (255, 30, 30), (head_cx + 3, eye_y), 2)
            pygame.draw.circle(surf, (255, 200, 100), (head_cx - 3, eye_y), 1)
            pygame.draw.circle(surf, (255, 200, 100), (head_cx + 3, eye_y), 1)
            # 怒嘴
            pygame.draw.arc(surf, (255, 30, 30), (head_cx - 3, cy + 1, 6, 4), 0, 3.14, 1)

        # 狂暴时身体周围红色火焰粒子
        if berserk:
            for i in range(4):
                phase = (frame + i * 3) % 12
                if phase < 10:
                    ang = math.radians(i * 90 + phase * 5)
                    fx = head_cx + int(math.cos(ang) * (body_r + 3 + phase // 2))
                    fy = cy + int(math.sin(ang) * (body_r + 3 + phase // 2)) // 2
                    # 火焰三角
                    flame_color = (255, 80 + phase * 10, 30)
                    pygame.draw.polygon(surf, flame_color, [
                        (fx, fy - 2), (fx - 1, fy), (fx + 1, fy)
                    ])
                    pygame.draw.circle(surf, (255, 220, 80), (fx, fy - 1), 1)

    elif hunter_type == HUNTER_BIGHEAD:
        # 大头: 头部占 70% + 2 根呆毛
        # 头部尺寸 = body_r + 4
        head_r_bh = body_r + 4 + level
        # 呆毛(2 根竖立, 随狂暴/移动状态变化)
        if berserk:
            # 狂暴: 头发竖起
            pygame.draw.line(surf, (80, 20, 20), (cx - 3, cy - head_r_bh - 1),
                             (cx - 5, cy - head_r_bh - 6), 1)
            pygame.draw.line(surf, (80, 20, 20), (cx + 3, cy - head_r_bh - 1),
                             (cx + 5, cy - head_r_bh - 6), 1)
        else:
            # 平时: 2 根弯曲呆毛
            pygame.draw.line(surf, (80, 20, 20), (cx - 3, cy - head_r_bh - 1),
                             (cx - 4, cy - head_r_bh - 5), 1)
            pygame.draw.line(surf, (80, 20, 20), (cx + 3, cy - head_r_bh - 1),
                             (cx + 4, cy - head_r_bh - 5), 1)

        # 头部(大)
        pygame.draw.circle(surf, body_dark, (cx, cy - 2), head_r_bh + 1)
        pygame.draw.circle(surf, body_color, (cx, cy - 2), head_r_bh)
        # 高光
        pygame.draw.circle(surf, body_hi, (cx - 3, cy - head_r_bh + 1), head_r_bh // 3)

        # 身体(小, 藏在头部下方)
        body_top_y = cy + head_r_bh - 4
        body_bot_y = cy + head_r_bh + 4
        pygame.draw.polygon(surf, body_dark, [
            (cx - body_r - 2, body_top_y),
            (cx + body_r + 2, body_top_y),
            (cx + body_r, body_bot_y),
            (cx - body_r, body_bot_y)
        ])
        pygame.draw.polygon(surf, body_color, [
            (cx - body_r, body_top_y + 1),
            (cx + body_r, body_top_y + 1),
            (cx + body_r - 1, body_bot_y - 1),
            (cx - body_r + 1, body_bot_y - 1)
        ])

        # 眼睛(红色, 较小, 凶狠)
        eye_y = cy - 3
        eye_color = (255, 30, 30) if berserk else (200, 30, 30)
        pygame.draw.circle(surf, eye_color, (cx - head_r_bh // 3, eye_y), 1)
        pygame.draw.circle(surf, eye_color, (cx + head_r_bh // 3, eye_y), 1)
        pygame.draw.circle(surf, (255, 200, 100), (cx - head_r_bh // 3, eye_y), 1)
        pygame.draw.circle(surf, (255, 200, 100), (cx + head_r_bh // 3, eye_y), 1)

        # 大嘴(一张一合, frame 决定)
        mouth_open = (frame // 4) % 2
        if mouth_open:
            # 张嘴: 椭圆嘴 + 内红
            pygame.draw.ellipse(surf, (50, 10, 10), (cx - 3, cy + 1, 6, 4))
            pygame.draw.ellipse(surf, (200, 30, 30), (cx - 2, cy + 1, 4, 3))
            # 牙齿
            pygame.draw.line(surf, (255, 255, 230), (cx - 1, cy + 1), (cx - 1, cy + 2), 1)
            pygame.draw.line(surf, (255, 255, 230), (cx + 1, cy + 1), (cx + 1, cy + 2), 1)
        else:
            # 闭嘴: 横线
            pygame.draw.line(surf, (40, 10, 10), (cx - 3, cy + 1), (cx + 3, cy + 1), 1)

        # 狂暴时火焰粒子
        if berserk:
            for i in range(3):
                phase = (frame + i * 4) % 10
                if phase < 8:
                    fx = cx + (i - 1) * 5
                    fy = cy - head_r_bh - 2 - phase
                    pygame.draw.polygon(surf, (255, 120, 30), [
                        (fx, fy - 2), (fx - 1, fy), (fx + 1, fy)
                    ])

    elif hunter_type == HUNTER_GRANDMA:
        # 孙婆婆: 白头发盘髻 + 深色衣服
        # 头发盘髻(顶部圆形)
        bun_y = cy - body_r - 3
        pygame.draw.circle(surf, (220, 215, 200), (cx, bun_y), 4)  # 浅色发髻
        pygame.draw.circle(surf, (180, 175, 160), (cx, bun_y), 4, 1)
        # 发髻装饰(一根簪子)
        pygame.draw.line(surf, (180, 50, 50), (cx - 2, bun_y - 2), (cx + 2, bun_y + 2), 1)

        # 头部(脸部, 紫色调)
        pygame.draw.ellipse(surf, body_dark, (cx - body_r, cy - body_r, body_r * 2, body_r * 2))
        pygame.draw.ellipse(surf, body_color, (cx - body_r + 1, cy - body_r + 1,
                                              body_r * 2 - 2, body_r * 2 - 2))
        # 高光
        pygame.draw.ellipse(surf, body_hi, (cx - body_r // 2, cy - body_r, body_r, body_r // 2))

        # 皱纹(额头/脸颊 3-4 条横线)
        for i in range(3):
            wy = cy - 3 + i * 3
            pygame.draw.line(surf, (60, 30, 80), (cx - body_r // 2, wy),
                             (cx + body_r // 2, wy), 1)

        # 眼睛(暗紫色眼)
        eye_y = cy - body_r // 3
        pygame.draw.circle(surf, (200, 180, 220), (cx - body_r // 2, eye_y), 1)
        pygame.draw.circle(surf, (200, 180, 220), (cx + body_r // 2, eye_y), 1)
        pygame.draw.circle(surf, (60, 30, 80), (cx - body_r // 2, eye_y), 1)
        pygame.draw.circle(surf, (60, 30, 80), (cx + body_r // 2, eye_y), 1)

        # 嘴(小, 老年人嘴)
        pygame.draw.arc(surf, (50, 25, 70), (cx - 2, cy + 2, 4, 3), 3.14, 6.28, 1)

        # 衣领(深色 V 领)
        pygame.draw.polygon(surf, (40, 20, 60), [
            (cx - body_r - 1, cy + body_r - 2),
            (cx + body_r + 1, cy + body_r - 2),
            (cx + 3, cy + body_r + 2),
            (cx - 3, cy + body_r + 2)
        ])
        # 衣领高光
        pygame.draw.line(surf, (90, 50, 110), (cx - 3, cy + body_r + 1),
                         (cx + 3, cy + body_r + 1), 1)

    elif hunter_type == HUNTER_BANDAGE:
        # 绷带猎梦者: 全身绷带 + 绿眼 + 残血/回血时特殊
        # 主体(暗肤色作为底层)
        pygame.draw.ellipse(surf, body_dark, (cx - body_r, cy - body_r, body_r * 2, body_r * 2))
        pygame.draw.ellipse(surf, body_color, (cx - body_r + 1, cy - body_r + 1,
                                              body_r * 2 - 2, body_r * 2 - 2))
        # 高光
        pygame.draw.ellipse(surf, body_hi, (cx - body_r // 2, cy - body_r, body_r, body_r // 2))

        # 残血时: 绷带松散, 拖在地上
        # 通过 extra 中的 low_hp_ratio 决定松散程度
        low_hp = extra.get('low_hp_ratio', 0)
        is_loose = low_hp > 0.3
        # 横向绷带 3-4 条(白色横纹, 残血时出现错位和下垂)
        for i in range(4):
            wy = cy - body_r + 2 + i * (body_r // 2)
            # 残血时: 绷带错位、拖在地上
            if is_loose:
                offset_x = ((i + 1) % 2) * (1 if i % 2 == 0 else -1)
                trail_y = cy + body_r + 2 + i  # 拖地
                pygame.draw.line(surf, (220, 215, 200), (cx - body_r + 2 + offset_x, wy + 1),
                                 (cx + body_r - 2 + offset_x, wy + 1), 1)
                # 拖地尾巴
                pygame.draw.line(surf, (200, 195, 180), (cx - body_r + offset_x, wy + 1),
                                 (cx - body_r - 1 + offset_x, trail_y), 1)
            else:
                pygame.draw.line(surf, (240, 235, 220), (cx - body_r + 1, wy),
                                 (cx + body_r - 1, wy), 1)
                # 绷带阴影
                pygame.draw.line(surf, (180, 170, 150), (cx - body_r + 1, wy + 1),
                                 (cx + body_r - 1, wy + 1), 1)

        # 眼睛(绿色, 从绷带缝里露出)
        eye_y = cy - body_r // 3
        pygame.draw.circle(surf, (60, 200, 80), (cx - body_r // 2, eye_y), 1)
        pygame.draw.circle(surf, (60, 200, 80), (cx + body_r // 2, eye_y), 1)
        pygame.draw.circle(surf, (160, 255, 180), (cx - body_r // 2, eye_y), 1)
        pygame.draw.circle(surf, (160, 255, 180), (cx + body_r // 2, eye_y), 1)

        # 嘴(绷带覆盖, 黑色横线)
        pygame.draw.line(surf, (40, 40, 50), (cx - 2, cy + 2), (cx + 2, cy + 2), 1)

        # 回血时绿色脉冲光
        if extra.get('healing'):
            phase = frame % 6
            for r_off, a in [(4, 100), (7, 60), (10, 30)]:
                if phase < 4:
                    r = body_r + r_off
                    alpha = int(a * (1.0 - phase / 4))
                    glow = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(glow, (100, 255, 130, alpha), (r, r), r, 1)
                    surf.blit(glow, (cx - r, cy - r))

    elif hunter_type == HUNTER_REDDRESS:
        # 红裙小女孩: 红色连衣裙(梯形) + 黑色头发 + 苍白脸
        # 炮停触发时: 整张精灵旋转(原地转一圈)
        spin = extra.get('spin_trigger', False)
        if spin:
            # 将精灵旋转后绘制(每0.4秒转一圈)
            spin_angle = (frame * 22.5) % 360  # 16帧一圈
            spin_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            _draw_red_dress_body(spin_surf, w, h, cx, cy, body_r, body_color, body_dark, body_hi)
            rotated = pygame.transform.rotate(spin_surf, spin_angle)
            rot_rect = rotated.get_rect(center=(cx, cy))
            surf.blit(rotated, rot_rect.topleft)
        else:
            _draw_red_dress_body(surf, w, h, cx, cy, body_r, body_color, body_dark, body_hi)

    else:
        # 通用兜底
        pygame.draw.ellipse(surf, body_dark, (cx - body_r, cy - body_r, body_r * 2, body_r * 2))
        pygame.draw.ellipse(surf, body_color, (cx - body_r + 1, cy - body_r + 1,
                                              body_r * 2 - 2, body_r * 2 - 2))

    # ── 触手(底部) - 晴天娃娃/红裙小女孩跳过(布偶/裙子无触手) ──
    if hunter_type not in (HUNTER_SUNNY, HUNTER_REDDRESS):
        for tx in range(cx - body_r + 2, cx + body_r - 2, 3):
            pygame.draw.line(surf, body_dark, (tx, cy + body_r - 2),
                             (tx - 1, cy + body_r + 1), 2)
            pygame.draw.line(surf, body_color, (tx, cy + body_r - 2),
                             (tx - 1, cy + body_r), 1)
    elif hunter_type == HUNTER_REDDRESS:
        # 红色裙边小波纹
        pygame.draw.line(surf, (160, 15, 35), (cx - body_r - 2, cy + body_r + 4),
                         (cx + body_r + 2, cy + body_r + 4), 1)


def _draw_turret_disabled_overlay(viewport, x, y, w, h):
    """炮塔被红裙小女孩炮停时: 整体变灰 + 红色X覆盖"""
    # 灰色半透明滤镜
    gray = pygame.Surface((w, h), pygame.SRCALPHA)
    gray.fill((80, 80, 90, 100))
    viewport.blit(gray, (x, y))
    # 红色 X(两条对角线)
    cx, cy = x + w // 2, y + h // 2
    # 红色描边
    pygame.draw.line(viewport, (40, 10, 10), (x + 4, y + 4), (x + w - 5, y + h - 5), 3)
    pygame.draw.line(viewport, (40, 10, 10), (x + w - 5, y + 4), (x + 4, y + h - 5), 3)
    # 红色主体
    pygame.draw.line(viewport, (220, 30, 30), (x + 5, y + 5), (x + w - 6, y + h - 6), 2)
    pygame.draw.line(viewport, (220, 30, 30), (x + w - 6, y + 5), (x + 5, y + h - 6), 2)


def _draw_red_dress_body(surf, w, h, cx, cy, body_r, body_color, body_dark, body_hi):
    """红裙小女孩身体绘制 - 独立函数便于旋转"""
    # 黑色头发(头顶块, 覆盖头部)
    pygame.draw.polygon(surf, (30, 20, 30), [
        (cx - body_r, cy - body_r),
        (cx + body_r, cy - body_r),
        (cx + body_r - 1, cy - body_r // 2),
        (cx - body_r + 1, cy - body_r // 2)
    ])
    # 头发下垂(刘海)
    pygame.draw.polygon(surf, (30, 20, 30), [
        (cx - body_r, cy - body_r + 1),
        (cx - body_r + 2, cy - body_r // 2),
        (cx - 2, cy - 1),
        (cx - body_r + 4, cy - body_r + 1)
    ])
    pygame.draw.polygon(surf, (30, 20, 30), [
        (cx + body_r, cy - body_r + 1),
        (cx + body_r - 2, cy - body_r // 2),
        (cx + 2, cy - 1),
        (cx + body_r - 4, cy - body_r + 1)
    ])

    # 苍白圆脸
    face_color = (240, 230, 230)
    face_dark = (200, 180, 180)
    pygame.draw.ellipse(surf, face_dark, (cx - body_r, cy - body_r, body_r * 2, body_r * 2))
    pygame.draw.ellipse(surf, face_color, (cx - body_r + 1, cy - body_r + 1,
                                          body_r * 2 - 2, body_r * 2 - 2))
    # 脸高光
    pygame.draw.ellipse(surf, (255, 250, 250), (cx - body_r // 2, cy - body_r, body_r, body_r // 2))

    # 大而黑的眼睛(略恐怖)
    eye_y = cy - body_r // 4
    pygame.draw.circle(surf, BLACK, (cx - body_r // 2, eye_y), 1)
    pygame.draw.circle(surf, BLACK, (cx + body_r // 2, eye_y), 1)
    # 眼睛光点
    pygame.draw.circle(surf, WHITE, (cx - body_r // 2, eye_y - 1), 1)
    pygame.draw.circle(surf, WHITE, (cx + body_r // 2, eye_y - 1), 1)

    # 小嘴
    pygame.draw.line(surf, (160, 80, 80), (cx - 1, cy + 1), (cx + 1, cy + 1), 1)

    # 红色连衣裙(梯形裙摆, 主体下方)
    skirt_top_y = cy + body_r - 4
    skirt_bot_y = cy + body_r + 4
    pygame.draw.polygon(surf, (180, 20, 40), [
        (cx - body_r, skirt_top_y),
        (cx + body_r, skirt_top_y),
        (cx + body_r + 2, skirt_bot_y),
        (cx - body_r - 2, skirt_bot_y),
    ])
    pygame.draw.polygon(surf, (220, 50, 70), [
        (cx - body_r + 1, skirt_top_y + 1),
        (cx + body_r - 1, skirt_top_y + 1),
        (cx + body_r, skirt_bot_y - 1),
        (cx - body_r, skirt_bot_y - 1),
    ])
    # 裙摆高光
    pygame.draw.line(surf, (255, 150, 160), (cx - body_r + 1, skirt_top_y + 1),
                     (cx + body_r - 1, skirt_top_y + 1), 1)
    # 蝴蝶结(头顶)
    pygame.draw.polygon(surf, (255, 200, 200), [
        (cx - 3, cy - body_r - 1), (cx, cy - body_r - 3),
        (cx + 3, cy - body_r - 1), (cx, cy - body_r + 1)
    ])
    pygame.draw.circle(surf, (220, 100, 130), (cx, cy - body_r), 1)


def draw_door_arrow_tile(surf, w, h, corridor_draw_func=None):
    """房门外侧标记(绿色双箭头): 在当前地图的走廊样式上印着两个渐变的<<绿色箭头"""
    # 底层: 走廊地砖(使用传入的绘制函数, 若未提供则用默认木质走廊)
    if corridor_draw_func is not None:
        corridor_draw_func(surf, w, h)
    else:
        draw_corridor_tile(surf, w, h)

    # ── 两个渐变的绿色左箭头 << ──
    cx = w // 2
    cy = h // 2
    arrow_gap = 5  # 两个箭头间距

    # 左箭头 (<< 的左边那个)
    _draw_single_chevron_arrow(surf, cx - arrow_gap // 2 - 5, cy, 6, 10, alpha=180)
    # 右箭头 (<< 的右边那个)
    _draw_single_chevron_arrow(surf, cx + arrow_gap // 2 + 1, cy, 6, 10, alpha=255)


def _draw_single_chevron_arrow(surf, cx, cy, width, height, alpha=255):
    """绘制单个渐变的<箭头(chevron形状)"""
    # 渐变颜色: 根据alpha值调整
    green_base = (40, 180, 60)
    green_dark = (20, 110, 40)
    green_hi = (90, 220, 110)

    # 根据alpha混合颜色
    if alpha < 255:
        factor = alpha / 255.0
        color = (
            int(green_base[0] * factor + 50 * (1 - factor)),
            int(green_base[1] * factor + 40 * (1 - factor)),
            int(green_base[2] * factor + 30 * (1 - factor)),
        )
    else:
        color = green_base

    half_h = height // 2
    # chevron < 形状: 三个点构成V形向左
    # 外描边
    outer_pts = [
        (cx + width, cy - half_h),   # 右上
        (cx, cy),                      # 左尖
        (cx + width, cy + half_h),   # 右下
    ]
    pygame.draw.polygon(surf, green_dark, outer_pts)
    # 内部填充(稍小)
    inner_pts = [
        (cx + width - 1, cy - half_h + 1),
        (cx + 1, cy),
        (cx + width - 1, cy + half_h - 1),
    ]
    pygame.draw.polygon(surf, color, inner_pts)
    # 高光(上边)
    pygame.draw.line(surf, green_hi, (cx + width, cy - half_h), (cx + 1, cy), 1)


def draw_red_channel_tile(surf, w, h, direction='S'):
    """红色通道(雪地地图专用)
    视觉: 红色地板 + 中央绿色三角箭头, 箭头方向指向房间内部
    direction: 'N'/'S'/'E'/'W'/'inner'
        - 'N': 门在房间北墙, 房间在门的南侧, 箭头朝下(指南)
        - 'S': 门在房间南墙, 房间在门的北侧, 箭头朝上(指北)
        - 'E': 门在房间东墙, 房间在门的西侧, 箭头朝左(指西)
        - 'W': 门在房间西墙, 房间在门的东侧, 箭头朝右(指东)
        - 'inner': 跨房间通道, 箭头朝上(默认)
    """
    # 底层: 红色(略带深色阴影)
    surf.fill((180, 50, 50))
    # 暗色砖块纹理(深浅交错)
    for row in range(0, h, 8):
        if (row // 8) % 2 == 0:
            base = (190, 60, 60)
        else:
            base = (160, 40, 40)
        pygame.draw.rect(surf, base, (0, row, w, 8))
        # 阴影线
        pygame.draw.line(surf, (130, 30, 30), (0, row + 7), (w, row + 7), 1)
    # 整体描边
    pygame.draw.rect(surf, (110, 20, 20), (0, 0, w, h), 1)
    # 高光顶部
    pygame.draw.line(surf, (220, 90, 90), (0, 0), (w, 0), 1)
    # 底部阴影
    pygame.draw.line(surf, (90, 15, 15), (0, h - 1), (w, h - 1), 1)

    # ── 绿色三角箭头(根据方向旋转) ──
    cx = w // 2
    cy = h // 2
    arrow_color = (40, 200, 70)     # 主绿(亮)
    arrow_dark = (20, 130, 40)     # 暗绿
    arrow_hi = (120, 240, 130)     # 亮绿
    arrow_glow = (80, 220, 100, 90)  # 光晕

    # 基础箭头形状(指向上方)
    tip_y = 6
    base_y = h - 6
    half_w = 8
    base_points_up = [
        (cx, tip_y),                 # 顶点
        (cx - half_w, base_y),       # 左下
        (cx + half_w, base_y),       # 右下
    ]
    inner_up = [
        (cx, tip_y + 2),
        (cx - half_w + 1, base_y - 1),
        (cx + half_w - 1, base_y - 1),
    ]
    handle_up = pygame.Rect(cx - 1, base_y - 1, 3, 3)

    # 根据 direction 旋转
    if direction == 'S':
        # 门在南墙, 房间在北, 箭头指北(向上)
        points = base_points_up
        inner = inner_up
        handle = handle_up
        tip_hl = (cx, tip_y + 2)
    elif direction == 'N':
        # 门在北墙, 房间在南, 箭头指南(向下)
        tip_y_d = h - 6
        base_y_d = 6
        points = [(cx, tip_y_d), (cx - half_w, base_y_d), (cx + half_w, base_y_d)]
        inner = [(cx, tip_y_d - 2), (cx - half_w + 1, base_y_d + 1), (cx + half_w - 1, base_y_d + 1)]
        handle = pygame.Rect(cx - 1, base_y_d - 2, 3, 3)
        tip_hl = (cx, tip_y_d - 2)
    elif direction == 'W':
        # 门在西墙, 房间在东, 箭头指东(向右)
        tip_x_r = w - 6
        base_x_r = 6
        points = [(tip_x_r, cy), (base_x_r, cy - half_w), (base_x_r, cy + half_w)]
        inner = [(tip_x_r - 2, cy), (base_x_r + 1, cy - half_w + 1), (base_x_r + 1, cy + half_w - 1)]
        handle = pygame.Rect(base_x_r - 2, cy - 1, 3, 3)
        tip_hl = (tip_x_r - 2, cy)
    elif direction == 'E':
        # 门在东墙, 房间在西, 箭头指西(向左)
        tip_x_l = 6
        base_x_l = w - 6
        points = [(tip_x_l, cy), (base_x_l, cy - half_w), (base_x_l, cy + half_w)]
        inner = [(tip_x_l + 2, cy), (base_x_l - 1, cy - half_w + 1), (base_x_l - 1, cy + half_w - 1)]
        handle = pygame.Rect(base_x_l - 1, cy - 1, 3, 3)
        tip_hl = (tip_x_l + 2, cy)
    else:
        # 'inner' 或其他: 默认向上
        points = base_points_up
        inner = inner_up
        handle = handle_up
        tip_hl = (cx, tip_y + 2)

    # 箭头外光晕
    glow = pygame.Surface((20, 20), pygame.SRCALPHA)
    pygame.draw.circle(glow, arrow_glow, (10, 10), 9)
    # 根据箭头位置放置光晕
    glow_x = tip_hl[0] - 10
    glow_y = tip_hl[1] - 10
    surf.blit(glow, (glow_x, glow_y))

    # 箭头主体(暗)
    pygame.draw.polygon(surf, arrow_dark, points)
    # 内部(亮)
    pygame.draw.polygon(surf, arrow_color, inner)
    # 顶点高光
    pygame.draw.circle(surf, arrow_hi, tip_hl, 2)
    # 箭头柄
    pygame.draw.rect(surf, arrow_dark, handle)


def draw_spawn_tile(surf, w, h):
    """猎梦者出生点格子(雪地地图专用)
    视觉: 白色雪地 + 蓝色十字光晕标记, 表示该格可触发回血"""
    # 底层: 白色雪地
    surf.fill((240, 248, 255))
    # 雪纹
    for row in range(0, h, 6):
        if (row // 6) % 2 == 0:
            base = (250, 253, 255)
        else:
            base = (220, 232, 248)
        pygame.draw.rect(surf, base, (0, row, w, 6))
        pygame.draw.line(surf, (200, 220, 240), (0, row + 5), (w, row + 5), 1)
    # 整体淡蓝边
    pygame.draw.rect(surf, (160, 195, 225), (0, 0, w, h), 1)
    # 顶部高光
    pygame.draw.line(surf, (255, 255, 255), (0, 0), (w, 0), 1)

    # 中心蓝色十字(出生点标记, 表示"此处可回血")
    cx, cy = w // 2, h // 2
    # 外光晕
    glow = pygame.Surface((20, 20), pygame.SRCALPHA)
    pygame.draw.circle(glow, (80, 160, 240, 90), (10, 10), 9)
    surf.blit(glow, (cx - 10, cy - 10))
    # 十字本体(蓝)
    arm_len = 5
    arm_w = 2
    pygame.draw.rect(surf, (40, 100, 200), (cx - arm_w // 2, cy - arm_len, arm_w, arm_len * 2))
    pygame.draw.rect(surf, (40, 100, 200), (cx - arm_len, cy - arm_w // 2, arm_len * 2, arm_w))
    # 中心高亮
    pygame.draw.circle(surf, (140, 200, 255), (cx, cy), 2)
    pygame.draw.circle(surf, WHITE, (cx, cy), 1)


# ═══════════════════════════════════════
#  主渲染函数 — viewport → scale 流程
#  屏幕显示 = 视野范围
# ═══════════════════════════════════════

from ui.ui_camera import VIEWPORT_SIZE, VIEW_TILES


def render_game(screen, game_state, camera, font_small, font_medium):
    """渲染整个游戏画面: 先画到viewport, 再scale到屏幕"""
    screen.fill(BLACK)

    # ── 计算scale: viewport填满屏幕游戏区域 ──
    sw, sh = screen.get_width(), screen.get_height()
    game_area_w = sw
    game_area_h = sh - HUD_HEIGHT
    scale = min(game_area_w / VIEWPORT_SIZE, game_area_h / VIEWPORT_SIZE)
    camera.scale = scale
    scaled_w = int(VIEWPORT_SIZE * scale)
    scaled_h = int(VIEWPORT_SIZE * scale)
    game_area_x = (game_area_w - scaled_w) // 2
    game_area_y = HUD_HEIGHT + (game_area_h - scaled_h) // 2

    # ── 复用viewport Surface(避免每帧重新分配内存) ──
    if not hasattr(render_game, '_viewport'):
        render_game._viewport = pygame.Surface((VIEWPORT_SIZE, VIEWPORT_SIZE))
    viewport = render_game._viewport
    viewport.fill((0, 0, 0))

    # ── 获取viewport在地图上的覆盖范围 ──
    left, top, _, _ = camera.viewport_map_rect

    # 地图层
    _render_map(viewport, game_state, left, top)

    # 建筑层
    _render_buildings(viewport, game_state, left, top)

    # 实体层
    _render_entities(viewport, game_state, left, top, font_small)

    # 子弹
    _render_bullets(viewport, game_state, left, top)

    # 舌头
    _render_tongues(viewport, game_state, left, top)

    # 镜子光束
    _render_mirror_beams(viewport, game_state, left, top)

    # 门的血条(最顶层, 不会被任何建筑/人物/特效遮挡)
    _render_door_hp_bars(viewport, game_state, left, top)

    # ── 缩放viewport到屏幕 ──
    scaled = pygame.transform.scale(viewport, (scaled_w, scaled_h))
    screen.blit(scaled, (game_area_x, game_area_y))

    # ── HUD (不缩放, 始终在顶部) ──
    from ui.ui_hud import render_hud
    render_hud(screen, game_state, font_small, font_medium)

    # ── 弹出菜单 ──
    from ui.ui_hud import render_popup_menu
    render_popup_menu(screen, game_state, camera, font_small)

    # ── 特效 ──
    from graphics.effects import render_effects
    render_effects(screen, game_state, camera, font_small, left, top, scale, game_area_x, game_area_y)

    # 存储当前scale/offset用于screen_to_grid
    game_state._scale = scale
    game_state._game_area_x = game_area_x
    game_state._game_area_y = game_area_y


def _render_map(viewport, game_state, left, top):
    """绘制地图到viewport"""
    grid = game_state.grid
    c0 = max(0, int(left // TILE_SIZE))
    r0 = max(0, int(top // TILE_SIZE))
    c1 = min(_cfg.MAP_COLS - 1, int((left + VIEWPORT_SIZE) // TILE_SIZE) + 1)
    r1 = min(_cfg.MAP_ROWS - 1, int((top + VIEWPORT_SIZE) // TILE_SIZE) + 1)

    # 走廊风格
    corridor_style = game_state.map_config.corridor_style if game_state.map_config else 'wood'
    corridor_funcs = {
        'wood': draw_corridor_tile,
        'moss': draw_corridor_moss,
        'snow': draw_corridor_snow,
        'lava': draw_corridor_lava,
    }
    corridor_draw = corridor_funcs.get(corridor_style, draw_corridor_tile)
    corridor_key = f"corridor_{corridor_style}"

    # 红色通道方向查找表 {red_pos: dir} (所有地图通用, 用于绘制红格上的箭头)
    red_dir_map = {}
    if hasattr(game_state, 'door_transitions') and game_state.door_transitions:
        for blue_pos, red_pos, ddir in game_state.door_transitions:
            red_dir_map[red_pos] = ddir

    # 收集所有门箭头位置(人类上床后门要移动到的目标位置)
    # 过滤已关闭的门: 如果门已关闭(滑动到箭头位置), 不显示箭头
    door_arrow_positions = set()
    for room in game_state.rooms:
        if room.door_arrow_col is None or room.door_arrow_row is None:
            continue
        # 检查该房间的门是否已关闭
        door = game_state.get_door_in_room(room.id)
        if door is None:
            continue  # 无门, 跳过
        # 门已关闭时不显示箭头(引导玩家进入)
        if door.is_door_closed:
            continue
        door_arrow_positions.add((room.door_arrow_col, room.door_arrow_row))

    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            sx = c * TILE_SIZE - left
            sy = r * TILE_SIZE - top
            if sx + TILE_SIZE < 0 or sx > VIEWPORT_SIZE or sy + TILE_SIZE < 0 or sy > VIEWPORT_SIZE:
                continue
            tile = grid[r][c]
            if tile == TILE_WALL:
                draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE, draw_wall_tile, cache_key="wall")
            elif tile == TILE_ROOM:
                draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE, draw_floor_tile, cache_key="floor")
            elif tile == TILE_BED:
                draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE, draw_floor_tile, cache_key="floor")
            elif tile == TILE_RED_CHANNEL:
                # 雪地地图红色通道: 红色地板 + 绿色箭头(指向房间)
                ddir = red_dir_map.get((c, r), 'S')
                # 简化 'S_to_11' 等 inner 标记: 箭头朝南(进入房间方向)
                if ddir.startswith('S_to'):
                    ddir = 'N'  # 房间在北, 红格在南, 箭头指南
                draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                                   lambda s, w, h, d=ddir: draw_red_channel_tile(s, w, h, d),
                                   cache_key=("red_channel", ddir))
            elif tile == TILE_SPAWN:
                # 雪地地图猎梦者出生点: 白色走廊 + 蓝色十字
                draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                                   draw_spawn_tile, cache_key="spawn_tile")
            elif tile == TILE_DOOR:
                # 初始门位置(蓝格): 使用走廊样式+绿色双箭头<<
                draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                                   lambda s, w, h, cd=corridor_draw: draw_door_arrow_tile(s, w, h, cd),
                                   cache_key=None)  # 不缓存, 因为走廊样式可能不同
            elif tile == TILE_EMPTY:
                # 检查是否是门箭头位置(门移动目标)
                if (c, r) in door_arrow_positions:
                    # 门箭头位置: 走廊样式+绿色双箭头<<
                    draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                                       lambda s, w, h, cd=corridor_draw: draw_door_arrow_tile(s, w, h, cd),
                                       cache_key=None)
                else:
                    draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE, corridor_draw, cache_key=corridor_key)


def _render_buildings(viewport, game_state, left, top):
    """绘制建筑到viewport
    分两个阶段: 第一阶段画所有非门建筑(以及门自身);
              第二阶段专门画门的血条, 保证血条永远在最顶层
    """
    for b in game_state.buildings:
        sx = b.grid_col * TILE_SIZE - left
        sy = b.grid_row * TILE_SIZE - top
        if sx + TILE_SIZE < 0 or sx > VIEWPORT_SIZE or sy + TILE_SIZE < 0 or sy > VIEWPORT_SIZE:
            continue

        if b.type == BLDG_DOOR:
            if b.current_hp > 0:
                # 检查门是否在动画中(关门:蓝格→红格 / 开门:红格→蓝格)
                anim_pos = None
                anim_data = None
                anim_target = None
                anim_direction = None
                if hasattr(game_state, 'door_animations') and game_state.door_animations:
                    for bp, ad in game_state.door_animations.items():
                        if ad['phase'] >= 1.0:
                            continue
                        direction = ad.get('direction', 'close')
                        if direction == 'close':
                            # 关门动画: 门在蓝格, 滑向红格
                            if bp == (b.grid_col, b.grid_row):
                                anim_pos = bp
                                anim_data = ad
                                anim_target = ad['red']
                                anim_direction = 'close'
                                break
                        elif direction == 'open':
                            # 开门动画: 门在红格, 滑向蓝格
                            if ad.get('blue') and bp == (b.grid_col, b.grid_row):
                                anim_pos = bp
                                anim_data = ad
                                anim_target = ad['blue']
                                anim_direction = 'open'
                                break

                if anim_pos is not None and anim_data is not None:
                    # 门正在滑动: 在当前位置→目标位置的插值位置上绘制
                    ac, ar = anim_pos
                    tc, tr = anim_target
                    phase = anim_data['phase']
                    interp_c = ac + (tc - ac) * phase
                    interp_r = ar + (tr - ar) * phase
                    anim_sx = interp_c * TILE_SIZE - left
                    anim_sy = interp_r * TILE_SIZE - top
                    # 动画中不缓存(每帧位置变化)
                    draw_pixel_texture(viewport, int(anim_sx), int(anim_sy), TILE_SIZE, TILE_SIZE,
                                       lambda s, w, h, lv=b.level, dt=b.door_type:
                                           draw_door(s, w, h, lv, dt),
                                       cache_key=None)
                else:
                    # 画门本身(血条在第二阶段统一画在最上层)
                    draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                                       lambda s, w, h: draw_door(s, w, h, b.level, b.door_type),
                                       cache_key=("door", b.level, b.door_type))
                if b.being_repaired:
                    cx = int(sx) + TILE_SIZE // 2
                    cy = int(sy) + TILE_SIZE // 2
                    pygame.draw.circle(viewport, (180, 180, 200), (cx, cy - 6), 3)
                    pygame.draw.line(viewport, GREEN, (cx, cy - 10), (cx, cy - 2), 2)
                    pygame.draw.line(viewport, GREEN, (cx - 4, cy - 6), (cx + 4, cy - 6), 2)
            else:
                draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE, draw_corridor_tile, cache_key="corridor")
                pygame.draw.rect(viewport, DARK_GRAY, (int(sx), int(sy), TILE_SIZE, TILE_SIZE), 1)

        elif b.type == BLDG_BED:
            # 检测该房间内是否有活人躺在床上
            has_human = any(
                h.alive and h.state == HUMAN_BED and h.room_id == b.room_id
                for h in game_state.humans
            )
            bed_frame = int(game_state.game_time * 2) % 2
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h, lv=b.level, hh=has_human, f=bed_frame:
                                   draw_bed(s, w, h, lv, hh, f),
                               cache_key=("bed", b.level, has_human, bed_frame))
        elif b.type == BLDG_TURRET:
            # 计算炮管朝向: 指向射程内最近猎梦者
            import math as _math
            turret_angle = -_math.pi / 4  # 默认右上
            min_dist = 999
            turret_range_tiles = b.turret_range if hasattr(b, 'turret_range') else 5
            for h in game_state.dream_hunters:
                if not h.alive or h.turret_disabled:
                    continue
                dx = h.px - b.px_center[0]
                dy = h.py - b.px_center[1]
                dist = _math.hypot(dx, dy) / TILE_SIZE
                if dist < min_dist and dist <= turret_range_tiles + 0.5:
                    min_dist = dist
                    # atan2: 屏幕坐标 y 向下, 转换为画布数学坐标
                    turret_angle = _math.atan2(-dy, dx)
            # 检测开火状态: 是否有本炮塔刚发射的子弹(0.1秒内)
            is_firing = any(
                getattr(bul, 'from_turret_uid', None) == b.uid
                and game_state.game_time - getattr(bul, 'spawn_time', -1) < 0.12
                for bul in game_state.bullets
            )
            # 炮停状态: 红裙小女孩炮停技能激活时, 所有炮塔变灰 + 红色X
            turret_disabled_by_hunter = any(
                h.alive and h.turret_disabled
                for h in game_state.dream_hunters
            )
            # 用 angle 量化作为 cache key(8 个方向)
            angle_key = int(((turret_angle + _math.pi) / (2 * _math.pi)) * 8) % 8
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h, lv=b.level, a=turret_angle, f=is_firing:
                                   draw_turret(s, w, h, lv, a, f),
                               cache_key=("turret", b.level, angle_key, is_firing))
            # 炮停时: 在炮塔上叠加灰色滤镜 + 红色 X
            if turret_disabled_by_hunter:
                _draw_turret_disabled_overlay(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE)
        elif b.type == BLDG_REPAIR:
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h: draw_repair_station(s, w, h),
                               cache_key="repair")
        elif b.type == BLDG_GAMEMACHINE:
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h: draw_gamemachine(s, w, h, b.level),
                               cache_key=("gamemachine", b.level))
        elif b.type in MINE_TYPES:
            mine_level = b.type - BLDG_MINE_COPPER
            mine_frame = int(game_state.game_time * 2) % 16
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h, ml=mine_level, f=mine_frame: draw_mine(s, w, h, ml, f),
                               cache_key=("mine", mine_level, mine_frame))
        elif b.type == BLDG_FRIDGE:
            fridge_frame = int(game_state.game_time * 2) % 20
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h, f=fridge_frame: draw_fridge(s, w, h, f),
                               cache_key=("fridge", fridge_frame))
        elif b.type == BLDG_SHIELD:
            hunter = game_state.dream_hunter
            is_active = hunter.shield_active if hunter else False
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h, a=is_active: draw_shield(s, w, h, a),
                               cache_key=("shield", is_active))
        elif b.type == BLDG_TRAP:
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h: draw_trap(s, w, h),
                               cache_key="trap")
        elif b.type == BLDG_GUILLOTINE:
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h: draw_guillotine(s, w, h),
                               cache_key="guillotine")
        elif b.type == BLDG_GRASS_S:
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h: draw_grass(s, w, h, False),
                               cache_key="grass_s")
        elif b.type == BLDG_GRASS_L:
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h: draw_grass(s, w, h, True),
                               cache_key="grass_l")
        elif b.type == BLDG_MIRROR:
            # 检查是否有猎梦者接近(8格内)
            bpx, bpy = b.px_center
            near = False
            for h in game_state.dream_hunters:
                if not h.alive:
                    continue
                dist = math.hypot(h.px - bpx, h.py - bpy) / TILE_SIZE
                if dist <= MIRROR_NEAR_DIST:
                    near = True
                    break
            is_burning = getattr(b, 'mirror_burn_active', False)
            mirror_frame = int(game_state.game_time * 2) % 12
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h, n=near, f=mirror_frame, b=is_burning:
                                   draw_mirror(s, w, h, n, f, b),
                               cache_key=("mirror", near, mirror_frame, is_burning))
        elif b.type == BLDG_GARLIC:
            # 大蒜激活状态: 门血 < 30% 且在冷却外
            door = next((bd for bd in game_state.buildings
                        if bd.type == BLDG_DOOR and bd.room_id == b.room_id), None)
            is_active = False
            if door and door.max_hp > 0:
                hp_ratio = door.current_hp / door.max_hp
                is_active = hp_ratio < GARLIC_THRESHOLD and b.cooldown_timer <= 0
            garlic_frame = int(game_state.game_time * 3) % 18
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h, a=is_active, f=garlic_frame:
                                   draw_garlic(s, w, h, a, f),
                               cache_key=("garlic", is_active, garlic_frame))
        elif b.type == BLDG_FROG:
            anim_frame = int((game_state.game_time * 3) % 2)
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h, f=anim_frame: draw_frog(s, w, h, f),
                               cache_key=("frog", anim_frame))
        elif b.type == BLDG_BEAR_BED:
            # 队友死亡数
            dead_count = sum(1 for h in game_state.humans if not h.alive)
            bear_frame = int(game_state.game_time * 2) % 8
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h, lv=b.level, dc=dead_count, f=bear_frame:
                                   draw_bear_bed(s, w, h, lv, dc, f),
                               cache_key=("bear_bed", b.level, dead_count, bear_frame))
        elif b.type == BLDG_SWORD:
            anim_frame = int((game_state.game_time * 2) % 4)
            # 检查该刀是否正在动画中(飞向/砍击/飞回)
            active_anim = None
            for _sa in game_state.sword_animations:
                if _sa['sword_id'] == id(b):
                    active_anim = _sa
                    break
            if active_anim and active_anim.get('sword_pixel') is not None:
                # 动画中: 在当前帧的像素位置绘制旋转的刀
                # sword_pixel 是地图绝对坐标, 要转成 viewport 坐标
                _sx_pos = active_anim['sword_pixel'][0] - left - TILE_SIZE // 2
                _sy_pos = active_anim['sword_pixel'][1] - top - TILE_SIZE // 2
                # 砍击瞬间额外绘制闪光(白色圆圈)
                if active_anim['phase'] == 'slash':
                    _slash_cx = int(active_anim['sword_pixel'][0] - left)
                    _slash_cy = int(active_anim['sword_pixel'][1] - top)
                    _slash_r = int(TILE_SIZE * (0.6 + 0.4 * (1.0 - abs(active_anim['slash_angle']) / 90.0)))
                    _slash_surf = pygame.Surface((_slash_r * 2, _slash_r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(_slash_surf, (255, 240, 150, 80), (_slash_r, _slash_r), _slash_r)
                    pygame.draw.circle(_slash_surf, (255, 255, 220, 50), (_slash_r, _slash_r), _slash_r * 2 // 3)
                    viewport.blit(_slash_surf, (_slash_cx - _slash_r, _slash_cy - _slash_r))
                draw_pixel_texture(viewport, int(_sx_pos), int(_sy_pos), TILE_SIZE, TILE_SIZE,
                                   lambda s, w, h, a=active_anim['slash_angle'], f=anim_frame:
                                       draw_sword_animated(s, w, h, a, f),
                                   cache_key=None)  # 动画中不缓存(避免闪烁)
            else:
                # 静止状态: 原有的绘制逻辑
                is_casting = b.cooldown_timer > SWORD_COOLDOWN - 0.3
                draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                                   lambda s, w, h, f=anim_frame, c=is_casting: draw_sword(s, w, h, f, c),
                                   cache_key=("sword", anim_frame, is_casting))


def _render_door_hp_bars(viewport, game_state, left, top):
    """第二阶段: 在所有实体(人物/猎梦者)之后绘制门的血条
    保证门的血条永远在最顶层, 不会被任何建筑/人物/特效遮挡
    """
    for b in game_state.buildings:
        if b.type != BLDG_DOOR or b.current_hp <= 0:
            continue
        sx = b.grid_col * TILE_SIZE - left
        sy = b.grid_row * TILE_SIZE - top
        if sx + TILE_SIZE < 0 or sx > VIEWPORT_SIZE or sy + TILE_SIZE < 0 or sy > VIEWPORT_SIZE:
            continue
        hp_ratio = b.current_hp / b.max_hp if b.max_hp > 0 else 0
        bar_w = TILE_SIZE - 4
        bar_h = 4
        bar_x = int(sx) + 2
        bar_y = max(2, int(sy) - 7)
        # 描边黑底
        pygame.draw.rect(viewport, BLACK, (bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2))
        # 红色底
        pygame.draw.rect(viewport, RED, (bar_x, bar_y, bar_w, bar_h))
        # 绿色血量
        pygame.draw.rect(viewport, GREEN, (bar_x, bar_y, int(bar_w * hp_ratio), bar_h))


def _draw_zzz(viewport, sx, sy, game_time):
    """在睡觉的人类上方绘制浮动Zzz动画(像素风格)"""
    # 3个Z依次向上飘, 大小递减, 透明度递减
    # 周期约2秒, 每个Z错开0.6秒
    for i in range(3):
        phase = (game_time * 1.5 + i * 0.6) % 2.0  # 0~2秒循环
        if phase > 1.5:
            continue  # 消失阶段
        # 位置: 从精灵顶部向上飘
        zx = sx + 18 + i * 3
        zy = sy - 4 - int(phase * 12) - i * 4
        # 大小: 3x3, 2x2, 2x2
        size = 3 - i if i < 2 else 2
        # 透明度随phase递减
        alpha = max(0, int(255 * (1.0 - phase / 1.5)))
        color = (200, 200, 255, alpha)
        # 绘制像素Z: 横线-斜线-横线
        z_surf = pygame.Surface((size * 2 + 1, size * 2 + 1), pygame.SRCALPHA)
        # 上横线
        pygame.draw.line(z_surf, color, (0, 0), (size * 2, 0), 1)
        # 斜线
        pygame.draw.line(z_surf, color, (size * 2, 0), (0, size * 2), 1)
        # 下横线
        pygame.draw.line(z_surf, color, (0, size * 2), (size * 2, size * 2), 1)
        viewport.blit(z_surf, (zx, zy))


def _render_entities(viewport, game_state, left, top, font_small):
    """绘制人类和猎梦者到viewport(支持多猎梦者)"""
    game_time = game_state.game_time
    # 呼吸动画帧(0/1 切换, 0.5s 一帧)
    breath_frame = int(game_time * 2) % 2

    # ── 渲染所有人类(活着的画精灵, 死亡的画墓碑) ──
    for human in game_state.humans:
        sx = human.px - TILE_SIZE // 2 - left
        sy = human.py - TILE_SIZE // 2 - top
        if sx + TILE_SIZE < 0 or sx > VIEWPORT_SIZE or sy + TILE_SIZE < 0 or sy > VIEWPORT_SIZE:
            continue

        is_bed = (human.state == HUMAN_BED)
        is_dead = (human.state == HUMAN_DEAD)

        if is_dead:
            # 死亡: 画墓碑(不画完整人, 但保留位置感)
            draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                               lambda s, w, h, c=human.color: draw_human_sprite(s, w, h, c, False, True),
                               cache_key=("human_dead", human.color))
            # 头顶墓碑粒子
            draw_tombstone_marker(viewport, int(sx) + TILE_SIZE // 2, int(sy) + TILE_SIZE // 2, game_time)
            if human.is_player:
                pygame.draw.rect(viewport, YELLOW, (int(sx), int(sy), TILE_SIZE, TILE_SIZE), 2)
            continue

        # 活着的: 画人形
        draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                           lambda s, w, h, c=human.color, b=is_bed, f=breath_frame:
                               draw_human_sprite(s, w, h, c, b, False, f),
                           cache_key=("human", human.color, is_bed, breath_frame))
        if is_bed:
            _draw_zzz(viewport, int(sx), int(sy), game_time)
        if human.is_player:
            pygame.draw.rect(viewport, YELLOW, (int(sx), int(sy), TILE_SIZE, TILE_SIZE), 2)

    # 渲染所有猎梦者
    for hunter in game_state.dream_hunters:
        if not hunter.alive:
            continue
        sx = hunter.px - TILE_SIZE // 2 - left
        sy = hunter.py - TILE_SIZE // 2 - top
        if sx + TILE_SIZE < 0 or sx > VIEWPORT_SIZE or sy + TILE_SIZE < 0 or sy > VIEWPORT_SIZE:
            continue
        # 帧动画: 0-15 循环(便于摆动/咀嚼/呼吸等)
        anim_frame = int(game_time * 4) % 16
        # 额外状态
        extra_state = {}
        # 绷带: 回血绿色脉冲 + 残血绷带松散
        if hunter.hunter_type == HUNTER_BANDAGE:
            if hunter.bandage_healing:
                extra_state['healing'] = True
            # 残血时绷带松散(< 50% 开始松散)
            hp_ratio_now = hunter.current_hp / hunter.max_hp if hunter.max_hp > 0 else 1.0
            extra_state['low_hp_ratio'] = 1.0 - hp_ratio_now
        # 红裙小女孩: 炮停时旋转触发
        if hunter.hunter_type == HUNTER_REDDRESS and hunter.turret_disabled:
            extra_state['spin_trigger'] = True
        # 不缓存(需逐帧动画: 摆动/咀嚼/火焰/治疗脉冲/旋转)
        draw_pixel_texture(viewport, int(sx), int(sy), TILE_SIZE, TILE_SIZE,
                           lambda s, w, h: draw_hunter_sprite(s, w, h, hunter.level,
                               hunter.hunter_type, hunter.berserk_active, 255,
                               anim_frame, extra_state),
                           cache_key=None)

        # 猎梦者头顶血量条 + 等级名字标签(类似门血条样式)
        hp_ratio = hunter.current_hp / hunter.max_hp if hunter.max_hp > 0 else 0
        hunter_name = HUNTER_TYPE_NAMES.get(hunter.hunter_type, '猎梦者')
        hunter_level = hunter.level + 1
        label_text = f"LV{hunter_level} {hunter_name}"

        # 用 pygame 字体渲染文字获取宽度
        label_surf = font_small.render(label_text, True, WHITE)
        label_w = label_surf.get_width()
        label_h = label_surf.get_height()

        bar_w = max(label_w, TILE_SIZE)
        bar_h = 4
        bar_x = int(sx) + (TILE_SIZE - bar_w) // 2
        bar_y = int(sy) - bar_h - label_h - 4

        # 名字文字
        viewport.blit(label_surf, (bar_x + (bar_w - label_w) // 2, bar_y))

        # 血条背景(黑框)
        pygame.draw.rect(viewport, BLACK, (bar_x - 1, bar_y + label_h + 1, bar_w + 2, bar_h + 2))
        # 血条底色(红)
        pygame.draw.rect(viewport, RED, (bar_x, bar_y + label_h + 2, bar_w, bar_h))
        # 血条血量(狂暴橙色, 正常紫色)
        bar_color = ORANGE if hunter.berserk_active else PURPLE
        pygame.draw.rect(viewport, bar_color, (bar_x, bar_y + label_h + 2, int(bar_w * hp_ratio), bar_h))

        # 渲染分身(孙婆婆)
        for clone in hunter.clones:
            if not clone.alive:
                continue
            csx = clone.px - TILE_SIZE // 2 - left
            csy = clone.py - TILE_SIZE // 2 - top
            if csx + TILE_SIZE < 0 or csx > VIEWPORT_SIZE or csy + TILE_SIZE < 0 or csy > VIEWPORT_SIZE:
                continue
            # 分身: 半透明缩小版(支持合体的闪光效果)
            clone_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            # 合体阶段(lifetime<1s): 显示闪光
            merge_flash = getattr(clone, 'lifetime', 0) < 1.0
            extra_clone = {'merge_flash': merge_flash} if merge_flash else None
            draw_hunter_sprite(clone_surf, TILE_SIZE, TILE_SIZE, hunter.level,
                             hunter.hunter_type, False, 160, anim_frame, extra_clone)
            clone_surf.set_alpha(160)
            viewport.blit(clone_surf, (int(csx), int(csy)))
            # 分身血条
            hp_ratio = clone.current_hp / clone.max_hp if clone.max_hp > 0 else 0
            bar_w = TILE_SIZE - 8
            bar_h = 3
            bar_x = int(csx) + 4
            bar_y = int(csy) - 6
            pygame.draw.rect(viewport, BLACK, (bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2))
            pygame.draw.rect(viewport, RED, (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(viewport, (180, 120, 220), (bar_x, bar_y, int(bar_w * hp_ratio), bar_h))


def _render_bullets(viewport, game_state, left, top):
    """绘制子弹到viewport"""
    for bullet in game_state.bullets:
        sx = int(bullet.px - left)
        sy = int(bullet.py - top)
        if 0 <= sx <= VIEWPORT_SIZE and 0 <= sy <= VIEWPORT_SIZE:
            pygame.draw.circle(viewport, ORANGE, (sx, sy), 4)
            pygame.draw.circle(viewport, YELLOW, (sx, sy), 2)


def _render_tongues(viewport, game_state, left, top):
    """绘制蛤蟆舌头到viewport - 较粗的粉色舌头，从蛤蟆延伸到猎梦者"""
    for tongue in game_state.tongues:
        sx = int(tongue.px - left)
        sy = int(tongue.py - top)
        # 舌头起点(蛤蟆位置)
        start_sx = int(tongue.start_px - left)
        start_sy = int(tongue.start_py - top)
        if 0 <= sx <= VIEWPORT_SIZE and 0 <= sy <= VIEWPORT_SIZE:
            # 画较粗的舌头线(粉色)
            pygame.draw.line(viewport, (240, 100, 120), (start_sx, start_sy), (sx, sy), 4)
            # 舌尖亮点
            pygame.draw.circle(viewport, (255, 180, 200), (sx, sy), 3)
            pygame.draw.circle(viewport, (255, 220, 230), (sx - 1, sy - 1), 1)


def _render_mirror_beams(viewport, game_state, left, top):
    """绘制镜子光束 - 蓝色光线连接镜子和猎梦者，灼热状态时为红色"""
    for b in game_state.buildings:
        if b.type != BLDG_MIRROR:
            continue
        hunter = b.mirror_target_hunter
        if hunter is None or not hunter.alive:
            continue

        # 镜子中心
        mx, my = b.px_center
        sx_m = int(mx - left)
        sy_m = int(my - top)
        # 猎梦者中心
        hx = hunter.px
        hy = hunter.py
        sx_h = int(hx - left)
        sy_h = int(hy - top)

        # 检查是否在视口内
        if not (0 <= sx_m <= VIEWPORT_SIZE and 0 <= sy_m <= VIEWPORT_SIZE):
            continue

        # 光束颜色: 灼热状态为红色，否则为蓝色
        if b.mirror_burn_active:
            beam_color = (255, 60, 60)
            beam_glow = (255, 150, 150)
        else:
            beam_color = (60, 140, 255)
            beam_glow = (150, 200, 255)

        # 画较粗的光线
        pygame.draw.line(viewport, beam_color, (sx_m, sy_m), (sx_h, sy_h), 3)
        # 外层光晕
        pygame.draw.line(viewport, beam_glow, (sx_m, sy_m), (sx_h, sy_h), 6)
        pygame.draw.line(viewport, beam_color, (sx_m, sy_m), (sx_h, sy_h), 3)

        # 镜子端发光点
        pygame.draw.circle(viewport, beam_glow, (sx_m, sy_m), 5)
        pygame.draw.circle(viewport, beam_color, (sx_m, sy_m), 3)

        # 猎梦者端发光点
        if 0 <= sx_h <= VIEWPORT_SIZE and 0 <= sy_h <= VIEWPORT_SIZE:
            pygame.draw.circle(viewport, beam_glow, (sx_h, sy_h), 5)
            pygame.draw.circle(viewport, beam_color, (sx_h, sy_h), 3)
