"""
经济定时器、战斗检测、AI决策
"""
import random
import math
from core.config import *
import core.config as _cfg
from world.map_data import *
from entities.entities import *


# ─── 经济系统 ───

def update_economy(game_state, dt):
    """每帧经济更新: 游戏机产电, 床/矿/小熊/镜子产金币"""
    # 1. 游戏机产电
    for b in game_state.buildings:
        if b.type == BLDG_GAMEMACHINE and b.alive:
            if b.room_id in game_state.room_power:
                game_state.room_power[b.room_id] += b.power_per_sec * dt

    # 2. 床 / 矿 / 小熊睡床 / 镜子 产金币
    for b in game_state.buildings:
        gps = b.gold_per_sec
        # 小熊睡床: 基础1金币/秒, 每死1个队友产出*2(封顶32倍)
        if b.type == BLDG_BEAR_BED:
            dead_count = sum(1 for h in game_state.humans if not h.alive)
            multiplier = min(2 ** dead_count, BEAR_BED_MAX_BONUS)
            gps = BEAR_BED_GOLD_PER_SEC * multiplier
        if gps <= 0:
            continue
        # 镜子根据猎梦者距离动态调整产出(取最近猎梦者)
        if b.type == BLDG_MIRROR:
            min_dist = 999
            best_hunter = None
            for h in game_state.dream_hunters:
                if h.alive:
                    bpx, bpy = b.px_center
                    tile_dist = math.hypot(h.px - bpx, h.py - bpy) / TILE_SIZE
                    if tile_dist < min_dist:
                        min_dist = tile_dist
                        best_hunter = h
            if min_dist < 999:
                b.mirror_target_hunter = best_hunter
                # 灼热红光状态
                if b.mirror_burn_active:
                    gps = MIRROR_BURN_GOLD
                    # 对锁定的猎梦者造成伤害
                    if best_hunter and not best_hunter.shield_active:
                        best_hunter.take_damage(MIRROR_BURN_DAMAGE * dt)
                        best_hunter.add_damage(MIRROR_BURN_DAMAGE * dt)
                else:
                    gps = MIRROR_GOLD_NEAR if min_dist <= MIRROR_NEAR_DIST else MIRROR_GOLD_FAR
                    # 5%概率触发灼热红光(冷却结束后)
                    if b.mirror_burn_cooldown <= 0 and random.random() < MIRROR_BURN_CHANCE * dt:
                        b.mirror_burn_active = True
                        b.mirror_burn_timer = MIRROR_BURN_DURATION
                        _spawn_damage_number(game_state, b.grid_col, b.grid_row, "灼!")

            # 更新灼热红光计时器
            if b.mirror_burn_active:
                b.mirror_burn_timer -= dt
                if b.mirror_burn_timer <= 0:
                    b.mirror_burn_active = False
                    b.mirror_burn_cooldown = MIRROR_BURN_COOLDOWN
            elif b.mirror_burn_cooldown > 0:
                b.mirror_burn_cooldown -= dt
        # 产金币归属该房间的床上人类
        room_human = game_state.get_human_in_room(b.room_id)
        if room_human is not None and room_human.alive:
            room_human.gold += gps * dt


# ─── 战斗系统 ───

def update_combat(game_state, dt):
    """更新所有战斗逻辑(支持多猎梦者)"""
    # 遍历所有猎梦者
    for hunter in game_state.dream_hunters:
        if not hunter.alive:
            continue

        # 0. 出生点回血: 仅雪地地图(站在任意白色出生点格子上自动回血)
        # 回血速率与原泉水系统一致, 仅雪地地图有该机制
        if game_state.map_type == MAP_TYPE_SNOW:
            c, r = hunter.grid_col, hunter.grid_row
            if 0 <= c < _cfg.MAP_COLS and 0 <= r < _cfg.MAP_ROWS:
                if game_state.grid[r][c] == TILE_SPAWN and not hunter.is_full_hp:
                    heal_acc = getattr(hunter, '_spawn_heal_accum', 0.0) + HUNTER_SPAWN_HEAL_RATE * dt
                    if heal_acc >= 1.0:
                        heal_int = int(heal_acc)
                        hunter.heal(heal_int)
                        heal_acc -= heal_int
                        _spawn_heal_number(game_state, hunter.grid_col, hunter.grid_row - 1, f"+{heal_int}")
                    hunter._spawn_heal_accum = heal_acc

        # 1. 猎梦者攻击门
        if hunter.attack_cooldown > 0:
            hunter.attack_cooldown -= dt
        else:
            _hunter_attack_door(game_state, hunter)

        # 1b. 分身攻击门
        for clone in hunter.clones[:]:
            if not clone.alive:
                continue
            if clone.attack_cooldown > 0:
                clone.attack_cooldown -= dt
            else:
                _clone_attack_door(game_state, clone)

        # 4. 猎梦者状态计时器(绷带回血/狂暴/炮停/护盾/恐惧/定身)
        hunter.update_effects(dt)

    # 1c. 绷带猎梦者: 每秒飘出"+HP"文字
    for hunter in game_state.dream_hunters:
        if not hunter.alive or hunter.hunter_type != HUNTER_BANDAGE:
            continue
        if hasattr(hunter, '_bandage_heal_accum') and hunter._bandage_heal_accum >= 1.0:
            _spawn_heal_number(game_state, hunter.grid_col, hunter.grid_row - 1,
                               f"+{int(hunter._bandage_heal_accum)}")
            hunter._bandage_heal_accum = 0.0

    # 2. 炮塔攻击猎梦者(含分身)
    _turrets_attack(game_state, dt)

    # 3. 猎梦者触碰秒杀(走廊人类 / 破门后床上人类)
    for hunter in game_state.dream_hunters:
        if hunter.alive:
            _hunter_kill_check(game_state, hunter)
        for clone in hunter.clones:
            if clone.alive:
                _clone_kill_check(game_state, clone)

    # 5. 更新子弹
    _update_bullets(game_state, dt)

    # 5b. 更新舌头
    _update_tongues(game_state, dt)

    # 6. 维修台回血
    _update_repair(game_state, dt)

    # 7. 新工具效果更新（护盾/蒜/诱捕/断头台/蛤蟆/冰箱）
    update_buildings(game_state, dt)

    # 9. 分身生命周期管理
    for hunter in game_state.dream_hunters:
        if hunter.alive:
            _update_clones(game_state, dt, hunter)


def _get_corridor_pos_near_arrow(arrow_c, arrow_r, door_dir, grid):
    """获取箭头位置(red_pos)旁边走廊侧的格子
    door_dir 表示房间在门的哪一侧, 走廊在反方向"""
    from core.config import TILE_EMPTY, TILE_SPAWN
    # 走廊方向: 与 door_dir 相反
    if door_dir == 'right':    # 房间在右, 走廊在左
        candidates = [(arrow_c - 1, arrow_r), (arrow_c, arrow_r - 1), (arrow_c, arrow_r + 1)]
    elif door_dir == 'left':   # 房间在左, 走廊在右
        candidates = [(arrow_c + 1, arrow_r), (arrow_c, arrow_r - 1), (arrow_c, arrow_r + 1)]
    elif door_dir == 'up':     # 房间在上, 走廊在下
        candidates = [(arrow_c, arrow_r + 1), (arrow_c - 1, arrow_r), (arrow_c + 1, arrow_r)]
    else:  # down: 房间在下, 走廊在上
        candidates = [(arrow_c, arrow_r - 1), (arrow_c - 1, arrow_r), (arrow_c + 1, arrow_r)]
    for c, r in candidates:
        if 0 <= c < _cfg.MAP_COLS and 0 <= r < _cfg.MAP_ROWS:
            if grid[r][c] in (TILE_EMPTY, TILE_SPAWN):
                return (c, r)
    # 后备: 返回第一个有效坐标
    return candidates[0]


