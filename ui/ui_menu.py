"""
像素风主菜单: 难度选择 + 双模式选择
"""
import pygame
import math
from core.config import *
from core.save_data import is_difficulty_unlocked, is_endless_unlocked, get_endless_best_wave


class MenuButton:
    def __init__(self, rect, text, color, hover_color):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.hovered = False

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, screen, font):
        bg = self.hover_color if self.hovered else self.color
        # 像素边框效果
        shadow_rect = self.rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(screen, (20, 20, 30), shadow_rect)
        pygame.draw.rect(screen, bg, self.rect)
        # 像素描边(双层)
        pygame.draw.rect(screen, WHITE, self.rect, 3)
        pygame.draw.rect(screen, BLACK, self.rect, 1)

        text_surf = font.render(self.text, True, WHITE)
        tx = self.rect.centerx - text_surf.get_width() // 2
        ty = self.rect.centery - text_surf.get_height() // 2
        screen.blit(text_surf, (tx, ty))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class DiffSelectButton:
    """难度选择按钮, 带选中高亮和锁定状态"""
    def __init__(self, rect, difficulty, diff_name, color, hover_color, selected_color, locked_color):
        self.rect = pygame.Rect(rect)
        self.difficulty = difficulty
        self.diff_name = diff_name
        self.color = color
        self.hover_color = hover_color
        self.selected_color = selected_color
        self.locked_color = locked_color
        self.hovered = False
        self.selected = False
        self.locked = True  # 默认锁定

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)
        self.locked = not is_difficulty_unlocked(self.difficulty)

    def draw(self, screen, font):
        if self.locked:
            bg = self.locked_color
        elif self.selected:
            bg = self.selected_color
        elif self.hovered:
            bg = self.hover_color
        else:
            bg = self.color

        # 像素边框效果
        shadow_rect = self.rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(screen, (20, 20, 30), shadow_rect)
        pygame.draw.rect(screen, bg, self.rect)

        if self.locked:
            # 锁定: 灰色边框 + 锁图标
            pygame.draw.rect(screen, GRAY, self.rect, 2)
            pygame.draw.rect(screen, BLACK, self.rect, 1)
            cx = self.rect.centerx
            cy = self.rect.centery - 4
            pygame.draw.rect(screen, DARK_GRAY, (cx - 4, cy, 8, 7))
            pygame.draw.rect(screen, GRAY, (cx - 3, cy + 1, 6, 5))
            pygame.draw.arc(screen, GRAY, (cx - 3, cy - 5, 6, 8), 0, 3.14, 2)
        else:
            border_color = (255, 215, 0) if self.selected else WHITE
            pygame.draw.rect(screen, border_color, self.rect, 3 if self.selected else 2)
            pygame.draw.rect(screen, BLACK, self.rect, 1)

        text_surf = font.render(self.diff_name, True, WHITE if not self.locked else DARK_GRAY)
        tx = self.rect.centerx - text_surf.get_width() // 2
        ty = self.rect.centery - text_surf.get_height() // 2 + (6 if self.locked else 0)
        screen.blit(text_surf, (tx, ty))

    def is_clicked(self, pos):
        if self.locked:
            return False
        return self.rect.collidepoint(pos)


