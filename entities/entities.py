"""
人类、猎梦者、建筑数据类
"""
import math
from core.config import *


# ═══════════════════════════════════════
#  人类
# ═══════════════════════════════════════

class Human:
    def __init__(self, human_id, is_player, color, grid_col, grid_row):
        self.id = human_id
        self.is_player = is_player
        self.color = color
        self.gold = HUMAN_INIT_GOLD
        self.state = HUMAN_WANDERING
        self.room_id = None

        # 网格位置
        self.grid_col = grid_col
        self.grid_row = grid_row
        # 像素位置(用于平滑移动)
        self.px = grid_col * TILE_SIZE + TILE_SIZE // 2
        self.py = grid_row * TILE_SIZE + TILE_SIZE // 2
        self.target_px = self.px
        self.target_py = self.py

        self.speed = HUMAN_SPEED * TILE_SIZE  # px/秒
        self.move_path = []  # 寻路路径
        self.move_timer = 0.0  # 移动间隔计时器
        self.decision_timer = 2.0  # AI决策计时器(初始短一些)
        self.is_under_attack = False

    @property
    def pos(self):
        return self.grid_col, self.grid_row

    @property
    def alive(self):
        return self.state != HUMAN_DEAD

    def kill(self):
        self.state = HUMAN_DEAD

    def set_bed(self, room_id, grid_col, grid_row):
        self.state = HUMAN_BED
        self.room_id = room_id
        self.grid_col = grid_col
        self.grid_row = grid_row
        self.px = grid_col * TILE_SIZE + TILE_SIZE // 2
        self.py = row_y = grid_row * TILE_SIZE + TILE_SIZE // 2


# ═══════════════════════════════════════
#  猎梦者
# ═══════════════════════════════════════