def _hunter_attack_door(game_state, hunter):
    """猎梦者攻击相邻的门"""
    hc, hr = hunter.pos

    # 定身或恐惧中: 不能攻击
    if hunter.is_stunned or hunter.is_feared:
        return

    # 检查四方向是否有门
    for nc, nr in get_neighbors(hc, hr):
        building = game_state.get_building_at(nc, nr)
        if building and building.type == BLDG_DOOR and building.current_hp > 0:
            # 攻击!
            damage = hunter.atk
            if not hunter.shield_active:
                # 触发门被攻击事件: 小草/一盆小草/能量罩/大蒜
                _on_door_attacked(game_state, building, hunter)
                building.take_damage(damage)
            leveled_up = hunter.add_damage(damage)
            hunter.attack_cooldown = 1.0 / max(0.1, hunter.atk_speed)

            # ── 种类技能触发 ──
            # 晴天娃娃: 攻击时随机触发狂暴
            if hunter.hunter_type == HUNTER_SUNNY and not hunter.berserk_active and hunter.berserk_cooldown <= 0:
                if random.random() < BERSERK_TRIGGER_CHANCE:
                    hunter.berserk_active = True
                    hunter.berserk_timer = BERSERK_DURATION

            # 大头: 撞门攻击触发狂暴
            if hunter.hunter_type == HUNTER_BIGHEAD and not hunter.berserk_active and hunter.berserk_cooldown <= 0:
                if random.random() < 0.08:  # 8%概率触发
                    hunter.berserk_active = True
                    hunter.berserk_timer = BERSERK_DURATION

            # 红裙小女孩: 攻击时随机触发炮停
            if hunter.hunter_type == HUNTER_REDDRESS and hunter.turret_disable_cooldown <= 0:
                if random.random() < TURRET_DISABLE_CHANCE:
                    hunter.turret_disable_timer = TURRET_DISABLE_DURATION
                    hunter.turret_disable_cooldown = TURRET_DISABLE_COOLDOWN

            # 孙婆婆: 升级时生成分身
            if leveled_up and hunter.hunter_type == HUNTER_GRANDMA:
                _spawn_clone(game_state, hunter)

            # 音效: 门被击打
            if game_state.audio:
                game_state.audio.play_sfx('door_hit')
            # 音效: 猎梦者升级
            if leveled_up and game_state.audio:
                game_state.audio.play_sfx('hunter_upgrade')

            # 标记门所在房间的人被攻击
            room_human = game_state.get_human_in_room(building.room_id)
            if room_human:
                room_human.is_under_attack = True

            # 播放伤害特效标记
            if not hunter.shield_active:
                _spawn_damage_number(game_state, nc, nr, damage)
            break


def _on_door_attacked(game_state, door_building, hunter):
    """门被攻击时触发: 小草奖励 / 能量罩激活检测 / 大蒜激活检测"""
    game_state.attack_count += 1
    room_id = door_building.room_id
    room_human = game_state.get_human_in_room(room_id)

    for b in game_state.buildings:
        if b.room_id != room_id:
            continue
        if b.type == BLDG_GRASS_S:
            reward = GRASS_S_GOLD_PER_HIT
            if room_human and room_human.alive:
                room_human.gold += reward
            spawn_gold_number(game_state, b.grid_col, b.grid_row, reward)
        elif b.type == BLDG_GRASS_L:
            b.attack_count += 1
            bonus = min(b.attack_count - 1, 5) * GRASS_L_STACK_BONUS
            reward = GRASS_L_BASE_GOLD_PER_HIT + bonus
            if room_human and room_human.alive:
                room_human.gold += reward
            spawn_gold_number(game_state, b.grid_col, b.grid_row, reward)
        elif b.type == BLDG_SHIELD:
            if (door_building.current_hp < door_building.max_hp * SHIELD_THRESHOLD
                    and b.cooldown_timer <= 0 and not hunter.shield_active):
                _activate_shield(game_state, b)
        elif b.type == BLDG_GARLIC:
            if (door_building.current_hp < door_building.max_hp * GARLIC_THRESHOLD
                    and b.cooldown_timer <= 0 and not hunter.is_feared):
                _activate_garlic(game_state, b, hunter)


def _turrets_attack(game_state, dt):
    """所有炮塔攻击范围内的猎梦者(含分身, 支持多猎梦者)"""
    # 收集所有存活猎梦者
    alive_hunters = [h for h in game_state.dream_hunters if h.alive]
    if not alive_hunters:
        return

    # 炮停技能: 任一猎梦者炮停激活则所有炮台停止
    any_turret_disabled = any(h.turret_disabled for h in alive_hunters)
    if any_turret_disabled:
        return

    # 收集所有可攻击目标: 所有存活猎梦者 + 存活分身
    targets = []
    for hunter in alive_hunters:
        targets.append(hunter)
        for clone in hunter.clones:
            if clone.alive:
                targets.append(clone)

    for turret in game_state.buildings:
        if turret.type != BLDG_TURRET:
            continue
        # 冷却
        turret._cooldown -= dt
        if turret._cooldown > 0:
            continue

        tc, tr = turret.pos
        # 找射程内的目标
        best_target = None
        best_dist = 999
        for target in targets:
            # 分身正常受炮塔攻击(击杀分身可阻止合体攻击力加成)
            hc, hr = target.pos
            dist = math.hypot(hc - tc, hr - tr)
            if dist <= turret.turret_range and dist < best_dist:
                if _can_turret_hit_hunter(game_state, target, turret):
                    best_target = target
                    best_dist = dist

        if best_target is not None:
            turret._cooldown = 1.0 / turret.turret_atk_speed
            tpx, tpy = turret.px_center
            bullet = Bullet(tpx, tpy, best_target, turret.turret_dps, from_turret_uid=turret.uid)
            bullet.spawn_time = game_state.game_time  # 记录开火时间
            game_state.bullets.append(bullet)
            if game_state.audio:
                game_state.audio.play_sfx('turret_fire')


def _can_turret_hit_hunter(game_state, hunter, turret):
    """炮塔能否打到猎梦者: 猎梦者在走廊或在破门的房间内"""
    hc, hr = hunter.pos
    tile = game_state.grid[hr][hc]
    if tile == TILE_EMPTY or tile == TILE_RED_CHANNEL:
        return True  # 走廊/红格(等同走廊)
    if tile == TILE_ROOM:
        # 检查该房间门是否已破
        room = get_room_at(game_state.rooms, hc, hr)
        if room and game_state.is_room_door_broken(room.id):
            return True
    return False


def _hunter_kill_check(game_state, hunter):
    """猎梦者触碰人类=秒杀"""
    hc, hr = hunter.pos

    for human in game_state.humans:
        if not human.alive:
            continue
        # 检查是否同格或相邻
        if abs(human.grid_col - hc) <= 1 and abs(human.grid_row - hr) <= 1:
            if human.state == HUMAN_WANDERING:
                # 走廊上触碰秒杀
                human.kill()
                if game_state.audio:
                    game_state.audio.play_sfx('human_death')
            elif human.state == HUMAN_BED:
                # 检查门是否已破
                if human.room_id is not None:
                    if game_state.is_room_door_broken(human.room_id):
                        # 门破且猎梦者在房间内
                        room = get_room_at(game_state.rooms, hc, hr)
                        if room and room.id == human.room_id:
                            human.kill()
                            if game_state.audio:
                                game_state.audio.play_sfx('human_death')


def _update_bullets(game_state, dt):
    """更新子弹位置, 处理命中"""
    for bullet in game_state.bullets[:]:
        hit = bullet.update(dt)
        if hit:
            target = bullet.target
            if isinstance(target, HunterClone):
                target.take_damage(bullet.damage)
                if not target.alive:
                    _spawn_damage_number(game_state, target.grid_col, target.grid_row, "灭!")
            else:
                target.take_damage(bullet.damage)
            game_state.bullets.remove(bullet)
            if game_state.audio:
                game_state.audio.play_sfx('bullet_hit')
        elif not bullet.alive:
            game_state.bullets.remove(bullet)