def render_menu(screen, font_title, font_btn, mode_buttons, diff_buttons, endless_btn):
    """渲染主菜单(内容垂直居中)"""
    sw, sh = screen.get_width(), screen.get_height()
    screen.fill((15, 15, 25))

    # 背景装饰 - 网格线
    for x in range(0, sw, 32):
        pygame.draw.line(screen, (25, 25, 40), (x, 0), (x, sh))
    for y in range(0, sh, 32):
        pygame.draw.line(screen, (25, 25, 40), (0, y), (sw, y))

    try:
        label_font = pygame.font.SysFont('simhei', 18)
        small_font = pygame.font.SysFont('simhei', 14)
    except Exception:
        label_font = pygame.font.Font(None, 18)
        small_font = pygame.font.Font(None, 14)

    # ── 计算整体内容高度, 垂直居中 ──
    title_h = 48 + 7 + 48       # 标题 + 间距 + 副标题
    gap1 = 30                    # 标题→难度标签
    label_h = 18                 # 标签高度
    gap2 = 5                     # 标签→按钮
    btn_h = 36                   # 难度按钮高度
    gap3 = 60                    # 难度→模式按钮
    mode_btn_h = 65              # 模式按钮高度
    mode_gap = 25                # 两个模式按钮间距
    bottom_margin = 45           # 底部提示+边距

    total_h = (title_h + gap1 + label_h + gap2 + btn_h
               + gap3 + mode_btn_h + mode_gap + mode_btn_h + bottom_margin)
    start_y = (sh - total_h) // 2

    # 标题
    title_text = "DREAM LOBBY"
    title_surf = font_title.render(title_text, True, (180, 140, 255))
    tx = sw // 2 - title_surf.get_width() // 2
    ty = start_y
    shadow = font_title.render(title_text, True, (60, 30, 100))
    screen.blit(shadow, (tx + 4, ty + 4))
    screen.blit(title_surf, (tx, ty))

    # 副标题
    sub_text = "盗 梦 空 间"
    sub_surf = font_title.render(sub_text, True, (200, 180, 240))
    sx = sw // 2 - sub_surf.get_width() // 2
    screen.blit(sub_surf, (sx, ty + 55))

    # 难度选择标签
    cur_y = start_y + title_h + gap1
    label = label_font.render("选择难度:", True, (180, 180, 200))
    screen.blit(label, (sw // 2 - 280, cur_y))

    # 动态调整难度按钮Y坐标到居中位置
    diff_btn_y = cur_y + label_h + gap2
    for btn in diff_buttons:
        btn.rect.y = diff_btn_y

    # 难度按钮
    for btn in diff_buttons:
        btn.draw(screen, label_font)

    # 无尽模式最高波数
    if endless_btn and is_endless_unlocked():
        best = get_endless_best_wave()
        if best > 0:
            wave_text = small_font.render(f"最高波数: {best}", True, (220, 150, 255))
            screen.blit(wave_text, (endless_btn.rect.right + 8, endless_btn.rect.centery - 7))

    # 模式按钮(动态调整Y坐标)
    mode_y1 = diff_btn_y + btn_h + gap3
    mode_y2 = mode_y1 + mode_btn_h + mode_gap
    if len(mode_buttons) >= 2:
        mode_buttons[0].rect.y = mode_y1
        mode_buttons[1].rect.y = mode_y2
    for btn in mode_buttons:
        btn.draw(screen, font_btn)

    # 底部提示
    hint = small_font.render("选择难度和角色开始游戏...", True, LIGHT_GRAY)
    screen.blit(hint, (sw // 2 - hint.get_width() // 2, sh - 35))


def create_diff_buttons():
    """创建难度选择按钮(含无尽模式)"""
    btn_w = 72
    btn_h = 36
    cx = SCREEN_WIDTH // 2
    # Y坐标: 在render_menu中动态计算后统一设置
    # 这里先设一个默认值, render_menu会根据居中计算调整
    y = 200
    gap = 8
    total_w = 7 * btn_w + 6 * gap
    start_x = cx - total_w // 2

    diff_configs = [
        (DIFF_EASY, DIFF_NAMES[DIFF_EASY], (40, 80, 50), (60, 120, 70), (80, 180, 100), (50, 50, 55)),
        (DIFF_NORMAL, DIFF_NAMES[DIFF_NORMAL], (60, 70, 30), (90, 110, 50), (130, 160, 70), (50, 50, 55)),
        (DIFF_HARD, DIFF_NAMES[DIFF_HARD], (80, 60, 30), (120, 90, 50), (170, 130, 70), (50, 50, 55)),
        (DIFF_NIGHTMARE, DIFF_NAMES[DIFF_NIGHTMARE], (90, 40, 40), (140, 60, 60), (190, 90, 90), (50, 50, 55)),
        (DIFF_HELL, DIFF_NAMES[DIFF_HELL], (100, 30, 30), (150, 50, 50), (200, 80, 80), (50, 50, 55)),
        (DIFF_PURGATORY, DIFF_NAMES[DIFF_PURGATORY], (70, 20, 90), (110, 40, 130), (160, 70, 180), (50, 50, 55)),
    ]

    buttons = []
    for i, (diff, name, color, hover, selected, locked) in enumerate(diff_configs):
        x = start_x + i * (btn_w + gap)
        btn = DiffSelectButton(
            (x, y, btn_w, btn_h),
            diff, name, color, hover, selected, locked,
        )
        if i == 0:
            btn.selected = True
        buttons.append(btn)

    # 无尽模式按钮
    endless_x = start_x + 6 * (btn_w + gap)
    endless_btn = DiffSelectButton(
        (endless_x, y, btn_w, btn_h),
        DIFF_ENDLESS, DIFF_NAMES[DIFF_ENDLESS],
        (80, 30, 80), (120, 50, 120), (170, 80, 170), (50, 50, 55),
    )
    buttons.append(endless_btn)

    return buttons


def create_menu_buttons():
    """创建两个模式选择按钮"""
    btn_w = 300
    btn_h = 65
    cx = SCREEN_WIDTH // 2
    y1 = 310
    y2 = 400

    btn_human = MenuButton(
        (cx - btn_w // 2, y1, btn_w, btn_h),
        "人类模式",
        (40, 80, 180),
        (60, 120, 240),
    )
    btn_hunter = MenuButton(
        (cx - btn_w // 2, y2, btn_w, btn_h),
        "猎梦者模式",
        (160, 40, 40),
        (220, 60, 60),
    )
    return [btn_human, btn_hunter]