class DreamHunter:
    def __init__(self, hunter_id, is_player, grid_col, grid_row, hunter_type=HUNTER_SUNNY):
        self.id = hunter_id
        self.is_player = is_player
        self.hunter_type = hunter_type  # 猎梦者种类
        self.level = 0  # 索引0 = Lv1
        self.cumulative_damage = 0  # 累计造成伤害
        self._endless_stat_mult = 1.0  # 无尽模式属性倍率
        self.current_hp = self.max_hp  # 使用property(含种类倍率)
        self.attack_cooldown = 0.0

        self.grid_col = grid_col
        self.grid_row = grid_row
        self.px = grid_col * TILE_SIZE + TILE_SIZE // 2
        self.py = grid_row * TILE_SIZE + TILE_SIZE // 2
        self.target_px = self.px
        self.target_py = self.py

        self.speed = HUNTER_SPEED[0] * TILE_SIZE
        self.move_path = []
        self.move_timer = 0.0
        self.target_room_id = None

        # 效果状态
        self.shield_active = False       # 能量罩激活中
        self.shield_timer = 0.0          # 能量罩剩余时间
        self.stunned_timer = 0.0         # 定身剩余时间（诱捕）
        self.fear_timer = 0.0            # 恐惧剩余时间（大蒜）
        self.atk_speed_mult = 1.0        # 攻速乘数（冰箱/其他减速效果）

        # ── 种类技能状态 ──
        # 狂暴(晴天娃娃/大头)
        self.berserk_timer = 0.0         # 狂暴剩余时间
        self.berserk_cooldown = 0.0      # 狂暴冷却剩余时间
        self.berserk_active = False      # 当前是否狂暴中

        # 分身(孙婆婆)
        self.clones = []                 # list[HunterClone]
        self.clone_merge_atk_bonus = 0   # 合体后永久额外攻击力

        # 炮停(红裙小女孩)
        self.turret_disable_timer = 0.0  # 炮停剩余时间
        self.turret_disable_cooldown = 0.0  # 炮停冷却剩余时间

        # 绷带回血
        self.bandage_healing = False     # 是否正在自动回血

        # 泉水出生点(用于自动回血判定)
        self.spawn_pos = None            # (col, row) 猎梦者出生点

    @property
    def hp_mult(self):
        return HUNTER_TYPE_MULT[self.hunter_type][0]

    @property
    def atk_mult(self):
        base = HUNTER_TYPE_MULT[self.hunter_type][1]
        # 合体永久攻击力加成
        if self.clone_merge_atk_bonus > 0:
            base += self.clone_merge_atk_bonus / max(1, HUNTER_ATK[self.level])
        return base

    @property
    def max_hp(self):
        return int(HUNTER_MAX_HP[self.level] * self.hp_mult * self._endless_stat_mult)

    @property
    def atk(self):
        # 等级加成: 每级额外+5%攻击力
        level_bonus = 1.0 + self.level * 0.05
        base_atk = HUNTER_ATK[self.level] * self.atk_mult * self._endless_stat_mult * level_bonus
        # 狂暴加成
        if self.berserk_active:
            base_atk *= BERSERK_ATK_MULT
        return int(base_atk)

    @property
    def atk_speed(self):
        # 等级加成: 每级额外+5%攻速
        level_bonus = 1.0 + self.level * 0.05
        base = HUNTER_ATK_SPEED[self.level] * self.atk_speed_mult * level_bonus
        # 狂暴加成
        if self.berserk_active:
            base *= BERSERK_SPEED_MULT
        return base

    @property
    def speed_val(self):
        return HUNTER_SPEED[self.level] * TILE_SIZE

    @property
    def pos(self):
        return self.grid_col, self.grid_row

    @property
    def alive(self):
        return self.current_hp > 0

    @property
    def turret_disabled(self):
        """红裙小女孩炮停技能是否激活"""
        return self.turret_disable_timer > 0

    def add_damage(self, amount):
        """造成伤害, 返回是否升级"""
        self.cumulative_damage += amount
        for i in range(self.level + 1, len(HUNTER_THRESHOLDS)):
            if self.cumulative_damage >= HUNTER_THRESHOLDS[i]:
                self.level = i
                self.current_hp = self.max_hp  # 升级回满血
                self.speed = HUNTER_SPEED[self.level] * TILE_SIZE
                return True
        return False

    def take_damage(self, amount):
        # 能量罩激活中: 不扣血
        if self.shield_active:
            return
        self.current_hp -= amount
        if self.current_hp < 0:
            self.current_hp = 0

    def heal(self, amount):
        self.current_hp = min(self.current_hp + amount, self.max_hp)

    @property
    def is_full_hp(self):
        return self.current_hp >= self.max_hp

    @property
    def is_stunned(self):
        return self.stunned_timer > 0

    @property
    def is_feared(self):
        return self.fear_timer > 0

    def update_effects(self, dt):
        """更新各种状态效果计时器"""
        if self.shield_timer > 0:
            self.shield_timer -= dt
            if self.shield_timer <= 0:
                self.shield_timer = 0
                self.shield_active = False
        if self.stunned_timer > 0:
            self.stunned_timer -= dt
            if self.stunned_timer < 0:
                self.stunned_timer = 0
        if self.fear_timer > 0:
            self.fear_timer -= dt
            if self.fear_timer < 0:
                self.fear_timer = 0

        # 狂暴计时
        if self.berserk_active:
            self.berserk_timer -= dt
            if self.berserk_timer <= 0:
                self.berserk_timer = 0
                self.berserk_active = False
                self.berserk_cooldown = BERSERK_COOLDOWN
        elif self.berserk_cooldown > 0:
            self.berserk_cooldown -= dt
            if self.berserk_cooldown < 0:
                self.berserk_cooldown = 0

        # 炮停计时
        if self.turret_disable_timer > 0:
            self.turret_disable_timer -= dt
            if self.turret_disable_timer < 0:
                self.turret_disable_timer = 0
        elif self.turret_disable_cooldown > 0:
            self.turret_disable_cooldown -= dt
            if self.turret_disable_cooldown < 0:
                self.turret_disable_cooldown = 0

        # 绷带自动回血(累积治疗量, 用于"+HP"飘字)
        if self.hunter_type == HUNTER_BANDAGE and self.alive:
            if self.current_hp < self.max_hp * BANDAGE_HEAL_TRIGGER:
                self.bandage_healing = True
                heal_amount = int(BANDAGE_HEAL_RATE * dt)
                if heal_amount > 0:
                    self.heal(heal_amount)
                    # 累积每秒回血量用于显示飘字
                    if not hasattr(self, '_bandage_heal_accum'):
                        self._bandage_heal_accum = 0.0
                    self._bandage_heal_accum += heal_amount
                if self.current_hp >= self.max_hp * BANDAGE_HEAL_STOP:
                    self.bandage_healing = False
            else:
                self.bandage_healing = False


# ═══════════════════════════════════════
#  猎梦者分身(孙婆婆)
# ═══════════════════════════════════════