def _update_tongues(game_state, dt):
    """更新舌头位置，处理命中和返回"""
    for tongue in game_state.tongues[:]:
        hit = tongue.update(dt)
        if hit:
            if tongue.hit and not tongue.returning:
                # 刚命中，造成伤害
                target = tongue.target
                if not target.shield_active:
                    target.take_damage(tongue.damage)
                    target.add_damage(tongue.damage)
                    _spawn_damage_number(game_state, target.grid_col, target.grid_row, tongue.damage)
            if not tongue.alive:
                # 返回完成，移除
                game_state.tongues.remove(tongue)
        elif not tongue.alive:
            game_state.tongues.remove(tongue)


def _update_repair(game_state, dt):
    """维修台回血: 门血量不满时持续维修, 按等级计算回血量"""
    for human in game_state.humans:
        if not human.alive or human.state != HUMAN_BED or human.room_id is None:
            continue
        door = game_state.get_door_in_room(human.room_id)
        if door is None or door.current_hp <= 0:
            continue
        if door.current_hp >= door.max_hp:
            for d in (game_state._repair_accum, game_state._repair_disp_accum, game_state._repair_disp_timer):
                d.pop(door.uid, None)
            continue
        repairs = game_state.get_repairs_in_room(human.room_id)
        if not repairs:
            continue
        total_heal = 0.0
        for repair in repairs:
            total_heal += repair.repair_hps * dt
        door_key = door.uid  # 使用稳定 uid，避免 id() 复用
        # HP累积(不丢失小数)
        acc = game_state._repair_accum.get(door_key, 0.0) + total_heal
        if acc >= 1.0:
            heal_int = int(acc)
            door.repair(heal_int)
            door.being_repaired = True
            acc -= heal_int
        game_state._repair_accum[door_key] = acc
        # 每秒飘字汇总
        disp_acc = game_state._repair_disp_accum.get(door_key, 0.0) + total_heal
        disp_timer = game_state._repair_disp_timer.get(door_key, 0.0) + dt
        if disp_timer >= 1.0:
            if disp_acc >= 1.0:
                _spawn_heal_number(game_state, door.grid_col, door.grid_row, int(disp_acc))
            disp_acc = 0.0
            disp_timer -= 1.0
        game_state._repair_disp_accum[door_key] = disp_acc
        game_state._repair_disp_timer[door_key] = disp_timer


def _spawn_damage_number(game_state, col, row, damage):
    """记录伤害数字(由effects.py渲染)"""
    if not hasattr(game_state, 'damage_numbers'):
        game_state.damage_numbers = []
    game_state.damage_numbers.append({
        'col': col, 'row': row,
        'value': damage,
        'timer': 1.0,
        'color': RED,
    })


def _spawn_heal_number(game_state, col, row, amount):
    """记录回血数字(由effects.py渲染)"""
    if not hasattr(game_state, 'heal_numbers'):
        game_state.heal_numbers = []
    game_state.heal_numbers.append({
        'col': col, 'row': row,
        'value': f'+{amount}',
        'timer': 1.0,
        'color': GREEN,
    })


def spawn_gold_number(game_state, col, row, amount):
    """记录金币飘字"""
    if not hasattr(game_state, 'gold_numbers'):
        game_state.gold_numbers = []
    game_state.gold_numbers.append({
        'col': col, 'row': row,
        'value': f'+{amount}',
        'timer': 1.0,
        'color': YELLOW,
    })


# ─── 新工具效果系统 ───

def _activate_shield(game_state, shield_building):
    """激活能量罩: 3 秒内门无敌"""
    hunter = game_state.dream_hunter
    hunter.shield_active = True
    hunter.shield_timer = SHIELD_DURATION
    shield_building.cooldown_timer = SHIELD_COOLDOWN
    _spawn_heal_number(game_state, shield_building.grid_col, shield_building.grid_row - 1, "盾!")


def _activate_garlic(game_state, garlic_building, hunter):
    """激活大蒜: 猎梦者恐惧 2 秒"""
    hunter.fear_timer = GARLIC_FEAR_DURATION
    garlic_building.cooldown_timer = GARLIC_COOLDOWN
    _spawn_heal_number(game_state, garlic_building.grid_col, garlic_building.grid_row - 1, "蒜!")


def _activate_trap(game_state, trap_building, hunter):
    """激活诱捕网: 猎梦者定身 2 秒"""
    hunter.stunned_timer = TRAP_DURATION
    trap_building.cooldown_timer = TRAP_COOLDOWN
    _spawn_damage_number(game_state, trap_building.grid_col, trap_building.grid_row, "网!")


def _activate_guillotine(game_state, guillotine_building, hunter):
    """激活断头台: 造成 10% 最大 HP 伤害"""
    damage = int(hunter.max_hp * GUILLOTINE_DAMAGE_RATIO)
    hunter.take_damage(damage)
    hunter.add_damage(damage)
    guillotine_building.cooldown_timer = GUILLOTINE_COOLDOWN
    _spawn_damage_number(game_state, guillotine_building.grid_col, guillotine_building.grid_row, damage)


def _try_frog_attack(game_state, frog_building, hunter):
    """蛤蟆: 远程舌攻 - 发射舌头追踪猎梦者"""
    if frog_building.cooldown_timer > 0:
        return
    fpx, fpy = frog_building.px_center
    dist = math.hypot(hunter.px - fpx, hunter.py - fpy)
    if dist > FROG_RANGE * TILE_SIZE:
        return
    damage = int(FROG_DPS * 1.0)  # DPS * 1秒
    # 创建舌头投射物
    tongue = Tongue(fpx, fpy, hunter, damage)
    game_state.tongues.append(tongue)
    # 更新蛤蟆朝向
    frog_building.facing_angle = math.atan2(hunter.py - fpy, hunter.px - fpx)
    frog_building.cooldown_timer = FROG_COOLDOWN


def update_buildings(game_state, dt):
    """每帧更新所有新工具的效果: 护盾/大蒜/诱捕/断头台/蛤蟆/冰箱 + 通用冷却
    支持多猎梦者: 效果对每个猎梦者独立计算"""
    alive_hunters = [h for h in game_state.dream_hunters if h.alive]
    if not alive_hunters:
        return

    # 1. 更新所有建筑的冷却倒计时
    for b in game_state.buildings:
        if b.cooldown_timer > 0:
            b.cooldown_timer = max(0.0, b.cooldown_timer - dt)

    # 2. 冰箱攻速减速 (对每个猎梦者独立计算)
    for hunter in alive_hunters:
        hunter.atk_speed_mult = 1.0
        for b in game_state.buildings:
            if b.type == BLDG_FRIDGE and b.alive:
                bpx, bpy = b.px_center
                dist = math.hypot(hunter.px - bpx, hunter.py - bpy) / TILE_SIZE
                if dist <= 10:
                    hunter.atk_speed_mult = min(hunter.atk_speed_mult, 1.0 - FRIDGE_ATK_SLOW)

    # 对每个猎梦者触发攻击性道具
    for hunter in alive_hunters:
        # 3. 诱捕网: 猎梦者 HP < 30% 时自动触发
        if hunter.current_hp < hunter.max_hp * TRAP_PROC_HP_RATIO:
            for b in game_state.buildings:
                if b.type == BLDG_TRAP and b.cooldown_timer <= 0 and not hunter.is_stunned:
                    _activate_trap(game_state, b, hunter)
                    break

        # 4. 断头台: 猎梦者 HP < 20% 时自动斩
        if hunter.current_hp < hunter.max_hp * GUILLOTINE_THRESHOLD and not hunter.shield_active:
            for b in game_state.buildings:
                if b.type == BLDG_GUILLOTINE and b.cooldown_timer <= 0:
                    _activate_guillotine(game_state, b, hunter)
                    break

        # 5. 蛤蟆: 远程攻击
        if hunter.alive and not hunter.shield_active:
            for b in game_state.buildings:
                if b.type == BLDG_FROG and b.alive:
                    _try_frog_attack(game_state, b, hunter)


