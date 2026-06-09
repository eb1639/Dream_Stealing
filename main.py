"""
《盗梦空间》— 主入口、游戏循环、状态机
"""
import sys
import random
import pygame
from core.config import *
from core.game_state import GameState
from core.save_data import is_difficulty_unlocked, is_endless_unlocked, on_difficulty_cleared, update_endless_best_wave, get_endless_best_wave
from world.map_data import *
from systems.systems import *
from systems.systems import _trigger_door_open
from graphics.renderer import render_game
from ui.ui_menu import render_menu, create_menu_buttons, create_diff_buttons
from ui.ui_hud import (show_build_menu, show_upgrade_menu, handle_popup_click,
                    handle_popup_scroll, handle_pause_btn_click,
                    render_pause_menu, handle_pause_menu_click)
from ui.ui_camera import Camera
from ui.input_router import InputRouter
from graphics.effects import update_effects
from core.audio import AudioManager, BGM_MENU, BGM_SAFE, BGM_BATTLE


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("DREAM LOBBY - Dao Meng Kong Jian")
    clock = pygame.time.Clock()

    def _make_font(size):
        try:
            return pygame.font.SysFont('simhei', size)
        except Exception:
            return pygame.font.Font(None, size)

    font_small = _make_font(14)
    font_medium = _make_font(18)
    font_btn = _make_font(24)
    font_title = _make_font(48)

    game_state = GameState()
    audio = AudioManager()
    game_state.audio = audio
    camera = Camera()
    input_router = InputRouter(camera)
    menu_buttons = create_menu_buttons()
    diff_buttons = create_diff_buttons()
    selected_difficulty = DIFF_EASY

    economy_accumulator = 0.0

    # 启动菜单 BGM
    audio.play_bgm(BGM_MENU)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        if dt > 0.1:
            dt = 0.1

        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game_state.phase in (PHASE_PLAYING, PHASE_SAFE):
                        game_state.phase = PHASE_MENU
                        game_state.popup_menu = None
                        audio.play_bgm(BGM_MENU)
                    elif game_state.is_game_over():
                        game_state.phase = PHASE_MENU
                        game_state.popup_menu = None
                        audio.play_bgm(BGM_MENU)
                elif event.key == pygame.K_p:
                    if game_state.phase in (PHASE_PLAYING, PHASE_SAFE):
                        if game_state.paused:
                            game_state.paused = False
                            game_state._pause_menu_open = False
                            audio.unpause_all()
                        else:
                            game_state.paused = True
                            game_state._pause_menu_open = True
                            audio.pause_all()
                elif event.key == pygame.K_f:
                    if game_state.phase in (PHASE_PLAYING, PHASE_SAFE) and not game_state.paused:
                        from systems.systems import cast_dragon_sword
                        cast_dragon_sword(game_state)

            cam_event, cam_data = input_router.handle_event(event, game_state)

            if game_state.phase == PHASE_MENU:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # 难度选择
                    for dbtn in diff_buttons:
                        if dbtn.is_clicked(event.pos):
                            audio.play_sfx('button_click')
                            selected_difficulty = dbtn.difficulty
                            for db in diff_buttons:
                                db.selected = (db.difficulty == selected_difficulty)
                            break
                    # 模式选择
                    for i, btn in enumerate(menu_buttons):
                        if btn.is_clicked(event.pos):
                            audio.play_sfx('button_click')
                            mode = MODE_HUMAN if i == 0 else MODE_HUNTER

                            # 人类模式: 检查难度是否解锁
                            if mode == MODE_HUMAN:
                                if selected_difficulty == DIFF_ENDLESS:
                                    if not is_endless_unlocked():
                                        continue  # 无尽模式未解锁
                                    game_state.init_game(mode, None, DIFF_ENDLESS, True)
                                else:
                                    if not is_difficulty_unlocked(selected_difficulty):
                                        continue  # 难度未解锁
                                    game_state.init_game(mode, None, selected_difficulty, False)
                            else:
                                # 猎梦者模式: 不分难度, 地图随机
                                game_state.init_game(mode, None, DIFF_EASY, False)

                            audio.play_bgm(BGM_SAFE)
                            camera.reset()
                            if mode == MODE_HUMAN:
                                camera.set_target(game_state.player_human)
                            else:
                                camera.set_target(game_state.dream_hunter)
                            camera.snap_to_entity(camera.target_entity)
                            # 关键: 必须注册 game_state 引用, 否则门动画触发器无法工作
                            set_current_game_state(game_state)
                            game_state.popup_menu = None
                            game_state._pause_menu_open = False
                            economy_accumulator = 0.0
                            break

            elif game_state.phase in (PHASE_SAFE, PHASE_PLAYING):
                if getattr(game_state, '_pause_menu_open', False):
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        handle_pause_menu_click(game_state, event.pos)
                    continue

                if game_state.paused:
                    if cam_event == 'hud_click':
                        mx, my = cam_data
                        if handle_pause_btn_click(game_state, (mx, my)):
                            continue
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if not game_state._pause_menu_open:
                            game_state._pause_menu_open = True
                    continue

                if cam_event == 'hud_click':
                    mx, my = cam_data
                    if handle_pause_btn_click(game_state, (mx, my)):
                        if game_state.paused:
                            audio.pause_all()
                        else:
                            audio.unpause_all()
                        continue
                    if hasattr(game_state, 'avatar_rects'):
                        for human_id, rect in game_state.avatar_rects.items():
                            if rect.collidepoint(mx, my):
                                human = game_state.get_human_by_id(human_id)
                                if human and human.alive and human.state == HUMAN_BED:
                                    if human.is_player and game_state.mode == MODE_HUMAN:
                                        camera.set_target(human)
                                        camera.snap_to_entity(human)
                                    else:
                                        camera.snap_to_entity(human)
                                        camera.follow_player = False
                                    break
                    if (hasattr(game_state, 'hunter_avatar_rect') and
                            game_state.hunter_avatar_rect and
                            game_state.hunter_avatar_rect.collidepoint(mx, my)):
                        camera.set_target(game_state.dream_hunter)
                        camera.snap_to_entity(game_state.dream_hunter)

                elif cam_event == 'click':
                    if game_state.popup_menu:
                        handle_popup_click(game_state, *mouse_pos)
                    else:
                        scale = getattr(game_state, '_scale', 1.0)
                        gax = getattr(game_state, '_game_area_x', 0)
                        gay = getattr(game_state, '_game_area_y', HUD_HEIGHT)
                        gx, gy = camera.screen_to_grid(*mouse_pos, gax, gay, scale)
                        _handle_map_click(game_state, gx, gy, mouse_pos)

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if game_state.popup_menu:
                        consumed = handle_popup_click(game_state, *mouse_pos)
                        if consumed:
                            continue

                if event.type == pygame.MOUSEWHEEL:
                    if game_state.popup_menu:
                        handle_popup_scroll(game_state, *mouse_pos, event.y)

                # 空格键: 手动开门(玩家相邻已关闭的门时)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    _try_player_open_door(game_state)

            elif game_state.is_game_over():
                if event.type == pygame.MOUSEBUTTONDOWN or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE
                ):
                    # 通关存档
                    if game_state.victory and game_state.mode == MODE_HUMAN:
                        if game_state.is_endless:
                            update_endless_best_wave(game_state.endless_wave)
                        else:
                            on_difficulty_cleared(game_state.difficulty)
                    game_state.phase = PHASE_MENU
                    audio.play_bgm(BGM_MENU)

        # ─── 玩家输入移动 ───
        if (game_state.phase in (PHASE_SAFE, PHASE_PLAYING)
                and not game_state.paused
                and not getattr(game_state, '_pause_menu_open', False)):
            keys = pygame.key.get_pressed()
            dx, dy = 0, 0
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                dy = -1
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                dy = 1
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                dx = -1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                dx = 1

            if dx != 0 or dy != 0:
                _handle_player_move(game_state, dx, dy, camera, dt)

        # ─── 更新 ───
        if not game_state.paused:
            if game_state.phase == PHASE_SAFE:
                game_state.safe_timer -= dt
                _update_safe_phase(game_state, dt)
                if game_state.safe_timer <= 0:
                    game_state.safe_timer = 0
                    game_state.phase = PHASE_PLAYING
                    audio.play_bgm(BGM_BATTLE)

            elif game_state.phase == PHASE_PLAYING:
                game_state.game_time += dt
                _update_playing_phase(game_state, dt)

                # 根据猎梦者等级切换 BGM 紧张度
                if game_state.dream_hunter:
                    audio.update_bgm_for_hunter_level(game_state.dream_hunter.level + 1)

                economy_accumulator += dt
                if economy_accumulator >= 1.0:
                    economy_accumulator -= 1.0
                    update_economy(game_state, 1.0)
                    _spawn_gold_effects(game_state)

                for h in game_state.humans:
                    h.is_under_attack = False
                for b in game_state.buildings:
                    b.being_repaired = False

        camera.update(dt)
        update_effects(game_state, dt)

        # ─── 渲染 ───
        if game_state.phase == PHASE_MENU:
            mouse_pos = pygame.mouse.get_pos()
            for btn in menu_buttons:
                btn.update(mouse_pos)
            for dbtn in diff_buttons:
                dbtn.update(mouse_pos)
            # 无尽模式按钮单独取出
            endless_btn = diff_buttons[-1] if diff_buttons and diff_buttons[-1].difficulty == DIFF_ENDLESS else None
            render_menu(screen, font_title, font_btn, menu_buttons, diff_buttons, endless_btn)

        elif game_state.phase in (PHASE_SAFE, PHASE_PLAYING):
            render_game(screen, game_state, camera, font_small, font_medium)
            render_pause_menu(screen, game_state, font_medium, font_btn)

        elif game_state.is_game_over():
            _render_game_over(screen, game_state, font_title, font_medium)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