class HunterClone:
    """孙婆婆猎梦者的分身: 独立寻路, 可被攻击消灭, 超时自动合体"""
    def __init__(self, owner, grid_col, grid_row):
        self.owner = owner              # 所属本体
        self.grid_col = grid_col
        self.grid_row = grid_row
        self.px = grid_col * TILE_SIZE + TILE_SIZE // 2
        self.py = grid_row * TILE_SIZE + TILE_SIZE // 2
        self.target_px = self.px
        self.target_py = self.py
        self.speed = owner.speed_val
        self.move_path = []
        self.move_timer = 0.0
        self.attack_cooldown = 0.0
        self.target_room_id = None
        self.lifetime = CLONE_LIFETIME  # 存活时间
        self.alive = True
        self._current_hp = self.max_hp  # 初始化血量

    @property
    def max_hp(self):
        return int(self.owner.max_hp * CLONE_HP_RATIO)

    @property
    def current_hp(self):
        return self._current_hp

    @current_hp.setter
    def current_hp(self, value):
        self._current_hp = max(0, min(value, self.max_hp))

    @property
    def atk(self):
        return int(self.owner.atk * CLONE_ATK_RATIO)

    @property
    def atk_speed(self):
        return self.owner.atk_speed * 0.8  # 分身攻速略低

    @property
    def pos(self):
        return self.grid_col, self.grid_row

    def take_damage(self, amount):
        self._current_hp -= amount
        if self._current_hp <= 0:
            self._current_hp = 0
            self.alive = False

    def heal(self, amount):
        self._current_hp = min(self._current_hp + amount, self.max_hp)


# ═══════════════════════════════════════
#  子弹
# ═══════════════════════════════════════

class Bullet:
    def __init__(self, px, py, target_hunter, damage, from_turret_uid=None):
        self.px = float(px)
        self.py = float(py)
        self.target = target_hunter
        self.damage = damage
        self.speed = BULLET_SPEED
        self.alive = True
        self.from_turret_uid = from_turret_uid  # 标识从哪个炮塔发射
        self.spawn_time = 0.0                   # 生成时间(用于开火动画)

    def update(self, dt):
        """移动子弹, 到达目标时返回True"""
        tx = self.target.px
        ty = self.target.py
        dx = tx - self.px
        dy = ty - self.py
        dist = math.hypot(dx, dy)
        if dist < 8:
            self.alive = False
            return True  # 命中
        move = self.speed * dt
        if move >= dist:
            self.px = tx
            self.py = ty
            self.alive = False
            return True
        self.px += dx / dist * move
        self.py += dy / dist * move
        return False


# ═══════════════════════════════════════
#  蛤蟆舌头
# ═══════════════════════════════════════

class Tongue:
    """蛤蟆舌头: 从蛤蟆位置射出，触碰到猎梦者后造成伤害并返回"""
    def __init__(self, px, py, target_hunter, damage):
        self.px = float(px)
        self.py = float(py)
        self.start_px = self.px
        self.start_py = self.py
        self.target = target_hunter
        self.damage = damage
        self.speed = BULLET_SPEED * 1.5  # 舌头比子弹快
        self.alive = True
        self.returning = False  # 是否正在返回
        self.hit = False  # 是否已命中

    def update(self, dt):
        if self.returning:
            # 返回蛤蟆
            dx = self.start_px - self.px
            dy = self.start_py - self.py
            dist = math.hypot(dx, dy)
            if dist < 8:
                self.alive = False
                return True
            move = self.speed * dt
            if move >= dist:
                self.px = self.start_px
                self.py = self.start_py
                self.alive = False
                return True
            self.px += dx / dist * move
            self.py += dy / dist * move
            return False
        else:
            # 飞向目标
            tx = self.target.px
            ty = self.target.py
            dx = tx - self.px
            dy = ty - self.py
            dist = math.hypot(dx, dy)
            if dist < 8:
                self.hit = True
                self.returning = True
                return True  # 命中
            move = self.speed * dt
            if move >= dist:
                self.px = tx
                self.py = ty
                self.hit = True
                self.returning = True
                return True
            self.px += dx / dist * move
            self.py += dy / dist * move
            return False


# ═══════════════════════════════════════
#  建筑
# ═══════════════════════════════════════