def cast_dragon_sword(game_state):
    """玩家手动激活屠龙刀（按 'F' 键）: 对正在攻击玩家门的猎梦者造成 20% 最大 HP 伤害
    无距离限制，优先攻击正在攻击玩家所在房间门的猎梦者"""
    player = game_state.player_human
    if not player or not player.alive or player.room_id is None:
        return False

    # 找正在攻击玩家房间门的猎梦者
    attacking_hunter = None
    for hunter in game_state.dream_hunters:
        if not hunter.alive:
            continue
        if hunter.target_room_id == player.room_id:
            attacking_hunter = hunter
            break

    # 如果没有正在攻击玩家门的猎梦者，找最近的
    if attacking_hunter is None:
        best_dist = 999
        for hunter in game_state.dream_hunters:
            if not hunter.alive:
                continue
            if player.room_id is not None:
                door = game_state.get_door_in_room(player.room_id)
                if door:
                    dist = math.hypot(hunter.px - door.px_center[0], hunter.py - door.px_center[1]) / TILE_SIZE
                    if dist < best_dist:
                        best_dist = dist
                        attacking_hunter = hunter

    if attacking_hunter is None:
        return False

    # 找任意一个可用的屠龙刀（无距离限制）
    best_sword = None
    for b in game_state.buildings:
        if b.type != BLDG_SWORD:
            continue
        if b.cooldown_timer > 0:
            continue
        best_sword = b
        break

    if best_sword is None:
        return False

    damage = int(attacking_hunter.max_hp * SWORD_DAMAGE_RATIO)
    if not attacking_hunter.shield_active:
        attacking_hunter.take_damage(damage)
        attacking_hunter.add_damage(damage)
        # 伤害数字在刀砍下的瞬间生成(随动画一起)
    best_sword.cooldown_timer = SWORD_COOLDOWN
    # 音效: 屠龙刀斩击
    if game_state.audio:
        game_state.audio.play_sfx('dragon_sword')

    # 注册斩击动画: 飞向→砍击→飞回
    # 用 id() 区分同一建筑(因为屠龙刀是按建筑计, 没有 uid 字段)
    sword_id = id(best_sword)
    # 清理该刀的旧动画(防止连续触发时叠加)
    game_state.sword_animations = [a for a in game_state.sword_animations if a['sword_id'] != sword_id]
    game_state.sword_animations.append({
        'sword_id': sword_id,
        'sword_grid_pos': (best_sword.grid_col, best_sword.grid_row),  # 原位(飞回用)
        'hunter_grid_pos': (attacking_hunter.grid_col, attacking_hunter.grid_row),  # 目标(砍下用)
        'hunter_px': (attacking_hunter.px, attacking_hunter.py),  # 实时像素位置
        'phase': 'fly',  # fly / slash / return
        'elapsed': 0.0,
        'damage': damage,
        'damage_spawned': False,  # 砍击瞬间只生成一次伤害数字
        'sword_pixel': None,  # 当前帧像素位置(由 update 计算)
        'slash_angle': 0.0,  # 砍击角度(随时间从 0→90 度)
    })
    return True



def update_ai(game_state, dt):
    """更新所有AI决策"""
    # AI人类决策
    for human in game_state.humans:
        if not human.alive or human.is_player:
            continue
        if human.state != HUMAN_BED:
            continue
        human.decision_timer -= dt
        if human.decision_timer <= 0:
            _ai_human_decide(game_state, human)
            human.decision_timer = random.uniform(AI_DECISION_MIN, AI_DECISION_MAX)

    # AI猎梦者决策(人类模式: 所有AI猎梦者各自决策)
    if game_state.mode == MODE_HUMAN:
        for hunter in game_state.dream_hunters:
            if hunter.alive and not hunter.is_player:
                _ai_hunter_decide(game_state, hunter)


def _ai_human_decide(game_state, human):
    """AI人类决策: 模拟真人玩家, 多样化购买行为
    优先级:
        1. 升级床(优先) > 升级门(门等级 < 床等级)
        2. 防御核心: 炮塔(1-3座) > 维修台(有炮塔后)
        3. 经济: 游戏机(供能) > 矿坑(无电可缓建)
        4. 高科技/黑科技(条件允许): 能量罩 / 冰箱 / 诱捕网 / 断头台
        5. 特殊赚钱: 镜子 / 小草 / 一盆小草 / 大蒜 / 蛤蟆 / 屠龙刀
        6. 升级炮塔
    """
    room_id = human.room_id
    if room_id is None:
        return

    bed = game_state.get_bed_in_room(room_id)
    door = game_state.get_door_in_room(room_id)
    turrets = game_state.get_turrets_in_room(room_id)
    repairs = game_state.get_repairs_in_room(room_id)
    room = get_room_by_id(game_state.rooms, room_id)
    if room is None:
        return

    # 房间空位(排除建筑和床)
    occupied = set()
    for b in game_state.get_buildings_in_room(room_id):
        occupied.add(b.pos)
    empty_tiles = [(c, r) for c, r in room.interior if (c, r) not in occupied]
    if not empty_tiles:
        return  # 房间已满, 仅做升级决策

    def _place(btype, cost_g, cost_p=0):
        """在空地建造建筑, 扣资源, 返回是否成功"""
        nonlocal empty_tiles
        if not empty_tiles or human.gold < cost_g:
            return False
        # 电力门槛: 房间电表不足则跳过
        if cost_p > 0 and game_state.room_power.get(room_id, 0) < cost_p:
            return False
        tc, tr = random.choice(empty_tiles)
        human.gold -= cost_g
        if cost_p > 0:
            game_state.room_power[room_id] -= cost_p
        nb = Building(btype, tc, tr, room_id)
        game_state.buildings.append(nb)
        game_state.building_at[(tc, tr)] = nb
        empty_tiles.remove((tc, tr))
        return True

    # 1. 升级床(优先)
    if bed and bed.can_upgrade():
        cost = bed.upgrade_cost()
        if human.gold >= cost:
            human.gold -= cost
            bed.upgrade()

    # 2. 升级门(门等级 < 床等级)
    if door and door.can_upgrade() and bed:
        if door.level < bed.level:
            cost = door.upgrade_cost()
            if human.gold >= cost:
                human.gold -= cost
                door.upgrade()

    # 3. 防御核心: 炮塔(1~3座)
    turret_cost = TURRET_UPGRADE_COST[0]
    if empty_tiles and len(turrets) < 3 and human.gold >= turret_cost:
        _place(BLDG_TURRET, turret_cost)

    # 4. 维修台(炮塔存在后建)
    if empty_tiles and len(repairs) < 2 and human.gold >= REPAIR_COST and turrets:
        _place(BLDG_REPAIR, REPAIR_COST)

    # 5. 经济: 游戏机(供能)
    if empty_tiles and human.gold >= GAMEMACHINE_COST[0]:
        gm_count = sum(1 for b in game_state.buildings
                       if b.type == BLDG_GAMEMACHINE and b.room_id == room_id)
        if gm_count < 2:  # 房间最多2台
            _place(BLDG_GAMEMACHINE, GAMEMACHINE_COST[0])

    # 6. 矿坑(若已建游戏机/有电, 只会建铜矿, 升级为银/金/钻石矿通过点击升级菜单)
    power_ok = game_state.room_power.get(room_id, 0) > 0
    mine_choices = []
    for mb, cg, cp in [
        (BLDG_MINE_COPPER, MINE_COST_GOLD[0], MINE_COST_POWER[0]),
    ]:
        existing = sum(1 for b in game_state.buildings
                       if b.type in MINE_TYPES and b.room_id == room_id)
        if existing < 1 and power_ok and human.gold >= cg and game_state.room_power.get(room_id, 0) >= cp:
            mine_choices.append((mb, cg, cp))
    if mine_choices and empty_tiles and random.random() < 0.5:
        mb, cg, cp = random.choice(mine_choices)
        _place(mb, cg, cp)

    # 7. 高科技/黑科技(中后期, 仅在有一定资源时)
    if empty_tiles and human.gold >= 80:
        power = game_state.room_power.get(room_id, 0)
        # 7a. 冰箱(80金+30电, 减速)
        if (power >= FRIDGE_COST_POWER and human.gold >= FRIDGE_COST_GOLD
                and not any(b.type == BLDG_FRIDGE and b.room_id == room_id
                            for b in game_state.buildings)):
            _place(BLDG_FRIDGE, FRIDGE_COST_GOLD, FRIDGE_COST_POWER)
        # 7b. 能量罩(100金+40电, 门血低时护盾)
        elif (power >= SHIELD_COST_POWER and human.gold >= SHIELD_COST_GOLD
                and not any(b.type == BLDG_SHIELD and b.room_id == room_id
                            for b in game_state.buildings)):
            _place(BLDG_SHIELD, SHIELD_COST_GOLD, SHIELD_COST_POWER)
        # 7c. 诱捕网(150金+60电, 猎梦者逃跑时定身)
        elif (power >= TRAP_COST_POWER and human.gold >= TRAP_COST_GOLD
                and not any(b.type == BLDG_TRAP and b.room_id == room_id
                            for b in game_state.buildings)):
            _place(BLDG_TRAP, TRAP_COST_GOLD, TRAP_COST_POWER)
        # 7d. 断头台(400金+200电, 猎梦者低血时直接斩)
        elif (power >= GUILLOTINE_COST_POWER and human.gold >= GUILLOTINE_COST_GOLD
                and not any(b.type == BLDG_GUILLOTINE and b.room_id == room_id
                            for b in game_state.buildings)):
            _place(BLDG_GUILLOTINE, GUILLOTINE_COST_GOLD, GUILLOTINE_COST_POWER)

    # 8. 特殊道具(随机选择, 模拟真人玩家偏好)
    if empty_tiles:
        # 8a. 镜子(60金, 持续赚钱)
        if human.gold >= MIRROR_COST and random.random() < 0.4:
            _place(BLDG_MIRROR, MIRROR_COST)
        # 8b. 小草(30金, 每次被攻击1金币)
        elif human.gold >= GRASS_S_COST and random.random() < 0.5:
            _place(BLDG_GRASS_S, GRASS_S_COST)
        # 8c. 一盆小草(80金, 攻击叠加)
        elif human.gold >= GRASS_L_COST and random.random() < 0.4:
            _place(BLDG_GRASS_L, GRASS_L_COST)
        # 8d. 大蒜(80金, 门血低时熏走猎梦者)
        elif human.gold >= GARLIC_COST and random.random() < 0.35:
            _place(BLDG_GARLIC, GARLIC_COST)
        # 8e. 蛤蟆(50金, 远距舌攻)
        elif human.gold >= FROG_COST and random.random() < 0.45:
            _place(BLDG_FROG, FROG_COST)
        # 8f. 小熊睡床(120金, 队友死时翻倍产钱)
        elif human.gold >= BEAR_BED_COST and random.random() < 0.3:
            _place(BLDG_BEAR_BED, BEAR_BED_COST)
        # 8g. 屠龙刀(200金, 按F一刀20%血, 高端玩家偏好)
        elif human.gold >= SWORD_COST and random.random() < 0.2:
            _place(BLDG_SWORD, SWORD_COST)

    # 9. 升级炮塔(等级不超过床等级)
    for turret in turrets:
        if turret.can_upgrade() and bed and turret.level < bed.level:
            cost = turret.upgrade_cost()
            if human.gold >= cost:
                human.gold -= cost
                turret.upgrade()