def _handle_player_move(game_state, dx, dy, camera, dt):
    if game_state.mode == MODE_HUMAN:
        human = game_state.player_human
        if human is None or not human.alive:
            return
        if human.state == HUMAN_BED:
            return

        human.move_timer -= dt
        move_interval = 1.0 / HUMAN_SPEED
        if human.move_timer > 0:
            return
        human.move_timer = move_interval

        door_hp_map = {}
        moved = move_entity_by_input(human, dx, dy, game_state.grid, door_hp_map, 'human_wandering')
        if moved:
            _check_bed_occupy(game_state, human)
            camera.set_target(human)

    elif game_state.mode == MODE_HUNTER:
        hunter = game_state.dream_hunter
        if hunter is None or not hunter.alive:
            return
        if game_state.phase == PHASE_SAFE:
            return

        hunter.move_timer -= dt
        move_interval = 1.0 / HUNTER_SPEED[0]
        if hunter.move_timer > 0:
            return
        hunter.move_timer = move_interval

        door_hp_map = {(b.grid_col, b.grid_row): b.current_hp
                       for b in game_state.buildings if b.type == BLDG_DOOR}
        moved = move_entity_by_input(hunter, dx, dy, game_state.grid, door_hp_map,
                                     'hunter', game_state.rooms)
        if moved:
            camera.set_target(hunter)


