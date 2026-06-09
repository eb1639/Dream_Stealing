"""
GameState — 全局游戏状态数据容器
"""
import random
from core.config import *
import core.config as _cfg
from world.map_data import *
from entities.entities import *


class GameState:
    def __init__(self):
        self.phase = PHASE_MENU
        self.mode = MODE_HUMAN
        self.difficulty = DIFF_EASY       # 当前难度等级
        self.is_endless = False           # 是否无尽模式
        self.endless_wave = 0             # 无尽模式当前波数
        self.endless_wave_timer = 0.0     # 无尽模式波次间隔计时器
        self.safe_timer = SAFE_TIME
        self.game_time = 0.0
        self.victory = False
        self.paused = False

        # 地图
        self.grid = None
        self.rooms = []
        self.map_type = MAP_TYPE_EASY
        self.map_config = None  # MapConfig 实例

        # 实体
        self.humans = []          # list[Human]
        self.player_human = None  # Human or None
        self.dream_hunter = None  # DreamHunter (兼容: 第一个猎梦者或玩家控制的猎梦者)
        self.dream_hunters = []   # list[DreamHunter] 所有猎梦者
        self.bullets = []         # list[Bullet]
        self.tongues = []         # list[Tongue] 蛤蟆舌头

        # 建筑索引: {(room_id, btype): Building} 或按房间查找
        self.buildings = []       # list[Building] 所有建筑
        # 快捷查找: {(col, row): Building}
        self.building_at = {}

        # AI房间预订(防止多人抢同一房, 与room_id解耦)
        self.reserved_room_ids = set()

        # 电力系统: 每房间独立电表 {room_id: float}
        self.room_power = {}
        # 屠龙刀 / 镜子 / 蛤蟆等一次性效果
        self.attack_count = 0   # 门被攻击总计数(全图)

        # 飘字特效（每局重置）
        self.damage_numbers = []
        self.gold_numbers = []
        self.heal_numbers = []

        # 屠龙刀斩击动画 (飞行/砍击/飞回三段, 与 update_sword_animations 配合)
        self.sword_animations = []

        # 维修台累积器（用 building uid 作 key，避免 id() 复用隐患）
        self._repair_accum = {}
        self._repair_disp_accum = {}
        self._repair_disp_timer = {}

        # 音频
        self.audio = None  # AudioManager 实例, 由 main.py 设置

        # UI 临时缓存（由 renderer / ui_hud 写入，main 读取）
        self.popup_menu = None
        self.avatar_rects = {}
        self.hunter_avatar_rect = None
        self.hunter_avatar_rects = {}  # 存储所有猎梦者头像rect, 用于点击切换镜头
        self._pause_btn_rect = None
        self._pause_menu_rects = None
        self._pause_menu_open = False

        # 渲染缓存（由 renderer 写入，input_router 读取）
        self._scale = 1.0
        self._game_area_x = 0
        self._game_area_y = HUD_HEIGHT

    # ─── 初始化 ───

    def init_game(self, mode, map_type=None, difficulty=DIFF_EASY, is_endless=False):
        self.phase = PHASE_INIT
        self.mode = mode
        self.difficulty = difficulty
        self.is_endless = is_endless
        self.endless_wave = 1 if is_endless else 0
        self.endless_wave_timer = 0.0
        self.safe_timer = SAFE_TIME
        self.game_time = 0.0
        self.victory = False
        self.paused = False
        self.bullets = []
        self.buildings = []
        self.building_at = {}
        self.player_human = None
        self.dream_hunter = None
        self.dream_hunters = []
        self.reserved_room_ids = set()

        # 雪地地图门滑动状态: {blue_pos: {'red': (c,r), 'phase': 0.0~1.0, 'active': True}}
        self.door_animations = {}
        # 雪地地图门对(由 build_map 加载, 用于快速查找)
        self.door_transitions = []

        # 重置飘字特效（防止上一局残留）
        self.damage_numbers = []
        self.gold_numbers = []
        self.heal_numbers = []
        # 重置屠龙刀动画
        self.sword_animations = []

        # 重置维修台累积器（防止上一局 door uid 残留）
        self._repair_accum = {}
        self._repair_disp_accum = {}
        self._repair_disp_timer = {}

        # 重置电力/全局状态
        self.room_power = {room.id: 0.0 for room in self.rooms}  # 在 build_map 后填充
        self.attack_count = 0

        # 重置 UI 临时缓存（防止旧菜单/旧按钮区域残留）
        self.popup_menu = None
        self.avatar_rects = {}
        self.hunter_avatar_rect = None
        self.hunter_avatar_rects = {}  # 存储所有猎梦者头像rect, 用于点击切换镜头
        self._pause_btn_rect = None
        self._pause_menu_rects = None
        self._pause_menu_open = False

        # 地图选择: 人类模式随机选地图, 猎梦者模式使用指定地图或随机
        if map_type is None:
            self.map_type = random.choice(MAP_TYPES)
        else:
            self.map_type = map_type

        # 生成地图
        self.grid, self.rooms, self.map_config = build_map(self.map_type)
        # 加载门滑动对(所有地图都支持门滑入动画)
        self.door_transitions = get_door_transitions(self.map_type)

        # 初始化电力(每房间一份)
        self.room_power = {room.id: 0.0 for room in self.rooms}

        # 出生点: 地图中央的走廊格
        spawn_col, spawn_row = get_spawn_point()
        if self.grid[spawn_row][spawn_col] != TILE_EMPTY:
            # 若中央格被占用, 顺延到最近的空地
            for d in range(1, max(_cfg.MAP_COLS, _cfg.MAP_ROWS)):
                for dc in range(-d, d + 1):
                    for dr in range(-d, d + 1):
                        nc, nr = spawn_col + dc, spawn_row + dr
                        if 0 <= nc < _cfg.MAP_COLS and 0 <= nr < _cfg.MAP_ROWS:
                            if self.grid[nr][nc] == TILE_EMPTY:
                                spawn_col, spawn_row = nc, nr
                                break
                    else:
                        continue
                    break
                else:
                    continue
                break

        # 创建人类
        self.humans = []
        colors = [PLAYER_COLOR] + AI_HUMAN_COLORS
        for i in range(6):
            is_player = (i == 0) if mode == MODE_HUMAN else False
            offset_c = random.randint(-2, 2)
            offset_r = random.randint(-2, 2)
            hc, hr = spawn_col + offset_c, spawn_row + offset_r
            # 确保出生在走廊(非房间、非墙)
            if not (0 <= hc < _cfg.MAP_COLS and 0 <= hr < _cfg.MAP_ROWS):
                hc, hr = spawn_col, spawn_row
            if self.grid[hr][hc] != TILE_EMPTY:
                hc, hr = spawn_col, spawn_row
            # 若中央格被占用或不是走廊，顺延到最近的空地
            if self.grid[hr][hc] not in (TILE_EMPTY, TILE_SPAWN, TILE_RED_CHANNEL):
                for d in range(1, max(_cfg.MAP_COLS, _cfg.MAP_ROWS)):
                    for dc in range(-d, d + 1):
                        for dr in range(-d, d + 1):
                            nc, nr = spawn_col + dc, spawn_row + dr
                            if 0 <= nc < _cfg.MAP_COLS and 0 <= nr < _cfg.MAP_ROWS:
                                if self.grid[nr][nc] in (TILE_EMPTY, TILE_SPAWN, TILE_RED_CHANNEL):
                                    hc, hr = nc, nr
                                    break
                        else:
                            continue
                        break
                    else:
                        continue
                    break
            human = Human(i, is_player, colors[i], hc, hr)
            self.humans.append(human)
            if is_player:
                self.player_human = human

        # 创建猎梦者(根据难度配置)
        self.dream_hunters = []

        # 猎梦者出生点(苔藓地图用四边缺口, 其他地图用中央)
        hunter_spawns = get_hunter_spawn_points(self.map_type)

        if mode == MODE_HUNTER:
            # 猎梦者模式: 单个猎梦者, 玩家控制, 随机种类
            hunter_type = random.choice([HUNTER_SUNNY, HUNTER_BIGHEAD, HUNTER_GRANDMA,
                                         HUNTER_BANDAGE, HUNTER_REDDRESS])
            # 随机选一个出生点
            spawn_c, spawn_r = random.choice(hunter_spawns)
            hunter = DreamHunter(0, True, spawn_c, spawn_r, hunter_type)
            hunter.spawn_pos = (spawn_c, spawn_r)
            self.dream_hunters = [hunter]
            self.dream_hunter = hunter
        else:
            # 人类模式: 根据难度配置创建猎梦者
            if is_endless:
                hunter_types_list = [HUNTER_BIGHEAD, HUNTER_GRANDMA, HUNTER_BANDAGE, HUNTER_REDDRESS]
                count = ENDLESS_START_COUNT + (self.endless_wave - 1) * ENDLESS_COUNT_PER_WAVE
            else:
                config = DIFF_HUNTER_CONFIG.get(difficulty, DIFF_HUNTER_CONFIG[DIFF_EASY])
                hunter_types_list, count = config

            for i in range(count):
                htype = random.choice(hunter_types_list)
                # 所有地图统一使用 4 个分散出生点(四边正中央"凸出走廊格")
                if hunter_spawns:
                    # 困难及以上难度: 每个出生点只分配一个猎梦者, 避免重叠
                    used_spawns = [h.spawn_pos for h in self.dream_hunters if h.spawn_pos is not None]
                    available_spawns = [sp for sp in hunter_spawns if sp not in used_spawns]
                    if available_spawns:
                        spawn_c, spawn_r = random.choice(available_spawns)
                    else:
                        # 所有出生点已占用, 回退到随机选择
                        spawn_c, spawn_r = random.choice(hunter_spawns)
                else:
                    # 兜底: 中央出生点附近
                    offset_c = random.randint(-2, 2)
                    offset_r = random.randint(-2, 2)
                    spawn_c = spawn_col + offset_c
                    spawn_r = spawn_row + offset_r
                hc, hr = spawn_c, spawn_r
                if not (0 <= hc < _cfg.MAP_COLS and 0 <= hr < _cfg.MAP_ROWS):
                    hc, hr = spawn_col, spawn_row
                # 若出生点非可通行格, 顺延到中央
                if self.grid[hr][hc] not in (TILE_EMPTY, TILE_SPAWN, TILE_RED_CHANNEL):
                    hc, hr = spawn_col, spawn_row
                if self.grid[hr][hc] not in (TILE_EMPTY, TILE_SPAWN, TILE_RED_CHANNEL):
                    # 中央格也不可走, 找最近空地
                    for d in range(1, max(_cfg.MAP_COLS, _cfg.MAP_ROWS)):
                        found = False
                        for dc in range(-d, d + 1):
                            for dr in range(-d, d + 1):
                                nc, nr = spawn_col + dc, spawn_row + dr
                                if 0 <= nc < _cfg.MAP_COLS and 0 <= nr < _cfg.MAP_ROWS:
                                    if self.grid[nr][nc] in (TILE_EMPTY, TILE_SPAWN, TILE_RED_CHANNEL):
                                        hc, hr = nc, nr
                                        found = True
                                        break
                            if found:
                                break
                        if found:
                            break
                hunter = DreamHunter(i, False, hc, hr, htype)
                hunter.spawn_pos = (hc, hr)
                self.dream_hunters.append(hunter)

            # 兼容: dream_hunter 指向第一个猎梦者
            self.dream_hunter = self.dream_hunters[0] if self.dream_hunters else None

        # 初始化房间建筑(门和床)
        for room in self.rooms:
            # 门
            dc, dr = room.door_pos
            door = Building(BLDG_DOOR, dc, dr, room.id)
            self.buildings.append(door)
            self.building_at[(dc, dr)] = door

            # 床: 优先使用地图配置中的bed位置, 否则随机放置
            bed_pos = None
            if room.bed_col is not None and room.bed_row is not None:
                bc, br = room.bed_col, room.bed_row
                # 确保bed位置在房间内且不是门
                if room.contains(bc, br) and (bc, br) != (dc, dr):
                    bed_pos = (bc, br)
                    bed = Building(BLDG_BED, bc, br, room.id)
                    self.buildings.append(bed)
                    self.building_at[(bc, br)] = bed
                    self.grid[br][bc] = TILE_BED

            if bed_pos is None:
                # 回退: 房间内部随机空位(排除门相邻)
                interior = list(room.cells)
                random.shuffle(interior)
                for bc, br in interior:
                    if (bc, br) == (dc, dr):
                        continue
                    if abs(bc - dc) + abs(br - dr) <= 1:
                        continue
                    bed_pos = (bc, br)
                    bed = Building(BLDG_BED, bc, br, room.id)
                    self.buildings.append(bed)
                    self.building_at[(bc, br)] = bed
                    self.grid[br][bc] = TILE_BED
                    break
                if bed_pos is None:
                    for bc, br in interior:
                        if (bc, br) != (dc, dr):
                            bed_pos = (bc, br)
                            bed = Building(BLDG_BED, bc, br, room.id)
                            self.buildings.append(bed)
                            self.building_at[(bc, br)] = bed
                            self.grid[br][bc] = TILE_BED
                            break

            # ── 房间初始化: 随机放置一个道具, 增加游戏趣味性 ──
            # 从"赚钱/特殊/基础"类道具中随机选一个, 不会放置门/床/炮塔/维修台
            self._spawn_random_room_item(room, bed_pos, door_pos=(dc, dr))

        # AI人类分配目标房间
        self._assign_ai_rooms()

        self.phase = PHASE_SAFE

    # 可在房间初始化时随机放置的道具(从菜单的赚钱/特殊/基础类中选, 不放门/床/炮塔/维修台)
    _RANDOM_ROOM_ITEM_POOL = [
        BLDG_GAMEMACHINE,   # 游戏机(基础)
        BLDG_MIRROR,        # 镜子(特殊赚钱)
        BLDG_GRASS_S,       # 一根小草(特殊)
        BLDG_GRASS_L,       # 一盆小草(特殊)
        BLDG_FROG,          # 蛤蟆(特殊)
        BLDG_BEAR_BED,      # 小熊睡床(特殊赚钱)
        BLDG_GARLIC,        # 大蒜(特殊)
    ]

    def _spawn_random_room_item(self, room, bed_pos=None, door_pos=None):
        """房间初始化时随机放置一个道具到空位"""
        # 候选空位: 房间内格子, 排除门/床/门相邻
        occupied = {(b.grid_col, b.grid_row) for b in self.buildings if b.room_id == room.id}
        candidates = []
        for c, r in room.cells:
            if (c, r) in occupied:
                continue
            if door_pos is not None and abs(c - door_pos[0]) + abs(r - door_pos[1]) <= 1:
                continue
            candidates.append((c, r))
        if not candidates:
            return
        # 随机选 1 个道具 + 1 个位置
        btype = random.choice(self._RANDOM_ROOM_ITEM_POOL)
        bc, br = random.choice(candidates)
        nb = Building(btype, bc, br, room.id)
        self.buildings.append(nb)
        self.building_at[(bc, br)] = nb

    def _assign_ai_rooms(self):
        """AI人类随机分配未占用的房间, 使用reserved_room_ids防止抢房"""
        available = [r for r in self.rooms if r.id not in self.reserved_room_ids]
        random.shuffle(available)
        for human in self.humans:
            if human.is_player and self.mode == MODE_HUMAN:
                continue
            if not available:
                break
            # 尝试分配直到找到可达的房间
            assigned = False
            for _ in range(len(available)):
                room = available.pop(0)
                bed = self.get_bed_in_room(room.id)
                if bed:
                    bc, br = bed.pos
                    path = find_path(self.grid, human.pos, (bc, br), 'human_wandering')
                    if path:
                        human.move_path = path
                        human.room_id = room.id
                        self.reserved_room_ids.add(room.id)
                        assigned = True
                        break
                    else:
                        # 不可达, 放回池中给其他人
                        available.append(room)
                else:
                    available.append(room)
            if not assigned:
                # 该AI未分配到房间, 后续_assign_room_to_ai兜底
                pass

    # ─── 查询 ───

    def get_bed_in_room(self, room_id):
        for b in self.buildings:
            if b.type == BLDG_BED and b.room_id == room_id:
                return b
        return None

    def get_door_in_room(self, room_id):
        for b in self.buildings:
            if b.type == BLDG_DOOR and b.room_id == room_id:
                return b
        return None

    def get_buildings_in_room(self, room_id):
        return [b for b in self.buildings if b.room_id == room_id]

    def get_turrets_in_room(self, room_id):
        return [b for b in self.buildings if b.type == BLDG_TURRET and b.room_id == room_id]

    def get_repairs_in_room(self, room_id):
        return [b for b in self.buildings if b.type == BLDG_REPAIR and b.room_id == room_id]

    def get_human_in_room(self, room_id):
        for h in self.humans:
            if h.room_id == room_id and h.alive and h.state == HUMAN_BED:
                return h
        return None

    def get_building_at(self, col, row):
        return self.building_at.get((col, row))

    def get_human_by_id(self, human_id):
        for h in self.humans:
            if h.id == human_id:
                return h
        return None

    def get_hunter_by_id(self, hunter_id):
        for h in self.dream_hunters:
            if h.id == hunter_id:
                return h
        return None

    def living_humans(self):
        return [h for h in self.humans if h.alive]

    def get_alive_ai_humans(self):
        return [h for h in self.humans if h.alive and not h.is_player]

    def get_unbroken_doors(self):
        return [b for b in self.buildings if b.type == BLDG_DOOR and b.current_hp > 0]

    def get_broken_doors(self):
        return [b for b in self.buildings if b.type == BLDG_DOOR and b.current_hp <= 0]

    def is_game_over(self):
        return self.phase in (PHASE_VICTORY, PHASE_DEFEAT)

    def is_room_door_broken(self, room_id):
        door = self.get_door_in_room(room_id)
        return door is not None and door.current_hp <= 0

    def get_room_of_door(self, door_building):
        return get_room_by_id(self.rooms, door_building.room_id)

    def any_human_alive(self):
        return any(h.alive for h in self.humans)

    def all_hunters_dead(self):
        """所有猎梦者是否已死亡"""
        return all(not h.alive for h in self.dream_hunters)

    def alive_hunters(self):
        """返回所有存活猎梦者"""
        return [h for h in self.dream_hunters if h.alive]