def _ai_hunter_decide(game_state, hunter):
    """AI猎梦者决策: 选最低等级门攻击, 破门后追击人类"""
    if hunter is None or not hunter.alive:
        return

    door_hp_map = {(b.grid_col, b.grid_row): b.current_hp
                   for b in game_state.buildings if b.type == BLDG_DOOR}

    # ── 门已破, 进入房间追击人类 ──
    if hunter.target_room_id is not None:
        door = game_state.get_door_in_room(hunter.target_room_id)
        room_human = game_state.get_human_in_room(hunter.target_room_id)
        if door is not None and door.current_hp <= 0 and room_human is not None:
            # 寻找人类附近可通行的房间格子
            target_pos = _find_hunt_target_in_room(game_state, hunter.target_room_id, room_human)
            if target_pos is not None:
                # 已在目标位置附近(相邻即可触发kill_check)
                if abs(hunter.grid_col - room_human.grid_col) <= 1 and abs(hunter.grid_row - room_human.grid_row) <= 1:
                    hunter.move_path = []
                    return
                # 已有路径则继续走
                if hunter.move_path:
                    return
                path = find_path(game_state.grid, hunter.pos, target_pos, 'hunter',
                                 door_hp_map, game_state.rooms)
                if path:
                    hunter.move_path = path
                return

    # ── 检查当前目标门是否仍然有效 ──
    need_new_target = True
    current_target_door = None
    if hunter.target_room_id is not None:
        door = game_state.get_door_in_room(hunter.target_room_id)
        if door is not None and door.current_hp > 0:
            need_new_target = False
            current_target_door = door

    # 选择新目标: 优先攻击有活人入住的房间, 选门等级最低的
    # 大头猎梦者: 优先弱门+避开炮台
    if need_new_target:
        # 筛选有活人入住的房间
        occupied_ids = set()
        for h in game_state.humans:
            if h.alive and h.state == HUMAN_BED and h.room_id is not None:
                occupied_ids.add(h.room_id)

        unbroken = [b for b in game_state.buildings
                    if b.type == BLDG_DOOR and b.current_hp > 0
                    and b.room_id in occupied_ids]
        if not unbroken:
            # 无已入住房间(极少情况), 追击走廊游荡人类
            wandering = [h for h in game_state.humans
                        if h.alive and h.state == HUMAN_WANDERING]
            if wandering:
                target_human = min(wandering,
                    key=lambda h: heuristic(hunter.pos, h.pos))
                path = find_path(game_state.grid, hunter.pos,
                               target_human.pos, 'hunter',
                               door_hp_map, game_state.rooms)
                if path:
                    hunter.move_path = path
                hunter.target_room_id = None
            else:
                hunter.move_path = []
                hunter.target_room_id = None
            return

        if hunter.hunter_type == HUNTER_BIGHEAD:
            # 大头策略: 优先攻击门等级最低的, 避开有炮台的房间
            # 按门等级排序, 优先低等级门
            unbroken.sort(key=lambda b: b.level)
            # 尝试找没有炮台的目标
            no_turret_doors = []
            for door in unbroken:
                turrets_in_room = game_state.get_turrets_in_room(door.room_id)
                if not turrets_in_room:
                    no_turret_doors.append(door)
            # 优先选无炮台房间中门等级最低的
            if no_turret_doors:
                min_level = min(b.level for b in no_turret_doors)
                candidates = [b for b in no_turret_doors if b.level == min_level]
            else:
                # 所有房间都有炮台, 选门等级最低的
                min_level = min(b.level for b in unbroken)
                candidates = [b for b in unbroken if b.level == min_level]
            current_target_door = random.choice(candidates)
        else:
            # 普通AI: 选门等级最低的
            min_level = min(b.level for b in unbroken)
            candidates = [b for b in unbroken if b.level == min_level]
            current_target_door = random.choice(candidates)
        hunter.target_room_id = current_target_door.room_id
        hunter.move_path = []

    # ── 寻路到门前(走廊侧) ──
    if current_target_door is None:
        return
    room = get_room_by_id(game_state.rooms, current_target_door.room_id)
    if room is None:
        return

    # 门关闭后已滑到箭头位置(red_pos), 猎梦者需要走到 red_pos 旁边的走廊格
    if current_target_door.is_door_closed and room.door_arrow_col is not None:
        # 门在箭头位置, 计算箭头位置旁边的走廊格
        arrow_c, arrow_r = room.door_arrow_col, room.door_arrow_row
        # 箭头位置就是 red_pos, 走廊侧在箭头的反方向(远离房间的方向)
        # door_dir 表示房间在门的哪一侧, 所以走廊在反方向
        corridor_pos = _get_corridor_pos_near_arrow(arrow_c, arrow_r, room.door_dir, game_state.grid)
    else:
        corridor_pos = get_door_adjacent_corridor(room, game_state.grid)

    # 已经在攻击位置
    if hunter.pos == corridor_pos or hunter.pos == current_target_door.pos:
        hunter.move_path = []
        return

    if hunter.move_path:
        return

    path = find_path(game_state.grid, hunter.pos, corridor_pos, 'hunter',
                     door_hp_map, game_state.rooms)
    if path:
        hunter.move_path = path
    else:
        hunter.target_room_id = None
        hunter.move_path = []