def _try_player_open_door(game_state):
    """玩家按空格键: 检查是否相邻已关闭的门, 是则触发开门"""
    if game_state.mode == MODE_HUMAN:
        human = game_state.player_human
    else:
        hunter = game_state.dream_hunter
        if hunter is None or not hunter.alive:
            return
        # 猎梦者模式下, 猎梦者也可以开门
        hc, hr = hunter.pos
        for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nc, nr = hc + dc, hr + dr
            if 0 <= nc < MAP_COLS and 0 <= nr < MAP_ROWS:
                building = game_state.get_building_at(nc, nr)
                if building and building.type == BLDG_DOOR and building.is_door_closed and building.current_hp > 0:
                    _trigger_door_open(game_state, nc, nr)
                    return
        return

    if human is None or not human.alive:
        return
    hc, hr = human.pos
    for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nc, nr = hc + dc, hr + dr
        if 0 <= nc < MAP_COLS and 0 <= nr < MAP_ROWS:
            building = game_state.get_building_at(nc, nr)
            if building and building.type == BLDG_DOOR and building.is_door_closed and building.current_hp > 0:
                _trigger_door_open(game_state, nc, nr)
                return


def _check_bed_occupy(game_state, human):
    """检测人类是否到达床格, 触发上床锁定"""
    bc, br = human.pos
    building = game_state.get_building_at(bc, br)
    if building and building.type == BLDG_BED:
        room_human = game_state.get_human_in_room(building.room_id)
        if room_human is None:
            human.set_bed(building.room_id, bc, br)
            game_state.reserved_room_ids.add(building.room_id)
        elif room_human.id != human.id:
            if human.room_id is not None:
                game_state.reserved_room_ids.discard(human.room_id)
            human.room_id = None
            human.move_path = []


