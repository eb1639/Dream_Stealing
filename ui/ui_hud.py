"""
顶部状态栏 + 弹出建造/升级菜单
"""
import pygame
import math
from core.config import *
from entities.entities import *
from world.map_data import *


# ─── 建筑菜单元数据: (名称, 描述, 绘制函数名) ───
# 描述用于菜单内道具说明; 绘制函数从 graphics.renderer 调用
BLDG_MENU_INFO = {
    BLDG_TURRET:           ("炮塔",       "自动攻击猎梦者, 升级提伤加射程",          "draw_turret"),
    BLDG_REPAIR:           ("维修台",     "持续修复门血, 升级加快速度",              "draw_repair_station"),
    BLDG_GAMEMACHINE:      ("游戏机",     "产生电力",                                "draw_gamemachine"),
    BLDG_MINE_COPPER:      ("铜矿",       "产金币(可升级为银/金/钻石矿)",            "draw_mine"),
    BLDG_MINE_SILVER:      ("银矿",       "产金币(原铜矿升级版)",                    "draw_mine"),
    BLDG_MINE_GOLD:        ("金矿",       "产金币(原铜矿升级版)",                    "draw_mine"),
    BLDG_MINE_DIAMOND:     ("钻石矿",     "产金币(原铜矿升级版, 已顶级)",            "draw_mine"),
    BLDG_FRIDGE:           ("冰箱",       "减缓猎梦者攻速",                          "draw_fridge"),
    BLDG_SHIELD:           ("能量罩",     "门血低于30%时3秒无敌",                   "draw_shield"),
    BLDG_TRAP:             ("诱捕网",     "猎梦者逃跑时定身",                        "draw_trap"),
    BLDG_GUILLOTINE:       ("断头台",     "猎梦者血低时直接斩血",                   "draw_guillotine"),
    BLDG_GRASS_S:          ("一根小草",   "门被攻击时给金币",                        "draw_grass"),
    BLDG_GRASS_L:          ("一盆小草",   "门被攻击时给金币, 攻击叠加",              "draw_grass_big"),
    BLDG_MIRROR:           ("镜子",       "近距双倍/远距少量金币持续产出",           "draw_mirror"),
    BLDG_GARLIC:           ("大蒜",       "门血低时熏走猎梦者",                      "draw_garlic"),
    BLDG_FROG:             ("蛤蟆",       "远距舌攻",                                "draw_frog"),
    BLDG_BEAR_BED:         ("小熊睡床",   "产金币, 队友死时翻倍",                   "draw_bear_bed"),
    BLDG_SWORD:            ("屠龙刀",     "按F键一刀斩猎梦者20%血",                 "draw_sword"),
}


def _get_building_draw_func(btype, frame=0):
    """根据 btype 返回对应的 (draw_func, level) 绘制参数。复用 renderer 中的精灵函数。"""
    from graphics.renderer import (
        draw_turret, draw_repair_station, draw_gamemachine, draw_mine,
        draw_fridge, draw_shield, draw_trap, draw_guillotine,
        draw_grass, draw_mirror, draw_garlic, draw_frog,
        draw_bear_bed, draw_sword,
    )
    if btype == BLDG_TURRET:
        return lambda s, w, h: draw_turret(s, w, h, 0)
    if btype == BLDG_REPAIR:
        return draw_repair_station
    if btype == BLDG_GAMEMACHINE:
        return lambda s, w, h: draw_gamemachine(s, w, h, 0)
    if btype in MINE_TYPES:
        level = btype - BLDG_MINE_COPPER
        return lambda s, w, h, lv=level: draw_mine(s, w, h, lv)
    if btype == BLDG_FRIDGE:
        return draw_fridge
    if btype == BLDG_SHIELD:
        return draw_shield
    if btype == BLDG_TRAP:
        return draw_trap
    if btype == BLDG_GUILLOTINE:
        return draw_guillotine
    if btype == BLDG_GRASS_S:
        return lambda s, w, h: draw_grass(s, w, h, False)
    if btype == BLDG_GRASS_L:
        return lambda s, w, h: draw_grass(s, w, h, True)
    if btype == BLDG_MIRROR:
        return draw_mirror
    if btype == BLDG_GARLIC:
        return draw_garlic
    if btype == BLDG_FROG:
        return lambda s, w, h: draw_frog(s, w, h, frame)
    if btype == BLDG_BEAR_BED:
        return lambda s, w, h: draw_bear_bed(s, w, h, 0)
    if btype == BLDG_SWORD:
        return lambda s, w, h: draw_sword(s, w, h, frame)
    return None


# ─── HUD渲染 ───