def _find_hunt_target_in_room(game_state, room_id, room_human):
    """在已破门房间内找猎梦者可通行的格子(靠近人类)"""
    room = get_room_by_id(game_state.rooms, room_id)
    if room is None:
        return None
    hc, hr = room_human.pos
    # 遍历房间内部, 找离人类最近的可通行格
    best = None
    best_dist = 999
    for c, r in room.interior:
        if is_walkable_for(game_state.grid, c, r, 'hunter', None, game_state.rooms):
            d = abs(c - hc) + abs(r - hr)
            if d < best_dist:
                best_dist = d
                best = (c, r)
    return best


# ─── 胜负判定 ───

def update_endless_wave(game_state, dt):
    """无尽模式: 当前波所有猎梦者死亡后进入下一波"""
    if not game_state.is_endless or game_state.phase != PHASE_PLAYING:
        return

    if not game_state.all_hunters_dead():
        return

    # 当前波已清, 进入下一波
    game_state.endless_wave += 1
    from core.save_data import update_endless_best_wave
    update_endless_best_wave(game_state.endless_wave - 1)

    # 生成新一波猎梦者(在中央出生点附近)
    spawn_c, spawn_r = get_spawn_point()
    if game_state.grid[spawn_r][spawn_c] != TILE_EMPTY:
        for d in range(1, max(_cfg.MAP_COLS, _cfg.MAP_ROWS)):
            found = False
            for dc in range(-d, d + 1):
                for dr in range(-d, d + 1):
                    nc, nr = spawn_c + dc, spawn_r + dr
                    if 0 <= nc < _cfg.MAP_COLS and 0 <= nr < _cfg.MAP_ROWS:
                        if game_state.grid[nr][nc] == TILE_EMPTY:
                            spawn_c, spawn_r = nc, nr
                            found = True
                            break
                if found:
                    break
            if found:
                break

    hunter_types_list = [HUNTER_BIGHEAD, HUNTER_GRANDMA, HUNTER_BANDAGE, HUNTER_REDDRESS]
    count = ENDLESS_START_COUNT + (game_state.endless_wave - 1) * ENDLESS_COUNT_PER_WAVE
    # 属性倍率随波次递增
    stat_mult = 1.0 + (game_state.endless_wave - 1) * ENDLESS_STAT_MULT_PER_WAVE

    game_state.dream_hunters = []
    for i in range(count):
        htype = random.choice(hunter_types_list)
        offset_c = random.randint(-2, 2)
        offset_r = random.randint(-2, 2)
        hc = spawn_c + offset_c
        hr = spawn_r + offset_r
        if not (0 <= hc < _cfg.MAP_COLS and 0 <= hr < _cfg.MAP_ROWS):
            hc, hr = spawn_c, spawn_r
        if game_state.grid[hr][hc] != TILE_EMPTY:
            hc, hr = spawn_c, spawn_r
        hunter = DreamHunter(len(game_state.dream_hunters), False, hc, hr, htype)
        hunter.spawn_pos = (spawn_c, spawn_r)
        # 无尽模式属性倍率
        hunter._endless_stat_mult = stat_mult
        game_state.dream_hunters.append(hunter)

    game_state.dream_hunter = game_state.dream_hunters[0] if game_state.dream_hunters else None

def check_win_lose(game_state):
    """仅在PLAYING阶段判定"""
    if game_state.phase != PHASE_PLAYING:
        return

    if game_state.mode == MODE_HUMAN:
        # 玩家死亡 → 失败
        player = game_state.player_human
        if player and not player.alive:
            game_state.phase = PHASE_DEFEAT
            game_state.victory = False
            return
        # 无尽模式: 不判定胜利(由update_endless_wave处理波次)
        if game_state.is_endless:
            return
        # 所有猎梦者死亡 → 胜利
        if game_state.all_hunters_dead():
            game_state.phase = PHASE_VICTORY
            game_state.victory = True
            return

    elif game_state.mode == MODE_HUNTER:
        # 所有人类死亡 → 胜利
        if not game_state.any_human_alive():
            game_state.phase = PHASE_VICTORY
            game_state.victory = True
            return
        # 猎梦者死亡 → 失败
        if game_state.dream_hunter and not game_state.dream_hunter.alive:
            game_state.phase = PHASE_DEFEAT
            game_state.victory = False
            return


# ─── 实体移动更新 ───

def update_movement(game_state, dt):
    """更新所有可移动实体的位置"""
    # 人类移动
    for human in game_state.humans:
        if not human.alive:
            continue
        if human.state != HUMAN_WANDERING:
            continue
        if not human.move_path:
            continue
        move_along_path(human, human.speed, dt)
        # 每帧检测门开关(包括站在门旁边的情况)
        _check_door_transition(human)

    # 所有猎梦者移动
    for hunter in game_state.dream_hunters:
        if hunter and hunter.alive and hunter.move_path:
            move_along_path(hunter, hunter.speed_val, dt)

    # 每帧检查所有wandering人类门开关(包括站在门旁边没有移动的情况)
    for human in game_state.humans:
        if not human.alive:
            continue
        if human.state != HUMAN_WANDERING:
            continue
        _check_door_transition(human)

    # 检查AI人类是否到达床(兜底: 处理PLAYING阶段仍在移动的AI)
    for human in game_state.humans:
        if not human.alive or human.is_player:
            continue
        if human.state != HUMAN_WANDERING:
            continue
        bc, br = human.pos
        building = game_state.get_building_at(bc, br)
        if building and building.type == BLDG_BED:
            room_human = game_state.get_human_in_room(building.room_id)
            if room_human is None:
                human.set_bed(building.room_id, bc, br)
                game_state.reserved_room_ids.add(building.room_id)


def move_along_path(entity, speed, dt):
    """沿路径平滑移动实体"""
    if not entity.move_path:
        return
    # 计算目标像素位置
    target_col, target_row = entity.move_path[0]
    target_px = target_col * TILE_SIZE + TILE_SIZE // 2
    target_py = target_row * TILE_SIZE + TILE_SIZE // 2
    entity.target_px = target_px
    entity.target_py = target_py

    # 当前像素位置
    dx = target_px - entity.px
    dy = target_py - entity.py
    dist = math.hypot(dx, dy)

    if dist < 2:
        # 到达该节点
        entity.px = target_px
        entity.py = target_py
        entity.grid_col = target_col
        entity.grid_row = target_row
        entity.move_path.pop(0)
        # 雪地地图: 踏入红格触发门滑入动画
        _check_door_transition(entity)
    else:
        move = speed * dt
        if move >= dist:
            entity.px = target_px
            entity.py = target_py
            entity.grid_col = target_col
            entity.grid_row = target_row
            entity.move_path.pop(0)
            _check_door_transition(entity)
        else:
            entity.px += dx / dist * move
            entity.py += dy / dist * move


def _check_door_transition(entity):
    """所有地图: 检测门开关触发
    - 人类踏入红格(TILE_RED_CHANNEL) → 关门(蓝格→红格滑动)
    - 人类靠近已关闭的门(4方向相邻TILE_DOOR) → 开门(红格→蓝格滑动)
    此函数在 entity 网格位置更新后调用"""
    from core.config import TILE_RED_CHANNEL, TILE_DOOR, TILE_WALL
    if not hasattr(entity, 'state'):
        return
    gs = _current_game_state_ref[0]
    if gs is None:
        return
    c, r = entity.grid_col, entity.grid_row
    if not (0 <= c < _cfg.MAP_COLS and 0 <= r < _cfg.MAP_ROWS):
        return

    tile = gs.grid[r][c]

    # 情况1: 踏入红格(门未关闭) → 关门
    if tile == TILE_RED_CHANNEL:
        _trigger_door_close(gs, c, r)

    # 开门需要玩家按空格键(在 main.py 中处理), 不再自动触发


