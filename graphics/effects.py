"""
金币飘字、伤害数字特效
"""
import pygame
from core.config import *
from ui.ui_camera import VIEWPORT_SIZE


def update_effects(game_state, dt):
    """更新所有特效计时器"""
    if hasattr(game_state, 'damage_numbers'):
        for dn in game_state.damage_numbers[:]:
            dn['timer'] -= dt
            if dn['timer'] <= 0:
                game_state.damage_numbers.remove(dn)

    if hasattr(game_state, 'gold_numbers'):
        for gn in game_state.gold_numbers[:]:
            gn['timer'] -= dt
            if gn['timer'] <= 0:
                game_state.gold_numbers.remove(gn)

    if hasattr(game_state, 'heal_numbers'):
        for hn in game_state.heal_numbers[:]:
            hn['timer'] -= dt
            if hn['timer'] <= 0:
                game_state.heal_numbers.remove(hn)


def render_effects(screen, game_state, camera, font, left, top, scale, gax, gay):
    """渲染所有特效(屏幕坐标=viewport坐标×scale+偏移)

    关键: 严格裁剪到 play area 矩形内, 防止任何特效溢出到两侧黑边
    """
    # play area 在屏幕上的实际像素矩形 (严格边界, 不留容差)
    play_w = int(VIEWPORT_SIZE * scale)
    play_h = int(VIEWPORT_SIZE * scale)
    play_rect = pygame.Rect(int(gax), int(gay), play_w, play_h)

    # 保存原 clip, 设置新 clip 为 play area (画完特效后恢复)
    prev_clip = screen.get_clip()
    screen.set_clip(play_rect)

    try:
        # 粗筛: 仅当特效中心点在 viewport 内地图像素范围内时才渲染
        # (浮在上方的数字可能稍微超出顶部, 依靠 set_clip 裁剪)
        def _in_view(col, row):
            px = col * TILE_SIZE + TILE_SIZE // 2
            py = row * TILE_SIZE + TILE_SIZE // 2
            return left <= px <= left + VIEWPORT_SIZE and top <= py <= top + VIEWPORT_SIZE

        if hasattr(game_state, 'damage_numbers'):
            for dn in game_state.damage_numbers:
                if not _in_view(dn['col'], dn['row']):
                    continue
                vx = dn['col'] * TILE_SIZE + TILE_SIZE // 2 - left
                vy = dn['row'] * TILE_SIZE - top - 28 - (1.0 - dn['timer']) * 25
                sx = vx * scale + gax
                sy = vy * scale + gay
                alpha = int(255 * dn['timer'])
                text = font.render(str(dn['value']), True, dn['color'])
                text.set_alpha(alpha)
                screen.blit(text, (sx - text.get_width() // 2 - 10, sy))

        if hasattr(game_state, 'gold_numbers'):
            for gn in game_state.gold_numbers:
                if not _in_view(gn['col'], gn['row']):
                    continue
                vx = gn['col'] * TILE_SIZE + TILE_SIZE // 2 - left
                vy = gn['row'] * TILE_SIZE - top - 18 - (1.0 - gn['timer']) * 20
                sx = vx * scale + gax
                sy = vy * scale + gay
                alpha = int(255 * gn['timer'])
                text = font.render(gn['value'], True, gn['color'])
                text.set_alpha(alpha)
                screen.blit(text, (sx - text.get_width() // 2, sy))

        if hasattr(game_state, 'heal_numbers'):
            for hn in game_state.heal_numbers:
                if not _in_view(hn['col'], hn['row']):
                    continue
                vx = hn['col'] * TILE_SIZE + TILE_SIZE // 2 - left
                vy = hn['row'] * TILE_SIZE - top - 28 - (1.0 - hn['timer']) * 20
                sx = vx * scale + gax
                sy = vy * scale + gay
                alpha = int(255 * hn['timer'])
                text = font.render(str(hn['value']), True, hn['color'])
                text.set_alpha(alpha)
                screen.blit(text, (sx - text.get_width() // 2 + 10, sy))
    finally:
        # 恢复原 clip, 不影响其他绘制
        screen.set_clip(prev_clip)