def _update_safe_phase(game_state, dt):
    for human in game_state.humans:
        if not human.alive or human.is_player:
            continue
        if human.state != HUMAN_WANDERING:
            continue
        if not human.move_path:
            continue
        move_along_path(human, human.speed, dt)
        _check_bed_occupy(game_state, human)

    # 推进门滑动动画(蓝格↔红格)
    update_door_animations(game_state, dt)
    # 推进屠龙刀斩击动画(飞向→砍击→飞回)
    update_sword_animations(game_state, dt)

    for human in game_state.humans:
        if not human.alive or human.is_player:
            continue
        if human.state != HUMAN_WANDERING:
            continue
        if not human.move_path and human.room_id is None:
            _assign_room_to_ai(game_state, human)


def _assign_room_to_ai(game_state, human):
    """为AI人类分配未预订且无活人入住的房间"""
    available = [r for r in game_state.rooms
                 if r.id not in game_state.reserved_room_ids
                 and game_state.get_human_in_room(r.id) is None]
    if not available:
        return

    room = min(available, key=lambda r: heuristic(human.pos, list(r.cells)[len(r.cells) // 2]))
    bed = game_state.get_bed_in_room(room.id)
    if bed:
        bc, br = bed.pos
        path = find_path(game_state.grid, human.pos, (bc, br), 'human_wandering')
        if path:
            human.move_path = path
            human.room_id = room.id
            game_state.reserved_room_ids.add(room.id)


def _update_playing_phase(game_state, dt):
    update_movement(game_state, dt)

    if game_state.game_time > 2.0:
        update_ai(game_state, dt)

    update_combat(game_state, dt)

    # 推进门滑动动画(蓝格↔红格)
    update_door_animations(game_state, dt)
    # 推进屠龙刀斩击动画(飞向→砍击→飞回)
    update_sword_animations(game_state, dt)

    check_win_lose(game_state)

    # 无尽模式波次递增
    if game_state.is_endless:
        update_endless_wave(game_state, dt)


def _spawn_gold_effects(game_state):
    for human in game_state.humans:
        if human.state == HUMAN_BED and human.alive:
            bed = game_state.get_bed_in_room(human.room_id)
            if bed:
                spawn_gold_number(game_state, bed.grid_col, bed.grid_row, bed.gold_per_sec)


def _handle_map_click(game_state, grid_x, grid_y, mouse_pos):
    if game_state.mode != MODE_HUMAN:
        return
    player = game_state.player_human
    if player is None or not player.alive or player.state != HUMAN_BED:
        return

    mx, my = mouse_pos

    building = game_state.get_building_at(grid_x, grid_y)
    if building:
        if building.room_id == player.room_id:
            show_upgrade_menu(game_state, building, mx, my)
        return

    room = get_room_at(game_state.rooms, grid_x, grid_y)
    if room and room.id == player.room_id:
        if game_state.get_building_at(grid_x, grid_y) is None:
            if game_state.grid[grid_y][grid_x] == TILE_ROOM:
                show_build_menu(game_state, grid_x, grid_y, mx, my)
                return

    game_state.popup_menu = None


def _render_game_over(screen, game_state, font_title, font_medium):
    sw, sh = screen.get_width(), screen.get_height()
    overlay = pygame.Surface((sw, sh))
    overlay.set_alpha(180)
    overlay.fill(BLACK)
    screen.blit(overlay, (0, 0))

    if game_state.victory:
        text = "胜利！"
        color = GREEN
    else:
        text = "失败"
        color = RED

    title_surf = font_title.render(text, True, color)
    tx = sw // 2 - title_surf.get_width() // 2
    ty = sh // 2 - 60
    screen.blit(title_surf, (tx, ty))

    # 无尽模式显示波数
    if game_state.is_endless:
        wave_text = f"坚持到第 {game_state.endless_wave} 波"
        wave_surf = font_medium.render(wave_text, True, (220, 150, 255))
        screen.blit(wave_surf, (sw // 2 - wave_surf.get_width() // 2, ty + 50))
        hint = font_medium.render("按空格或点击返回主菜单", True, WHITE)
    else:
        hint = font_medium.render("按空格或点击返回主菜单", True, WHITE)
    hx = sw // 2 - hint.get_width() // 2
    screen.blit(hint, (hx, ty + 80))


if __name__ == '__main__':
    main()