def _check_adjacent_closed_doors(gs, col, row, entity):
    """检查人类4方向相邻位置是否有已关闭的门, 有则触发开门
    只处理"已关闭"的门(门在 red_pos 位置); 初始状态门在 blue_pos 时跳过"""
    from core.config import TILE_DOOR
    for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nc, nr = col + dc, row + dr
        if 0 <= nc < _cfg.MAP_COLS and 0 <= nr < _cfg.MAP_ROWS:
            tile_at = gs.grid[nr][nc]
            if tile_at == TILE_DOOR:
                # 仅当该 TILE_DOOR 位置匹配某门对的 red_pos(即门已滑入并关闭)时
                # 才触发开门动画; 初始状态门在 blue_pos, 不算"已关闭"
                is_closed_here = any(rp == (nc, nr)
                                     for _bp, rp, _ddir in gs.door_transitions)
                if is_closed_here:
                    _trigger_door_open(gs, nc, nr, entity)
                    return  # 一次只开一扇门


def _trigger_door_close(gs, red_c, red_r):
    """触发门关闭动画(蓝格→红格滑动)
    蓝格立即变为墙(门正在离开), 红格等动画完成再变"""
    from core.config import TILE_WALL
    # 查找门对: red == (red_c, red_r)
    for blue_pos, red_pos, ddir in gs.door_transitions:
        if red_pos != (red_c, red_r):
            continue
        # 检查是否有活跃的关门动画(防止重复触发)
        if blue_pos in gs.door_animations:
            anim = gs.door_animations[blue_pos]
            if anim.get('direction') == 'close' and anim['phase'] < 1.0:
                return  # 关门动画正在进行中
            # 动画已完成或为开门动画, 可以触发新的关门
        # 蓝格立即变为墙(门正在离开原位)
        bc, br = blue_pos
        gs.grid[br][bc] = TILE_WALL
        # 红格等动画完成再变(在 update_door_animations 中处理)
        # 记录动画
        gs.door_animations[blue_pos] = {
            'red': red_pos,
            'phase': 0.0,
            'active': True,
            'direction': 'close',  # 关门动画
        }
        break


def _trigger_door_open(gs, door_c, door_r, entity=None):
    """触发门打开动画(红格→蓝格滑动)
    只有当门已关闭(位于箭头位置)时才触发
    grid变更推迟到动画完成时执行, 保证视觉与逻辑一致"""
    from core.config import TILE_DOOR, TILE_RED_CHANNEL

    # 查找门建筑 (不要求 is_door_closed=True, 因为可能动画完成后没更新)
    target_door = None
    for b in gs.buildings:
        if b.type == BLDG_DOOR and b.grid_col == door_c and b.grid_row == door_r:
            target_door = b
            break

    if target_door is None:
        return  # 关门动画未完成, 建筑尚未到位

    # 查找对应的door_transition来找到blue_pos
    blue_pos = None
    red_pos = None
    for bp, rp, ddir in gs.door_transitions:
        if rp == (door_c, door_r):
            blue_pos = bp
            red_pos = rp
            break

    if blue_pos is None:
        return

    # 检查是否已有开门动画
    for anim_key, anim in gs.door_animations.items():
        if anim.get('red') == red_pos and anim.get('direction') == 'open':
            return  # 开门动画已在进行中

    # 检查是否有正在进行的关门动画(同一对门), 避免冲突
    for anim_key, anim in gs.door_animations.items():
        if (anim.get('red') == red_pos and anim.get('direction') == 'close'
                and anim['phase'] < 1.0):
            return  # 等关门动画完成

    # 不立即修改grid, 推迟到动画完成时再改

    # 记录开门动画(使用red_pos作为key, 因为门现在在箭头位置)
    gs.door_animations[red_pos] = {
        'blue': blue_pos,
        'phase': 0.0,
        'active': True,
        'direction': 'open',  # 开门动画
    }


# 全局引用, 用于 _check_door_transition 获取 game_state
_current_game_state_ref = [None]


def set_current_game_state(game_state):
    """设置 _check_door_transition 使用的 game_state 引用"""
    _current_game_state_ref[0] = game_state


def update_sword_animations(game_state, dt):
    """推进屠龙刀斩击动画 (fly / slash / return 三段)
    同步计算刀当前帧的像素位置 + 砍击角度, 由 renderer 直接读取"""
    from core.config import (SWORD_ANIM_FLY_DURATION, SWORD_ANIM_SLASH_DURATION,
                              SWORD_ANIM_RETURN_DURATION, TILE_SIZE)
    if not game_state.sword_animations:
        return
    finished = []
    for anim in game_state.sword_animations:
        anim['elapsed'] += dt
        # 实时跟踪猎梦者位置(动画过程中猎梦者可能还在移动)
        sword_id = anim['sword_id']
        # 用当前猎梦者位置(如还活着); 否则用记录的位置
        hunter_px = anim['hunter_px']
        for h in game_state.dream_hunters:
            if (h.grid_col, h.grid_row) == anim['hunter_grid_pos'] and h.alive:
                hunter_px = (h.px, h.py)
                anim['hunter_px'] = hunter_px
                break
        sword_gx, sword_gy = anim['sword_grid_pos']
        sword_px = (sword_gx * TILE_SIZE + TILE_SIZE // 2,
                    sword_gy * TILE_SIZE + TILE_SIZE // 2)
        fly_t = SWORD_ANIM_FLY_DURATION
        slash_t = SWORD_ANIM_SLASH_DURATION
        return_t = SWORD_ANIM_RETURN_DURATION

        if anim['phase'] == 'fly':
            # 0 ~ fly_t: 从刀位置直线飞向猎梦者
            t = min(1.0, anim['elapsed'] / fly_t)
            # ease-out 让刀快到时减速
            eased_t = 1.0 - (1.0 - t) * (1.0 - t)
            cur_x = sword_px[0] + (hunter_px[0] - sword_px[0]) * eased_t
            cur_y = sword_px[1] + (hunter_px[1] - sword_px[1]) * eased_t
            anim['sword_pixel'] = (cur_x, cur_y)
            anim['slash_angle'] = -45.0  # 飞行时剑尖指向前方(右上倾斜)
            if t >= 1.0:
                anim['phase'] = 'slash'
                anim['elapsed'] = 0.0
                # 砍击瞬间: 生成伤害数字(在猎梦者头顶)
                if not anim['damage_spawned'] and anim['damage'] > 0:
                    _spawn_damage_number(game_state, anim['hunter_grid_pos'][0],
                                          anim['hunter_grid_pos'][1] - 1,
                                          anim['damage'])
                    anim['damage_spawned'] = True

        elif anim['phase'] == 'slash':
            # 0 ~ slash_t: 在猎梦者头顶做下砍动作(角度从 -90 → 0)
            t = min(1.0, anim['elapsed'] / slash_t)
            anim['sword_pixel'] = hunter_px
            anim['slash_angle'] = -90.0 + 90.0 * t  # -90°(举剑)→ 0°(平砍)
            if t >= 1.0:
                anim['phase'] = 'return'
                anim['elapsed'] = 0.0

        elif anim['phase'] == 'return':
            # 0 ~ return_t: 从猎梦者飞回刀原位
            t = min(1.0, anim['elapsed'] / return_t)
            eased_t = t * t  # ease-in 慢慢加速
            cur_x = hunter_px[0] + (sword_px[0] - hunter_px[0]) * eased_t
            cur_y = hunter_px[1] + (sword_px[1] - hunter_px[1]) * eased_t
            anim['sword_pixel'] = (cur_x, cur_y)
            anim['slash_angle'] = 0.0  # 飞回时平放
            if t >= 1.0:
                finished.append(anim)

    for anim in finished:
        try:
            game_state.sword_animations.remove(anim)
        except ValueError:
            pass


def update_door_animations(game_state, dt):
    """更新门滑入/滑出动画进度
    动画完成时才修改grid和建筑位置, 保证视觉与逻辑一致"""
    from core.config import TILE_DOOR, TILE_WALL, TILE_RED_CHANNEL
    if not game_state.door_animations:
        return
    finished = []
    for anim_key, anim in game_state.door_animations.items():
        anim['phase'] += dt / SNOW_DOOR_SLIDE_DURATION
        if anim['phase'] >= 1.0:
            anim['phase'] = 1.0
            anim['active'] = False
            finished.append(anim_key)
    
    for anim_key in finished:
        anim = game_state.door_animations[anim_key]
        anim['phase'] = 1.0
        anim['active'] = False
        
        direction = anim.get('direction', 'close')
        
        if direction == 'close':
            # 关门动画完成(蓝格→红格): 蓝格已是WALL, 只需改红格+移动建筑
            red_pos = anim['red']
            blue_pos = anim_key
            rc, rr = red_pos
            game_state.grid[rr][rc] = TILE_DOOR
            for b in game_state.buildings:
                if b.type == BLDG_DOOR and (b.grid_col, b.grid_row) == blue_pos:
                    old_pos = (b.grid_col, b.grid_row)
                    b.grid_col = red_pos[0]
                    b.grid_row = red_pos[1]
                    game_state.building_at.pop(old_pos, None)
                    game_state.building_at[red_pos] = b
                    b.is_door_closed = True
                    break
        
        elif direction == 'open':
            # 开门动画完成(红格→蓝格): 现在才修改grid和建筑位置
            blue_pos = anim['blue']
            red_pos = anim_key
            bc, br = blue_pos
            rc, rr = red_pos
            game_state.grid[rr][rc] = TILE_RED_CHANNEL
            game_state.grid[br][bc] = TILE_DOOR
            for b in game_state.buildings:
                if b.type == BLDG_DOOR and (b.grid_col, b.grid_row) == red_pos:
                    old_pos = (b.grid_col, b.grid_row)
                    b.grid_col = blue_pos[0]
                    b.grid_row = blue_pos[1]
                    game_state.building_at.pop(old_pos, None)
                    game_state.building_at[blue_pos] = b
                    b.is_door_closed = False
                    break

    # 清理已完成的动画(防止长时间游戏内存累积)
    for anim_key in finished:
        game_state.door_animations.pop(anim_key, None)


# ─── 玩家输入移动 ───

def move_entity_by_input(entity, dx, dy, grid, door_hp_map=None,
                         entity_type='human_wandering', rooms=None):
    """尝试将实体向(dx,dy)方向移动一格"""
    new_col = entity.grid_col + dx
    new_row = entity.grid_row + dy
    if is_walkable_for(grid, new_col, new_row, entity_type, door_hp_map, rooms):
        entity.grid_col = new_col
        entity.grid_row = new_row
        entity.px = new_col * TILE_SIZE + TILE_SIZE // 2
        entity.py = new_row * TILE_SIZE + TILE_SIZE // 2
        entity.move_path = []
        # 雪地地图: 踏入红格触发门滑入
        _check_door_transition(entity)
        return True
    return False


# ─── 分身系统(孙婆婆) ───

def _spawn_clone(game_state, hunter):
    """孙婆婆升级时生成分身"""
    # 在猎梦者周围找可通行格子
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1)]:
        nc, nr = hunter.grid_col + dx, hunter.grid_row + dy
        if 0 <= nc < _cfg.MAP_COLS and 0 <= nr < _cfg.MAP_ROWS:
            tile = game_state.grid[nr][nc]
            if tile in (TILE_EMPTY, TILE_DOOR, TILE_RED_CHANNEL):
                clone = HunterClone(hunter, nc, nr)
                hunter.clones.append(clone)
                return
    # 找不到合适位置, 在本体位置生成
    clone = HunterClone(hunter, hunter.grid_col, hunter.grid_row)
    hunter.clones.append(clone)