class Building:
    """房间内的建筑: 门/床/炮塔/维修台 + 15 种新工具"""
    _next_uid = 1  # 类级自增 ID，避免 id() 复用隐患

    def __init__(self, btype, grid_col, grid_row, room_id):
        self.uid = Building._next_uid  # 唯一稳定标识
        Building._next_uid += 1
        self.type = btype
        self.grid_col = grid_col
        self.grid_row = grid_row
        self.room_id = room_id
        self.level = 0  # 索引0 = Lv1

        # 门专属
        self.door_type = DOOR_WOOD if btype == BLDG_DOOR else None  # 门材质类型
        self.current_hp = DOOR_MAX_HP[0] if btype == BLDG_DOOR else 0
        self.being_repaired = False  # 当前帧是否被维修中
        # 门开关状态(用于门的反复开关机制)
        self.original_blue_col = grid_col  # 门的原始蓝格位置(用于开门时滑回)
        self.original_blue_row = grid_row
        self.is_door_closed = False  # 门是否已关闭(滑入箭头位置)

        # 炮塔专属
        if btype == BLDG_TURRET:
            self._cooldown = 0.0

        # 通用: 升级费用缓存
        self._upgrade_cost_cache = None

        # 工具专属通用字段
        self.cooldown_timer = 0.0     # 通用冷却倒计时
        self.active_timer = 0.0       # 通用效果持续时间
        self.attack_count = 0          # 用于一盆小草的攻击计数
        self.facing_angle = 0.0        # 蛤蟆/屠龙刀朝向
        # 镜子专属
        self.mirror_burn_timer = 0.0   # 灼热红光剩余时间
        self.mirror_burn_cooldown = 0.0  # 灼热红光冷却
        self.mirror_burn_active = False  # 当前是否灼热红光中
        self.mirror_target_hunter = None  # 当前镜子锁定的猎梦者

    @property
    def pos(self):
        return self.grid_col, self.grid_row

    @property
    def px_center(self):
        return self.grid_col * TILE_SIZE + TILE_SIZE // 2, self.grid_row * TILE_SIZE + TILE_SIZE // 2

    @property
    def max_hp(self):
        if self.type == BLDG_DOOR:
            return DOOR_MAX_HP[self.level]
        return 0

    @property
    def alive(self):
        if self.type == BLDG_DOOR:
            return self.current_hp > 0
        return True

    # ─── 升级费用查询 ───

    def upgrade_cost(self):
        if self.type == BLDG_DOOR:
            if self.level + 1 >= len(DOOR_UPGRADE_COST):
                return None
            return DOOR_UPGRADE_COST[self.level + 1]
        elif self.type == BLDG_BED:
            if self.level + 1 >= len(BED_UPGRADE_COST):
                return None
            return BED_UPGRADE_COST[self.level + 1]
        elif self.type == BLDG_TURRET:
            if self.level + 1 >= len(TURRET_UPGRADE_COST):
                return None
            return TURRET_UPGRADE_COST[self.level + 1]
        elif self.type == BLDG_REPAIR:
            if self.level + 1 >= len(REPAIR_UPGRADE_COST):
                return None
            return REPAIR_UPGRADE_COST[self.level + 1]
        elif self.type == BLDG_GAMEMACHINE:
            if self.level + 1 >= len(GAMEMACHINE_UPGRADE_COST):
                return None
            return GAMEMACHINE_UPGRADE_COST[self.level + 1]
        elif self.type in MINE_TYPES:
            # 矿的等级通过 type 编码: 升级即改为下一级 type
            # 费用按 (当前 type 索引 + 1) 对应 MINE_COST_GOLD
            mine_idx = MINE_TYPES.index(self.type)
            if mine_idx + 1 >= len(MINE_TYPES):
                return None  # 钻石矿已顶级
            return MINE_COST_GOLD[mine_idx + 1]
        return None

    def can_upgrade(self):
        return self.upgrade_cost() is not None

    def upgrade(self):
        """执行升级, 返回新等级"""
        if not self.can_upgrade():
            return self.level
        if self.type in MINE_TYPES:
            # 矿升级: 直接将 type 改为下一级, level 字段对矿无意义(用 type 编码)
            mine_idx = MINE_TYPES.index(self.type)
            if mine_idx + 1 >= len(MINE_TYPES):
                return self.type
            self.type = MINE_TYPES[mine_idx + 1]
            return self.type
        self.level += 1
        if self.type == BLDG_DOOR:
            # 门升级: 5级(索引4)时切换材质
            if self.level == 5:
                self.door_type = DOOR_IRON  # 木门满级→铁门
            elif self.level == 10:
                self.door_type = DOOR_GOLD  # 铁门满级→金门
            self.current_hp = self.max_hp  # 升级回满血
        return self.level

    # ─── 建筑静态属性查询（用于各系统读取数值） ───

    @property
    def build_cost_gold(self):
        """建造此建筑所需金币（不含电力）"""
        costs = {
            BLDG_DOOR: 0,  # 门是预生成的
            BLDG_BED: 0,   # 床是预生成的
            BLDG_TURRET: TURRET_UPGRADE_COST[0],
            BLDG_REPAIR: REPAIR_COST,
            BLDG_GAMEMACHINE: GAMEMACHINE_COST[0],
            BLDG_MINE_COPPER: MINE_COST_GOLD[0],
            BLDG_MINE_SILVER: MINE_COST_GOLD[1],
            BLDG_MINE_GOLD: MINE_COST_GOLD[2],
            BLDG_MINE_DIAMOND: MINE_COST_GOLD[3],
            BLDG_FRIDGE: FRIDGE_COST_GOLD,
            BLDG_SHIELD: SHIELD_COST_GOLD,
            BLDG_TRAP: TRAP_COST_GOLD,
            BLDG_GUILLOTINE: GUILLOTINE_COST_GOLD,
            BLDG_GRASS_S: GRASS_S_COST,
            BLDG_GRASS_L: GRASS_L_COST,
            BLDG_MIRROR: MIRROR_COST,
            BLDG_GARLIC: GARLIC_COST,
            BLDG_FROG: FROG_COST,
            BLDG_BEAR_BED: BEAR_BED_COST,
            BLDG_SWORD: SWORD_COST,
        }
        return costs.get(self.type, 0)

    @property
    def build_cost_power(self):
        """建造此建筑所需电力（仅需电力的建筑返回 > 0）"""
        costs = {
            BLDG_MINE_COPPER: MINE_COST_POWER[0],
            BLDG_MINE_SILVER: MINE_COST_POWER[1],
            BLDG_MINE_GOLD: MINE_COST_POWER[2],
            BLDG_MINE_DIAMOND: MINE_COST_POWER[3],
            BLDG_FRIDGE: FRIDGE_COST_POWER,
            BLDG_SHIELD: SHIELD_COST_POWER,
            BLDG_TRAP: TRAP_COST_POWER,
            BLDG_GUILLOTINE: GUILLOTINE_COST_POWER,
        }
        return costs.get(self.type, 0)

    @property
    def requires_power(self):
        """此建筑建造时是否需要消耗电力"""
        return self.build_cost_power > 0

    @property
    def power_per_sec(self):
        """此建筑每秒产生多少电力（仅游戏机）"""
        if self.type == BLDG_GAMEMACHINE:
            return GAMEMACHINE_POWER_PER_SEC[self.level]
        return 0.0

    @property
    def gold_per_sec(self):
        """此建筑每秒产生多少金币（床/矿/小熊睡床/镜子）
        备注: 镜子和小熊睡床的实际产出在 update_economy() 中根据
        猎梦者距离/队友死亡数量动态计算, 此处仅返回基础值(>0)以确保不被跳过"""
        if self.type == BLDG_BED:
            return BED_GOLD_PER_SEC[self.level]
        if self.type in MINE_TYPES:
            level = self.type - BLDG_MINE_COPPER
            return MINE_GOLD_PER_SEC[level]
        if self.type == BLDG_BEAR_BED:
            return BEAR_BED_GOLD_PER_SEC  # 基础1, 实际按队友死亡数倍增
        if self.type == BLDG_MIRROR:
            return MIRROR_GOLD_FAR  # 占位: 实际按猎梦者距离切换
        return 0.0

    @property
    def turret_dps(self):
        if self.type == BLDG_TURRET:
            return TURRET_DPS[self.level]
        return 0

    @property
    def turret_range(self):
        if self.type == BLDG_TURRET:
            return TURRET_RANGE[self.level]
        return 0

    @property
    def turret_atk_speed(self):
        if self.type == BLDG_TURRET:
            return TURRET_ATK_SPEED[self.level]
        return 0

    @property
    def repair_hps(self):
        if self.type == BLDG_REPAIR:
            return REPAIR_HPS[self.level]
        return 0

    def take_damage(self, amount):
        if self.type == BLDG_DOOR:
            self.current_hp -= amount
            if self.current_hp < 0:
                self.current_hp = 0

    def repair(self, amount):
        if self.type == BLDG_DOOR and self.current_hp > 0:
            self.current_hp = min(self.current_hp + amount, self.max_hp)