def _draw_coin_icon(screen, x, y, size, color=GOLD):
    """绘制像素风金币图标(置于 HUD 顶部状态栏)"""
    cx = x + size // 2
    cy = y + size // 2
    r = size // 2 - 1
    # 主体圆
    pygame.draw.circle(screen, color, (cx, cy), r)
    pygame.draw.circle(screen, (180, 130, 0), (cx, cy), r, 1)
    # 内部方孔(用底色遮罩)
    inner = max(2, r - 4)
    pygame.draw.rect(screen, (30, 30, 40), (cx - inner // 2, cy - inner // 2, inner, inner))
    pygame.draw.rect(screen, (180, 130, 0), (cx - inner // 2, cy - inner // 2, inner, inner), 1)
    # 高光
    pygame.draw.circle(screen, (255, 240, 120), (cx - r // 3, cy - r // 3), max(1, r // 4))


def _draw_lightning_icon(screen, x, y, size, color=YELLOW):
    """绘制像素风闪电图标(置于 HUD 顶部状态栏)"""
    # 顶点 → 右凸 → 斜下 → 左凸 → 底点 → 斜上
    cx = x + size // 2
    top = y + 1
    bottom = y + size - 1
    mid = y + size // 2
    pts = [
        (cx - 1, top),
        (cx + 2, mid - 1),
        (cx, mid - 1),
        (cx + 2, bottom),
        (cx - 3, mid + 1),
        (cx - 1, mid + 1),
    ]
    pygame.draw.polygon(screen, color, pts)
    pygame.draw.polygon(screen, (200, 160, 0), pts, 1)
    # 描边/阴影
    pygame.draw.line(screen, (220, 220, 255), (cx - 1, top), (cx + 2, mid - 1), 1)

def render_hud(screen, game_state, font_small, font_medium):
    """绘制顶部状态栏"""
    sw = screen.get_width()
    # 背景
    hud_rect = pygame.Rect(0, 0, sw, HUD_HEIGHT)
    pygame.draw.rect(screen, (30, 30, 40), hud_rect)
    pygame.draw.line(screen, GRAY, (0, HUD_HEIGHT), (sw, HUD_HEIGHT), 2)

    # 左上角暂停按钮
    pause_btn_size = 28
    pause_btn_margin = 8
    pause_btn_rect = pygame.Rect(pause_btn_margin, (HUD_HEIGHT - pause_btn_size) // 2,
                                  pause_btn_size, pause_btn_size)
    mx, my = pygame.mouse.get_pos()
    hover = pause_btn_rect.collidepoint(mx, my)
    btn_bg = (60, 60, 75) if hover else (45, 45, 55)
    pygame.draw.rect(screen, btn_bg, pause_btn_rect)
    pygame.draw.rect(screen, GRAY, pause_btn_rect, 1)
    # 暂停图标: 两条竖线
    bar_w = 4
    bar_h = 14
    bar_gap = 6
    cx = pause_btn_rect.centerx
    cy = pause_btn_rect.centery
    pygame.draw.rect(screen, WHITE, (cx - bar_gap - bar_w, cy - bar_h // 2, bar_w, bar_h))
    pygame.draw.rect(screen, WHITE, (cx + bar_gap, cy - bar_h // 2, bar_w, bar_h))
    game_state._pause_btn_rect = pause_btn_rect

    # 左侧: 金币(暂停按钮右侧)
    gold_x = pause_btn_margin + pause_btn_size + 10
    if game_state.mode == MODE_HUMAN and game_state.player_human:
        # 金币图标 + 整数数值(无文字)
        _draw_coin_icon(screen, gold_x, 10, 18, GOLD)
        gold_surf = font_medium.render(f" {int(game_state.player_human.gold)}", True, YELLOW)
        screen.blit(gold_surf, (gold_x + 22, 8))
        gold_surf = gold_surf  # 复用以计算后续位置
    elif game_state.mode == MODE_HUNTER and game_state.dream_hunter:
        type_name = HUNTER_TYPE_NAMES.get(game_state.dream_hunter.hunter_type, '')
        gold_text = f"{type_name} 伤害: {game_state.dream_hunter.cumulative_damage} 等级{game_state.dream_hunter.level + 1}"
        gold_surf = font_medium.render(gold_text, True, YELLOW)
        screen.blit(gold_surf, (gold_x, 8))
    else:
        _draw_coin_icon(screen, gold_x, 10, 18, GOLD)
        gold_surf = font_medium.render(" 0", True, YELLOW)
        screen.blit(gold_surf, (gold_x + 22, 8))

    # 电力(游戏机产出, 房间级独立电表): 仅人类模式显示
    if game_state.mode == MODE_HUMAN and game_state.player_human and game_state.player_human.room_id is not None:
        room_id = game_state.player_human.room_id
        power = game_state.room_power.get(room_id, 0.0)
        # 闪电图标(像素风) - 修正: 加上 22px 图标+间距偏移, 避免与金币数值重叠
        _lightning_x = gold_x + 22 + gold_surf.get_width() + 14
        _draw_lightning_icon(screen, _lightning_x, 12, 18, YELLOW)
        power_text = font_medium.render(f" {int(power)}", True, YELLOW)
        screen.blit(power_text, (_lightning_x + 22, 8))

    # 中间: 计时器 + 难度等级
    # 难度等级显示(人类模式)
    if game_state.mode == MODE_HUMAN:
        diff_name = DIFF_NAMES.get(game_state.difficulty, '')
        diff_color = DIFF_COLORS.get(game_state.difficulty, WHITE)
        if game_state.is_endless:
            diff_text = f"无尽 波数{game_state.endless_wave}"
            diff_color = DIFF_COLORS.get(DIFF_ENDLESS, WHITE)
        else:
            diff_text = diff_name
        diff_surf = font_medium.render(diff_text, True, diff_color)
        screen.blit(diff_surf, (sw // 2 - diff_surf.get_width() // 2, 2))

    if game_state.phase == PHASE_SAFE:
        time_text = f"安全: {int(game_state.safe_timer)}秒"
        time_color = GREEN
    else:
        time_text = f"时间: {int(game_state.game_time)}秒"
        time_color = WHITE
    time_surf = font_medium.render(time_text, True, time_color)
    screen.blit(time_surf, (sw // 2 - time_surf.get_width() // 2, 18))

    # 猎梦者HP: 移除HUD重叠血条文本, 改为在viewport中猎梦者头顶显示(类似门血条)

    # 右侧: 人类头像(同排, 右对齐)
    avatar_start_x = sw - 20
    ava_y = 4
    ava_w, ava_h = 40, 40
    ava_gap = 6
    game_state.avatar_rects = {}

    for human in game_state.humans:
        ax = avatar_start_x - (human.id + 1) * (ava_w + ava_gap)
        avatar_rect = pygame.Rect(ax, ava_y, ava_w, ava_h)
        if human.is_player:
            color = PLAYER_COLOR
        elif human.alive:
            color = human.color
        else:
            color = DARK_GRAY

        border_color = RED if (human.alive and human.is_under_attack) else GRAY
        if not human.alive:
            border_color = DARK_GRAY
        pygame.draw.rect(screen, border_color, avatar_rect, 2)
        pygame.draw.rect(screen, color, (ax + 3, ava_y + 3, 34, 34))

        if not human.alive:
            pygame.draw.line(screen, RED, (ax, ava_y), (ax + ava_w, ava_y + ava_h), 2)
            pygame.draw.line(screen, RED, (ax + ava_w, ava_y), (ax, ava_y + ava_h), 2)
        elif human.state == HUMAN_BED:
            label = font_small.render("睡", True, WHITE)
            screen.blit(label, (ax + 6, ava_y + 22))
        else:
            label = font_small.render("跑", True, WHITE)
            screen.blit(label, (ax + 6, ava_y + 22))

        game_state.avatar_rects[human.id] = avatar_rect

    # 猎梦者头像(紧挨人类头像左侧, 支持多猎梦者)
    total_human_w = 6 * (ava_w + ava_gap)
    hunter_count = len(game_state.dream_hunters)
    hunter_total_w = hunter_count * (ava_w + ava_gap)
    hunter_ax_start = avatar_start_x - total_human_w - hunter_total_w - ava_gap
    game_state.hunter_avatar_rects = {}  # 修复: 改为字典存储所有猎梦者头像rect
    for i, hunter in enumerate(game_state.dream_hunters):
        hunter_ax = hunter_ax_start + i * (ava_w + ava_gap)
        hunter_avatar_rect = pygame.Rect(hunter_ax, ava_y, ava_w, ava_h)
        # 种类对应颜色
        type_colors = {
            HUNTER_SUNNY: (200, 170, 30),
            HUNTER_BIGHEAD: (150, 40, 40),
            HUNTER_GRANDMA: (120, 70, 140),
            HUNTER_BANDAGE: (180, 170, 150),
            HUNTER_REDDRESS: (180, 20, 50),
        }
        border_color = type_colors.get(hunter.hunter_type, PURPLE)
        if not hunter.alive:
            border_color = DARK_GRAY
        pygame.draw.rect(screen, border_color, hunter_avatar_rect, 2)
        inner_colors = {
            HUNTER_SUNNY: (120, 100, 20),
            HUNTER_BIGHEAD: (80, 20, 20),
            HUNTER_GRANDMA: (60, 30, 70),
            HUNTER_BANDAGE: (100, 95, 85),
            HUNTER_REDDRESS: (90, 10, 25),
        }
        inner_color = inner_colors.get(hunter.hunter_type, DARK_PURPLE)
        if not hunter.alive:
            inner_color = DARK_GRAY
        pygame.draw.rect(screen, inner_color, (hunter_ax + 3, ava_y + 3, 34, 34))
        hl = font_small.render("猎", True, WHITE if hunter.alive else DARK_GRAY)
        screen.blit(hl, (hunter_ax + 5, ava_y + 22))
        if not hunter.alive:
            pygame.draw.line(screen, RED, (hunter_ax, ava_y), (hunter_ax + ava_w, ava_y + ava_h), 2)
            pygame.draw.line(screen, RED, (hunter_ax + ava_w, ava_y), (hunter_ax, ava_y + ava_h), 2)
        # 存储每个猎梦者的头像rect(使用hunter.id作为key)
        game_state.hunter_avatar_rects[hunter.id] = hunter_avatar_rect
    # 兼容旧代码: 保留hunter_avatar_rect指向第一个
    game_state.hunter_avatar_rect = (
        game_state.hunter_avatar_rects[game_state.dream_hunters[0].id]
        if game_state.dream_hunters else None
    )


# ─── 弹出菜单 ───

def render_popup_menu(screen, game_state, camera, font):
    """绘制弹出菜单: 每项一个矩形方框, 左侧图标 + 右侧名称/说明; 支持上下滚动; 高度自适应内容"""
    if not hasattr(game_state, 'popup_menu') or game_state.popup_menu is None:
        return

    menu = game_state.popup_menu
    px = menu['screen_x']
    py = menu['screen_y']

    sw, sh = screen.get_width(), screen.get_height()

    # ─── 布局常量 ───
    PANEL_W = 460
    ITEM_H = 56
    ITEM_GAP = 5
    HEADER_H = 32
    PANEL_PAD = 6
    SCROLLBAR_W = 8   # 滚动条宽度
    MAX_VISIBLE = 5   # 最多同时显示 5 项

    options = menu['options']
    total = len(options)
    need_scroll = total > MAX_VISIBLE
    visible_count = min(total, MAX_VISIBLE)
    inner_w = PANEL_W - PANEL_PAD * 2 - (SCROLLBAR_W + 4 if need_scroll else 0)

    # 自适应高度: 仅根据可见项数
    list_h = visible_count * (ITEM_H + ITEM_GAP) - ITEM_GAP
    panel_h = HEADER_H + PANEL_PAD + list_h + PANEL_PAD + 2

    # ─── 边界保护 ───
    if px + PANEL_W > sw:
        px = sw - PANEL_W - 5
    if py + panel_h > sh:
        py = sh - panel_h - 5
    if px < 5:
        px = 5
    if py < HUD_HEIGHT + 5:
        py = HUD_HEIGHT + 5

    # ─── 滚动偏移: 限制在合法范围 ───
    if 'scroll' not in menu:
        menu['scroll'] = 0
    max_scroll = max(0, total - MAX_VISIBLE)
    menu['scroll'] = max(0, min(menu['scroll'], max_scroll))
    scroll = menu['scroll']

    # ─── 背景面板 ───
    panel_rect = pygame.Rect(px, py, PANEL_W, panel_h)
    shadow = pygame.Surface((PANEL_W + 6, panel_h + 6), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 120), (0, 0, PANEL_W + 6, panel_h + 6))
    screen.blit(shadow, (px - 3, py - 3))
    pygame.draw.rect(screen, (35, 35, 50), panel_rect)
    pygame.draw.rect(screen, GRAY, panel_rect, 2)

    # ─── 标题 ───
    title_text = menu.get('title', '建造菜单')
    title_surf = font.render(title_text, True, YELLOW)
    screen.blit(title_surf, (px + 10, py + 6))

    # 资源状态(右上角): 金币 + 电力
    human = game_state.player_human
    if human is not None:
        # 金币
        cx_coin = px + PANEL_W - 200
        _draw_coin_icon(screen, cx_coin, py + 8, 16, GOLD)
        coin_surf = font.render(f" {int(human.gold)}", True, YELLOW)
        screen.blit(coin_surf, (cx_coin + 20, py + 6))
        # 电力
        if human.room_id is not None:
            power = game_state.room_power.get(human.room_id, 0.0)
            cx_pow = px + PANEL_W - 90
            _draw_lightning_icon(screen, cx_pow, py + 8, 16, YELLOW)
            pow_surf = font.render(f" {int(power)}", True, YELLOW)
            screen.blit(pow_surf, (cx_pow + 20, py + 6))

    # ─── 选项(滚动) ───
    item_x = px + PANEL_PAD
    item_y0 = py + HEADER_H + PANEL_PAD - 2
    mouse_x, mouse_y = pygame.mouse.get_pos()
    item_rects = []

    # 用于裁剪选项区域(避免越界)
    list_clip_rect = pygame.Rect(px + 2, py + HEADER_H + 2,
                                 PANEL_W - 4, panel_h - HEADER_H - 4)
    prev_clip = screen.get_clip()
    screen.set_clip(list_clip_rect)

    for vi in range(visible_count):
        idx = scroll + vi
        opt = options[idx]
        ix = item_x
        iy = item_y0 + vi * (ITEM_H + ITEM_GAP)
        item_rect = pygame.Rect(ix, iy, inner_w, ITEM_H)
        item_rects.append((item_rect, idx))

        hover = item_rect.collidepoint(mouse_x, mouse_y)
        bg = (60, 60, 75) if hover else (50, 50, 60)
        pygame.draw.rect(screen, bg, item_rect)
        pygame.draw.rect(screen, (90, 90, 110) if hover else GRAY, item_rect, 1)

        # 左侧: 道具图案(40x40 居中, 描边)
        ICON_BOX = 40
        icon_pad = (ITEM_H - ICON_BOX) // 2
        icon_rect_bg = pygame.Rect(ix + 6, iy + icon_pad, ICON_BOX, ICON_BOX)
        pygame.draw.rect(screen, (25, 25, 35), icon_rect_bg)
        pygame.draw.rect(screen, (110, 110, 130), icon_rect_bg, 1)
        draw_func = opt.get('draw_func')
        if draw_func is not None:
            icon_surf = pygame.Surface((ICON_BOX, ICON_BOX))
            draw_func(icon_surf, ICON_BOX, ICON_BOX)
            icon_clip = screen.get_clip()
            screen.set_clip(icon_rect_bg)
            screen.blit(icon_surf, (icon_rect_bg.x, icon_rect_bg.y))
            screen.set_clip(icon_clip)

        # 右侧: 名称(大) + 描述(小)
        text_x = icon_rect_bg.right + 10
        name = opt['name']
        desc = opt['desc']
        name_color = WHITE if not hover else YELLOW
        name_surf = font.render(name, True, name_color)
        screen.blit(name_surf, (text_x, iy + 5))

        # 描述: 用小号字体
        try:
            desc_font = pygame.font.SysFont('simhei', 13)
        except Exception:
            desc_font = pygame.font.Font(None, 13)
        desc_surf = desc_font.render(desc, True, LIGHT_GRAY)
        screen.blit(desc_surf, (text_x, iy + 25))

        # 价格: 图标保持金色, 数字根据资源情况变色(图标本身不会变红)
        gold_cost = opt.get('cost_gold', 0)
        power_cost = opt.get('cost_power', 0)
        enough_gold = (human is not None and human.gold >= gold_cost)
        enough_power = (power_cost == 0) or (
            human is not None and human.room_id is not None
            and game_state.room_power.get(human.room_id, 0.0) >= power_cost
        )
        affordable = enough_gold and enough_power
        # 数字颜色: 够钱=黄色, 不够=暗红; 但图标保持金色不变
        digit_color = YELLOW if affordable else (180, 60, 60)
        icon_color = GOLD  # 图标始终为金色, 不会变红

        # 右侧价格组合: 闪电图 + 数字 在右, 金币图 + 数字 在其左
        price_right = item_rect.right - 8
        if power_cost > 0:
            pow_digits = str(int(power_cost))
            pow_surf = font.render(pow_digits, True, digit_color)
            pow_w = pow_surf.get_width()
            pow_x = price_right - pow_w
            pow_y = iy + (ITEM_H - 16) // 2
            _draw_lightning_icon(screen, pow_x - 18, pow_y, 16, icon_color)
            screen.blit(pow_surf, (pow_x, pow_y - 2))
            price_right = pow_x - 22

        if gold_cost > 0:
            gold_digits = str(int(gold_cost))
            gold_surf = font.render(gold_digits, True, digit_color)
            gold_w = gold_surf.get_width()
            gold_x = price_right - gold_w
            gold_y = iy + (ITEM_H - 16) // 2
            _draw_coin_icon(screen, gold_x - 18, gold_y, 16, icon_color)
            screen.blit(gold_surf, (gold_x, gold_y - 2))

    screen.set_clip(prev_clip)

    menu['rendered_rects'] = item_rects

    # ─── 滚动条(右侧) - 仅在需要时显示 ───
    if need_scroll:
        sb_x = px + PANEL_W - SCROLLBAR_W - 4
        sb_y = py + HEADER_H + 2
        sb_h = panel_h - HEADER_H - 4
        # 背景轨道
        pygame.draw.rect(screen, (25, 25, 35), (sb_x, sb_y, SCROLLBAR_W, sb_h))
        # 滑块高度 = sb_h * (MAX_VISIBLE / total)
        thumb_h = max(20, int(sb_h * MAX_VISIBLE / total))
        # 滑块位置
        thumb_y = sb_y + int((sb_h - thumb_h) * scroll / max_scroll) if max_scroll > 0 else sb_y
        pygame.draw.rect(screen, (130, 130, 150), (sb_x, thumb_y, SCROLLBAR_W, thumb_h))
        pygame.draw.rect(screen, GRAY, (sb_x, sb_y, SCROLLBAR_W, sb_h), 1)

        # 滚动提示(顶部/底部小箭头提示)
        if scroll > 0:
            arrow_y = sb_y + 2
            pygame.draw.polygon(screen, LIGHT_GRAY, [
                (sb_x + SCROLLBAR_W // 2, arrow_y),
                (sb_x + 1, arrow_y + 5),
                (sb_x + SCROLLBAR_W - 1, arrow_y + 5),
            ])
        if scroll < max_scroll:
            arrow_y = sb_y + sb_h - 6
            pygame.draw.polygon(screen, LIGHT_GRAY, [
                (sb_x + SCROLLBAR_W // 2, arrow_y + 4),
                (sb_x + 1, arrow_y - 1),
                (sb_x + SCROLLBAR_W - 1, arrow_y - 1),
            ])

    menu['_scrollbar_rect'] = (
        pygame.Rect(px + PANEL_W - SCROLLBAR_W - 4, py + HEADER_H + 2, SCROLLBAR_W, panel_h - HEADER_H - 4)
        if need_scroll else None
    )


def _build_option(btype, cost_gold, cost_power=0, extra_desc=None, callback_key=None):
    """构造一个菜单选项 dict。callback_key 可自定义, 缺省为 'build_{btype}'"""
    name, default_desc, _ = BLDG_MENU_INFO.get(btype, (BLDG_NAMES.get(btype, '未知'), '', ''))
    desc = extra_desc if extra_desc else default_desc
    draw_func = _get_building_draw_func(btype)
    if callback_key is None:
        callback_key = f'build_{btype}'
    return {
        'btype': btype,
        'callback_key': callback_key,
        'name': name,
        'desc': desc,
        'cost_gold': cost_gold,
        'cost_power': cost_power,
        'draw_func': draw_func,
    }


def show_build_menu(game_state, col, row, screen_x, screen_y):
    """显示空格子的建造菜单: 含炮塔/维修台 + 15 种新工具
    所有道具均无购买次数限制, 允许玩家无限次购买(只要有空位和资源)
    """
    options = []
    room = get_room_at(game_state.rooms, col, row)
    if room:
        turrets = game_state.get_turrets_in_room(room.id)
        repairs = game_state.get_repairs_in_room(room.id)
        # 防御 / 基础
        if len(turrets) < 4:
            options.append(_build_option(BLDG_TURRET, TURRET_UPGRADE_COST[0], 0,
                                         "自动攻击猎梦者(房间内限4座), 升级提伤加射程"))
        if len(repairs) < 3:
            options.append(_build_option(BLDG_REPAIR, REPAIR_COST, 0,
                                         "持续修复门血(房间内限3座), 升级提速"))
        # 游戏机(可建多个, 持续产电)
        options.append(_build_option(BLDG_GAMEMACHINE, GAMEMACHINE_COST[0], 0,
                                     "持续产出电力(可建多台), 升级提速"))
        # 铜矿(每房间限1个, 通过点击已建铜矿进入升级菜单, 升级为银/金/钻石矿)
        # 仅当该房间内没有任何矿(任意等级)时才显示
        mine_count = sum(1 for b in game_state.buildings
                         if b.type in MINE_TYPES and b.room_id == room.id)
        if mine_count < 1:
            options.append(_build_option(BLDG_MINE_COPPER, MINE_COST_GOLD[0], MINE_COST_POWER[0],
                                         "产金币(可点击升级为银/金/钻石矿)"))
        # 冰箱 / 能量罩 / 诱捕网 / 断头台(每房间限1个, 但无限次购买因为换房间可再建)
        for btype, cg, cp in [
            (BLDG_FRIDGE,     FRIDGE_COST_GOLD,     FRIDGE_COST_POWER),
            (BLDG_SHIELD,     SHIELD_COST_GOLD,     SHIELD_COST_POWER),
            (BLDG_TRAP,       TRAP_COST_GOLD,       TRAP_COST_POWER),
            (BLDG_GUILLOTINE, GUILLOTINE_COST_GOLD, GUILLOTINE_COST_POWER),
        ]:
            count = sum(1 for b in game_state.buildings if b.type == btype and b.room_id == room.id)
            if count < 1:
                _name, base_desc, _ = BLDG_MENU_INFO[btype]
                options.append(_build_option(btype, cg, cp, base_desc))
        # 特殊道具 - 移除购买次数限制, 允许无限次购买
        for btype, cost in [
            (BLDG_GRASS_S,  GRASS_S_COST),
            (BLDG_GRASS_L,  GRASS_L_COST),
            (BLDG_MIRROR,   MIRROR_COST),
            (BLDG_GARLIC,   GARLIC_COST),
            (BLDG_FROG,     FROG_COST),
            (BLDG_BEAR_BED, BEAR_BED_COST),
            (BLDG_SWORD,    SWORD_COST),
        ]:
            _name, base_desc, _ = BLDG_MENU_INFO[btype]
            options.append(_build_option(btype, cost, 0, base_desc))

    if options:
        game_state.popup_menu = {
            'screen_x': screen_x,
            'screen_y': screen_y,
            'options': options,
            'type': 'build',
            'col': col,
            'row': row,
            'title': '建造菜单',
            'scroll': 0,
        }
    else:
        game_state.popup_menu = None


def show_upgrade_menu(game_state, building, screen_x, screen_y):
    """显示建筑升级菜单(沿用新UI格式)"""
    options = []
    if building.can_upgrade():
        cost = building.upgrade_cost()
        # 矿的升级显示为"升级为银/金/钻石矿"
        if building.type in MINE_TYPES:
            new_name = MINE_UPGRADE_NAME.get(building.type, '下一级')
            current_name = BLDG_NAMES.get(building.type, '铜矿')
            options.append(_build_option(building.type, cost, 0,
                                         f"将{current_name}升级为{new_name}",
                                         callback_key='upgrade'))
        else:
            btype_names = {BLDG_DOOR: '门', BLDG_BED: '床', BLDG_TURRET: '炮塔',
                           BLDG_REPAIR: '维修台', BLDG_GAMEMACHINE: '游戏机'}
            name = btype_names.get(building.type, BLDG_NAMES.get(building.type, '未知'))
            new_level = building.level + 2
            # 升级菜单使用 'upgrade' 回调, 避免被错误地当作 'build_*' 处理而崩
            options.append(_build_option(building.type, cost, 0,
                                         f"将{name}升级至Lv{new_level}",
                                         callback_key='upgrade'))

    if options:
        game_state.popup_menu = {
            'screen_x': screen_x,
            'screen_y': screen_y,
            'options': options,
            'type': 'upgrade',
            'building': building,
            'title': '升级菜单',
            'scroll': 0,
        }
    else:
        game_state.popup_menu = None


def handle_popup_click(game_state, mouse_x, mouse_y):
    """处理弹出菜单点击, 返回是否消费了点击"""
    if not hasattr(game_state, 'popup_menu') or game_state.popup_menu is None:
        return False

    menu = game_state.popup_menu

    if 'rendered_rects' not in menu:
        return False

    for rect, idx in menu['rendered_rects']:
        if rect.collidepoint(mouse_x, mouse_y):
            option = menu['options'][idx]
            callback_key = option.get('callback_key', '')

            # 根据 callback_key 精确路由
            if callback_key == 'upgrade':
                # 升级路径: 直接调用 _do_upgrade, 不会走到 _do_build
                _do_upgrade(game_state, menu['building'])
                game_state.popup_menu = None
                return True
            elif callback_key.startswith('build_') and 'btype' in option:
                # 建造路径: 使用 option['btype'] 显式决定建筑类型
                # 防御: 升级菜单若误用此路径, menu 中无 col/row, _do_build 内部已保护
                _do_build(game_state, option['btype'], menu.get('col'), menu.get('row'))
                game_state.popup_menu = None
                return True
            else:
                # 未知回调: 不消费点击
                return False

    # 点击菜单外: 关闭
    game_state.popup_menu = None
    return True


def handle_popup_scroll(game_state, mouse_x, mouse_y, wheel_delta):
    """处理菜单内的滚轮事件。wheel_delta > 0 表示向上滚动(内容向上), < 0 表示向下。
    仅当菜单存在、鼠标在菜单区域上方才生效。"""
    if not hasattr(game_state, 'popup_menu') or game_state.popup_menu is None:
        return False
    menu = game_state.popup_menu
    if 'rendered_rects' not in menu or not menu['rendered_rects']:
        return False

    # 检查鼠标是否在菜单的任意项上(或者滚动条上)
    in_items = any(rect.collidepoint(mouse_x, mouse_y) for rect, _ in menu['rendered_rects'])
    sb_rect = menu.get('_scrollbar_rect')
    in_sb = sb_rect is not None and sb_rect.collidepoint(mouse_x, mouse_y)
    if not in_items and not in_sb:
        return False

    total = len(menu['options'])
    max_scroll = max(0, total - 5)  # MAX_VISIBLE=5
    if max_scroll == 0:
        return False

    # 滚轮向上(deltaY>0 in pygame) -> 列表向下滑 -> scroll 增大
    # 滚轮向下(deltaY<0) -> 列表向上滑 -> scroll 减小
    if wheel_delta > 0:
        menu['scroll'] = min(max_scroll, menu.get('scroll', 0) + 1)
    elif wheel_delta < 0:
        menu['scroll'] = max(0, menu.get('scroll', 0) - 1)
    return True


def _do_build(game_state, btype, col, row):
    """执行建造: 检查金币和电力"""
    human = game_state.player_human
    if human is None:
        return
    # 防御: 门/床是预生成的, 不应通过 _do_build 创建
    if btype in (BLDG_DOOR, BLDG_BED):
        return
    # 防御: 坐标无效则忽略
    if col is None or row is None:
        return
    # 计算该建筑的实际成本
    test_building = Building(btype, col, row, human.room_id)
    gold_cost = test_building.build_cost_gold
    power_cost = test_building.build_cost_power

    # 检查金币
    if human.gold < gold_cost:
        return
    # 检查电力(在放置房间消耗, 一次性扣除)
    room = get_room_at(game_state.rooms, col, row)
    if power_cost > 0:
        if room is None or game_state.room_power.get(room.id, 0) < power_cost:
            return  # 电力不足

    human.gold -= gold_cost
    if power_cost > 0 and room is not None:
        game_state.room_power[room.id] = game_state.room_power.get(room.id, 0) - power_cost

    building = Building(btype, col, row, human.room_id)
    game_state.buildings.append(building)
    game_state.building_at[(col, row)] = building
    # 音效: 建造完成
    if game_state.audio:
        game_state.audio.play_sfx('build_complete')


def _do_upgrade(game_state, building):
    """执行升级"""
    cost = building.upgrade_cost()
    if cost is None:
        return

    human = game_state.player_human
    if human is None or human.gold < cost:
        return

    human.gold -= cost
    building.upgrade()
    # 音效: 升级完成
    if game_state.audio:
        game_state.audio.play_sfx('upgrade_complete')


# ─── 暂停弹窗菜单 ───

def handle_pause_btn_click(game_state, mouse_pos):
    """检查是否点击了暂停按钮: 点击后立即暂停游戏并打开菜单"""
    if hasattr(game_state, '_pause_btn_rect'):
        if game_state._pause_btn_rect.collidepoint(mouse_pos):
            # 暂停按钮行为: 已暂停→继续并关菜单; 未暂停→暂停并开菜单
            if game_state.paused:
                game_state.paused = False
                game_state._pause_menu_open = False
            else:
                game_state.paused = True
                game_state._pause_menu_open = True
            return True
    return False


def render_pause_menu(screen, game_state, font_medium, font_btn):
    """在屏幕中央渲染暂停菜单 (游戏已暂停时, 显示"继续游戏"、"退出游戏"和音频设置)"""
    if not getattr(game_state, '_pause_menu_open', False):
        return

    sw, sh = screen.get_width(), screen.get_height()

    # 半透明遮罩
    overlay = pygame.Surface((sw, sh))
    overlay.set_alpha(160)
    overlay.fill(BLACK)
    screen.blit(overlay, (0, 0))

    # 菜单面板(加高以容纳音频设置)
    panel_w, panel_h = 300, 340
    panel_x = sw // 2 - panel_w // 2
    panel_y = sh // 2 - panel_h // 2
    panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
    pygame.draw.rect(screen, (35, 35, 50), panel_rect)
    pygame.draw.rect(screen, GRAY, panel_rect, 3)

    mouse_x, mouse_y = pygame.mouse.get_pos()

    # 标题
    title = font_btn.render("游戏菜单", True, WHITE)
    screen.blit(title, (panel_x + panel_w // 2 - title.get_width() // 2, panel_y + 15))

    # 两个按钮: 继续游戏 + 退出游戏
    btn_w, btn_h = 220, 38
    btn_x = panel_x + (panel_w - btn_w) // 2
    resume_btn_rect = pygame.Rect(btn_x, panel_y + 55, btn_w, btn_h)
    exit_btn_rect = pygame.Rect(btn_x, panel_y + 100, btn_w, btn_h)

    for rect, label, base_color, hover_color in [
        (resume_btn_rect, "继续游戏", (40, 130, 60), (60, 170, 90)),
        (exit_btn_rect, "退出游戏", (160, 50, 50), (210, 70, 70)),
    ]:
        hover = rect.collidepoint(mouse_x, mouse_y)
        bg = hover_color if hover else base_color
        pygame.draw.rect(screen, bg, rect)
        pygame.draw.rect(screen, WHITE, rect, 2)
        text = font_medium.render(label, True, WHITE)
        screen.blit(text, (rect.centerx - text.get_width() // 2,
                          rect.centery - text.get_height() // 2))

    # ─── 音频设置区域 ───
    audio_y_start = panel_y + 150
    # 分隔线
    pygame.draw.line(screen, GRAY, (panel_x + 15, audio_y_start), (panel_x + panel_w - 15, audio_y_start), 1)

    audio_title = font_medium.render("音频设置", True, YELLOW)
    screen.blit(audio_title, (panel_x + panel_w // 2 - audio_title.get_width() // 2, audio_y_start + 8))

    audio = game_state.audio
    rects = {}

    if audio:
        # 音乐音量
        label_bgm = font_medium.render("音乐", True, LIGHT_GRAY)
        screen.blit(label_bgm, (panel_x + 20, audio_y_start + 38))
        slider_x = panel_x + 70
        slider_w = 160
        slider_y_bgm = audio_y_start + 42
        slider_h = 14
        bgm_slider_rect = pygame.Rect(slider_x, slider_y_bgm, slider_w, slider_h)
        pygame.draw.rect(screen, (25, 25, 35), bgm_slider_rect)
        pygame.draw.rect(screen, GRAY, bgm_slider_rect, 1)
        fill_w = int(slider_w * audio.bgm_volume)
        if fill_w > 0:
            pygame.draw.rect(screen, (80, 140, 220), (slider_x, slider_y_bgm, fill_w, slider_h))
        bgm_pct = font_medium.render(f"{int(audio.bgm_volume * 100)}%", True, LIGHT_GRAY)
        screen.blit(bgm_pct, (slider_x + slider_w + 8, slider_y_bgm - 2))
        rects['bgm_slider'] = bgm_slider_rect

        # 音效音量
        label_sfx = font_medium.render("音效", True, LIGHT_GRAY)
        screen.blit(label_sfx, (panel_x + 20, audio_y_start + 68))
        slider_y_sfx = audio_y_start + 72
        sfx_slider_rect = pygame.Rect(slider_x, slider_y_sfx, slider_w, slider_h)
        pygame.draw.rect(screen, (25, 25, 35), sfx_slider_rect)
        pygame.draw.rect(screen, GRAY, sfx_slider_rect, 1)
        fill_w_sfx = int(slider_w * audio.sfx_volume)
        if fill_w_sfx > 0:
            pygame.draw.rect(screen, (80, 200, 120), (slider_x, slider_y_sfx, fill_w_sfx, slider_h))
        sfx_pct = font_medium.render(f"{int(audio.sfx_volume * 100)}%", True, LIGHT_GRAY)
        screen.blit(sfx_pct, (slider_x + slider_w + 8, slider_y_sfx - 2))
        rects['sfx_slider'] = sfx_slider_rect

        # 开关按钮
        bgm_toggle_rect = pygame.Rect(panel_x + 25, audio_y_start + 100, 110, 30)
        bgm_hover = bgm_toggle_rect.collidepoint(mouse_x, mouse_y)
        bgm_color = (40, 130, 60) if audio.bgm_enabled else (130, 50, 50)
        bgm_color = tuple(min(255, c + 30) for c in bgm_color) if bgm_hover else bgm_color
        pygame.draw.rect(screen, bgm_color, bgm_toggle_rect)
        pygame.draw.rect(screen, WHITE, bgm_toggle_rect, 1)
        bgm_text = "♪ 音乐 开" if audio.bgm_enabled else "♪ 音乐 关"
        bgm_surf = font_medium.render(bgm_text, True, WHITE)
        screen.blit(bgm_surf, (bgm_toggle_rect.centerx - bgm_surf.get_width() // 2,
                                bgm_toggle_rect.centery - bgm_surf.get_height() // 2))
        rects['bgm_toggle'] = bgm_toggle_rect

        sfx_toggle_rect = pygame.Rect(panel_x + 155, audio_y_start + 100, 110, 30)
        sfx_hover = sfx_toggle_rect.collidepoint(mouse_x, mouse_y)
        sfx_color = (40, 130, 60) if audio.sfx_enabled else (130, 50, 50)
        sfx_color = tuple(min(255, c + 30) for c in sfx_color) if sfx_hover else sfx_color
        pygame.draw.rect(screen, sfx_color, sfx_toggle_rect)
        pygame.draw.rect(screen, WHITE, sfx_toggle_rect, 1)
        sfx_text = "🔊 音效 开" if audio.sfx_enabled else "🔊 音效 关"
        sfx_surf = font_medium.render(sfx_text, True, WHITE)
        screen.blit(sfx_surf, (sfx_toggle_rect.centerx - sfx_surf.get_width() // 2,
                                sfx_toggle_rect.centery - sfx_surf.get_height() // 2))
        rects['sfx_toggle'] = sfx_toggle_rect

    game_state._pause_menu_rects = {
        'resume': resume_btn_rect,
        'exit': exit_btn_rect,
        'audio': rects,
    }


def handle_pause_menu_click(game_state, mouse_pos):
    """处理暂停菜单按钮点击, 返回是否需要继续处理事件"""
    rects = getattr(game_state, '_pause_menu_rects', None)
    if rects is None:
        return False
    if rects['resume'].collidepoint(mouse_pos):
        # 继续游戏: 关闭暂停状态和菜单
        game_state.paused = False
        game_state._pause_menu_open = False
        if game_state.audio:
            game_state.audio.unpause_all()
        return True
    if rects['exit'].collidepoint(mouse_pos):
        # 退出游戏: 返回主菜单
        game_state.phase = PHASE_MENU
        game_state.paused = False
        game_state._pause_menu_open = False
        game_state.popup_menu = None
        return True

    # 音频控件点击
    audio_rects = rects.get('audio', {})
    audio = game_state.audio
    if audio and audio_rects:
        if 'bgm_slider' in audio_rects and audio_rects['bgm_slider'].collidepoint(mouse_pos):
            rel_x = mouse_pos[0] - audio_rects['bgm_slider'].x
            vol = max(0.0, min(1.0, rel_x / audio_rects['bgm_slider'].width))
            audio.set_bgm_volume(vol)
            return True
        if 'sfx_slider' in audio_rects and audio_rects['sfx_slider'].collidepoint(mouse_pos):
            rel_x = mouse_pos[0] - audio_rects['sfx_slider'].x
            vol = max(0.0, min(1.0, rel_x / audio_rects['sfx_slider'].width))
            audio.set_sfx_volume(vol)
            return True
        if 'bgm_toggle' in audio_rects and audio_rects['bgm_toggle'].collidepoint(mouse_pos):
            audio.toggle_bgm()
            return True
        if 'sfx_toggle' in audio_rects and audio_rects['sfx_toggle'].collidepoint(mouse_pos):
            audio.toggle_sfx()
            return True

    # 点击菜单外: 关闭菜单 (但保持暂停状态以避免误操作)
    return True