def _update_clones(game_state, dt, hunter):
    """更新分身: 移动/AI/生命周期/合体"""
    if not hunter.clones:
        return

    door_hp_map = {(b.grid_col, b.grid_row): b.current_hp
                   for b in game_state.buildings if b.type == BLDG_DOOR}

    for clone in hunter.clones[:]:
        if not clone.alive:
            # 分身死亡, 移除
            hunter.clones.remove(clone)
            continue

        # 生命周期倒计时
        clone.lifetime -= dt
        if clone.lifetime <= 0:
            # 超时后寻找主体合体: 永久攻击力加成
            hunter.clone_merge_atk_bonus += CLONE_MERGE_ATK_BONUS
            _spawn_damage_number(game_state, hunter.grid_col, hunter.grid_row, "合!")
            hunter.clones.remove(clone)
            continue

        # 分身剩余时间<3秒时，寻路向主体靠拢准备合体
        if clone.lifetime < 3.0:
            if not clone.move_path or clone.pos != clone.move_path[0]:
                path = find_path(game_state.grid, clone.pos, hunter.pos, 'hunter',
                               door_hp_map, game_state.rooms)
                if path:
                    clone.move_path = path
            continue

        # 分身移动(跟随本体的目标或独立寻路)
        if clone.move_path:
            move_along_path(clone, clone.speed, dt)
        else:
            # 分身AI: 寻路到本体目标门附近
            if hunter.target_room_id is not None:
                door = game_state.get_door_in_room(hunter.target_room_id)
                if door and door.current_hp > 0:
                    room = get_room_by_id(game_state.rooms, door.room_id)
                    if room:
                        if door.is_door_closed and room.door_arrow_col is not None:
                            corridor_pos = _get_corridor_pos_near_arrow(
                                room.door_arrow_col, room.door_arrow_row,
                                room.door_dir, game_state.grid)
                        else:
                            corridor_pos = get_door_adjacent_corridor(room, game_state.grid)
                        # 在本体附近找偏移位置
                        offset_pos = _find_clone_position(game_state, clone, corridor_pos)
                        if offset_pos:
                            path = find_path(game_state.grid, clone.pos, offset_pos, 'hunter',
                                           door_hp_map, game_state.rooms)
                            if path:
                                clone.move_path = path
            elif hunter.move_path:
                # 跟随本体
                target = hunter.move_path[-1] if hunter.move_path else hunter.pos
                offset_pos = _find_clone_position(game_state, clone, target)
                if offset_pos:
                    path = find_path(game_state.grid, clone.pos, offset_pos, 'hunter',
                                   door_hp_map, game_state.rooms)
                    if path:
                        clone.move_path = path


def _find_clone_position(game_state, clone, target_pos):
    """为分身找目标附近的可通行格子(避免和本体重叠)"""
    tc, tr = target_pos
    for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, 1)]:
        nc, nr = tc + dx, tr + dy
        if 0 <= nc < _cfg.MAP_COLS and 0 <= nr < _cfg.MAP_ROWS:
            tile = game_state.grid[nr][nc]
            if tile in (TILE_EMPTY, TILE_DOOR, TILE_RED_CHANNEL):
                return (nc, nr)
    return target_pos


def _clone_attack_door(game_state, clone):
    """分身攻击相邻的门"""
    if not clone.alive:
        return
    cc, cr = clone.pos
    for nc, nr in get_neighbors(cc, cr):
        building = game_state.get_building_at(nc, nr)
        if building and building.type == BLDG_DOOR and building.current_hp > 0:
            damage = clone.atk
            building.take_damage(damage)
            clone.attack_cooldown = 1.0 / max(0.1, clone.atk_speed)
            _spawn_damage_number(game_state, nc, nr, damage)
            break


def _clone_kill_check(game_state, clone):
    """分身触碰人类=秒杀"""
    if not clone.alive:
        return
    cc, cr = clone.pos
    for human in game_state.humans:
        if not human.alive:
            continue
        if abs(human.grid_col - cc) <= 1 and abs(human.grid_row - cr) <= 1:
            if human.state == HUMAN_WANDERING:
                human.kill()
                if game_state.audio:
                    game_state.audio.play_sfx('human_death')
            elif human.state == HUMAN_BED:
                if human.room_id is not None:
                    if game_state.is_room_door_broken(human.room_id):
                        room = get_room_at(game_state.rooms, cc, cr)
                        if room and room.id == human.room_id:
                            human.kill()
                            if game_state.audio:
                                game_state.audio.play_sfx('human_death')
