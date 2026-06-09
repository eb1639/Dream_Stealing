# ── 屏幕 ──
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
TILE_SIZE = 32
HUD_HEIGHT = 56
MAP_PIXEL_W = 33 * TILE_SIZE  # 1056 (默认, 加载地图时动态更新)
MAP_PIXEL_H = 26 * TILE_SIZE  # 832  (默认, 加载地图时动态更新)
MAP_COLS = 33  # 默认, 加载地图时动态更新
MAP_ROWS = 26  # 默认, 加载地图时动态更新


def set_map_size(cols, rows):
    """加载地图时调用, 动态更新地图尺寸"""
    global MAP_COLS, MAP_ROWS, MAP_PIXEL_W, MAP_PIXEL_H
    MAP_COLS = cols
    MAP_ROWS = rows
    MAP_PIXEL_W = cols * TILE_SIZE
    MAP_PIXEL_H = rows * TILE_SIZE


# ── 地图类型 ──
MAP_TYPE_EASY = 'easy'
MAP_TYPE_NORMAL = 'normal'
MAP_TYPE_HARD = 'hard'             # 旧冰雪地图(已弃用, 保留常量以防兼容性问题)
MAP_TYPE_HELL = 'hell'
MAP_TYPE_SNOW = 'snow'             # 雪地地图(替换之前的"冰雪")

# 候选池: 已移除 hard (旧冰雪地图, 已被 snow 取代)
MAP_TYPES = [MAP_TYPE_EASY, MAP_TYPE_NORMAL, MAP_TYPE_SNOW, MAP_TYPE_HELL]
MAP_NAMES = {
    MAP_TYPE_EASY: '简单',
    MAP_TYPE_NORMAL: '苔藓',
    MAP_TYPE_SNOW: '雪地',
    MAP_TYPE_HELL: '炼狱',
    MAP_TYPE_HARD: '冰雪(已弃用)',
}

# ── 走廊风格 ──
CORRIDOR_WOOD = 'wood'
CORRIDOR_MOSS = 'moss'
CORRIDOR_SNOW = 'snow'
CORRIDOR_LAVA = 'lava'

# ── 颜色 ──
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 40, 40)
GREEN = (40, 180, 60)
BLUE = (50, 100, 220)
YELLOW = (240, 200, 20)
PURPLE = (140, 40, 180)
DARK_PURPLE = (80, 10, 120)
ORANGE = (240, 140, 20)
GRAY = (120, 120, 120)
DARK_GRAY = (60, 60, 60)
LIGHT_GRAY = (200, 200, 200)
BROWN = (92, 61, 46)
DARK_BROWN = (60, 38, 28)
TEAL = (45, 138, 110)
DARK_TEAL = (30, 100, 78)
BEIGE = (232, 220, 200)
DARK_BEIGE = (200, 185, 160)
IRON = (80, 80, 85)
CYAN = (80, 200, 220)
GOLD = (220, 180, 30)

# ── Tile 类型（与矩阵 JSON 1:1 对应, 矩阵值即下值） ──
# 矩阵值:  0 走廊   1 房间   2 墙体   3 房门(蓝格)   4 红格(进门箭头, 踏入触发门滑入)   5 猎梦者出生点
TILE_EMPTY       = 0
TILE_ROOM        = 1
TILE_WALL        = 2
TILE_DOOR        = 3
TILE_RED_CHANNEL = 4   # 矩阵值 4, 人类踏入触发门滑入动画(从蓝格滑到红格)
TILE_SPAWN       = 5   # 矩阵值 5, 猎梦者出生点(等同走廊, 站立回血)
# 仅游戏内部使用的 Grid 值 (不出现在矩阵中)
TILE_BED         = 6

# ── 人类状态 ──
HUMAN_WANDERING = 0
HUMAN_BED = 1
HUMAN_DEAD = 2

# ── 游戏阶段 ──
PHASE_MENU = 0
PHASE_INIT = 1
PHASE_SAFE = 2
PHASE_PLAYING = 3
PHASE_VICTORY = 4
PHASE_DEFEAT = 5

# ── 模式 ──
MODE_HUMAN = 0
MODE_HUNTER = 1

# ─ 建筑类型 ──
BLDG_DOOR = 0
BLDG_BED = 1
BLDG_TURRET = 2
BLDG_REPAIR = 3
# 基础类
BLDG_GAMEMACHINE = 4       # 游戏机（产电）
BLDG_MINE_COPPER  = 5      # 铜矿 Lv1（建造菜单可建）
BLDG_MINE_SILVER  = 6      # 银矿 Lv2（铜矿升级后）
BLDG_MINE_GOLD    = 7      # 金矿 Lv3（银矿升级后）
BLDG_MINE_DIAMOND = 8      # 钻石矿 Lv4（金矿升级后）
# 高科技类
BLDG_FRIDGE = 9            # 冰箱（减速猎梦者攻速）
BLDG_SHIELD = 10           # 能量罩（门血低时无敌护盾）
# 黑科技类
BLDG_TRAP = 11             # 诱捕网（猎梦者逃跑时定身）
BLDG_GUILLOTINE = 12       # 断头台（猎梦者低血时直接斩10%）
# 特殊类
BLDG_GRASS_S = 13          # 一根小草（被攻击时少量金币）
BLDG_GRASS_L = 14          # 一盆小草（被攻击时较多金币，随攻击叠加）
BLDG_MIRROR = 15           # 镜子（远距少量金币，近距双倍）
BLDG_GARLIC = 16           # 大蒜（门血低时熏走猎梦者）
BLDG_FROG = 17             # 蛤蟆（远程舌攻，伤害低）
BLDG_BEAR_BED = 18         # 小熊睡床（产钱，队友死时翻倍）
BLDG_SWORD = 19            # 屠龙刀（手动一刀砍猎梦者20%血量）

# 矿等级映射：按 (type - BLDG_MINE_COPPER) 算等级
MINE_TYPES = (BLDG_MINE_COPPER, BLDG_MINE_SILVER, BLDG_MINE_GOLD, BLDG_MINE_DIAMOND)
MINE_UPGRADE_NAME = {
    BLDG_MINE_COPPER:  '银矿',
    BLDG_MINE_SILVER:  '金矿',
    BLDG_MINE_GOLD:    '钻石矿',
    # BLDG_MINE_DIAMOND 已顶级，无下一级
}

# 建筑中文名（用于HUD显示）
BLDG_NAMES = {
    BLDG_DOOR: '门',
    BLDG_BED: '床',
    BLDG_TURRET: '炮塔',
    BLDG_REPAIR: '维修台',
    BLDG_GAMEMACHINE: '游戏机',
    BLDG_MINE_COPPER: '铜矿',
    BLDG_MINE_SILVER: '银矿',
    BLDG_MINE_GOLD: '金矿',
    BLDG_MINE_DIAMOND: '钻石矿',
    BLDG_FRIDGE: '冰箱',
    BLDG_SHIELD: '能量罩',
    BLDG_TRAP: '诱捕网',
    BLDG_GUILLOTINE: '断头台',
    BLDG_GRASS_S: '小草',
    BLDG_GRASS_L: '一盆小草',
    BLDG_MIRROR: '镜子',
    BLDG_GARLIC: '大蒜',
    BLDG_FROG: '蛤蟆',
    BLDG_BEAR_BED: '小熊睡床',
    BLDG_SWORD: '屠龙刀',
}

# ── 难度等级 ──
DIFF_EASY = 0          # 简单
DIFF_NORMAL = 1         # 普通
DIFF_HARD = 2           # 困难
DIFF_NIGHTMARE = 3      # 噩梦
DIFF_HELL = 4           # 地狱
DIFF_PURGATORY = 5      # 炼狱
DIFF_ENDLESS = 6        # 无尽模式

DIFF_NAMES = {
    DIFF_EASY: '简单',
    DIFF_NORMAL: '普通',
    DIFF_HARD: '困难',
    DIFF_NIGHTMARE: '噩梦',
    DIFF_HELL: '地狱',
    DIFF_PURGATORY: '炼狱',
    DIFF_ENDLESS: '无尽',
}

DIFF_COLORS = {
    DIFF_EASY: (80, 200, 80),
    DIFF_NORMAL: (200, 200, 60),
    DIFF_HARD: (220, 140, 40),
    DIFF_NIGHTMARE: (200, 60, 60),
    DIFF_HELL: (180, 30, 30),
    DIFF_PURGATORY: (140, 20, 160),
    DIFF_ENDLESS: (220, 50, 220),
}

# ── 猎梦者种类 ──
HUNTER_SUNNY = 0       # 晴天娃娃猎梦者
HUNTER_BIGHEAD = 1     # 大头猎梦者
HUNTER_GRANDMA = 2     # 孙婆婆猎梦者
HUNTER_BANDAGE = 3     # 绷带猎梦者
HUNTER_REDDRESS = 4    # 红裙小女孩猎梦者

HUNTER_TYPE_NAMES = {
    HUNTER_SUNNY: '晴天娃娃',
    HUNTER_BIGHEAD: '大头',
    HUNTER_GRANDMA: '孙婆婆',
    HUNTER_BANDAGE: '绷带',
    HUNTER_REDDRESS: '红裙小女孩',
}

# 种类属性倍率: (HP倍率, ATK倍率)
HUNTER_TYPE_MULT = {
    HUNTER_SUNNY:    (1.0, 1.0),   # 普通
    HUNTER_BIGHEAD:  (1.0, 1.5),   # 高攻击
    HUNTER_GRANDMA:  (1.0, 1.0),   # 普通
    HUNTER_BANDAGE:  (1.5, 1.0),   # 高血量
    HUNTER_REDDRESS: (1.3, 1.8),   # 最高攻击+较高血量
}

# ── 猎梦者技能参数 ──
BERSERK_DURATION = 10.0       # 狂暴持续10秒
BERSERK_COOLDOWN = 40.0       # 狂暴冷却40秒
BERSERK_ATK_MULT = 1.4        # 狂暴攻击力倍率
BERSERK_SPEED_MULT = 1.3      # 狂暴攻速倍率
BERSERK_TRIGGER_CHANCE = 0.05 # 晴天娃娃狂暴触发概率(每次攻击)

CLONE_HP_RATIO = 0.3          # 分身血量=本体30%
CLONE_ATK_RATIO = 0.4         # 分身攻击力=本体40%
CLONE_LIFETIME = 15.0         # 分身存活15秒后寻找主体合体
CLONE_MERGE_ATK_BONUS = 5.0   # 合体后永久额外攻击力(每分身)

BANDAGE_HEAL_RATE = 30        # 绷带回血速率(HP/秒)
BANDAGE_HEAL_TRIGGER = 0.3    # 血量低于30%触发
BANDAGE_HEAL_STOP = 0.5       # 回血到50%停止

# 猎梦者泉水回血(苔藓地图出生点)
HUNTER_SPAWN_HEAL_RATE = 20   # HP/秒(站在出生点格子上自动回血)

# 雪地地图门滑入动画时长
SNOW_DOOR_SLIDE_DURATION = 0.35  # 秒

# 雪地地图门滑入的猎梦者攻击目标: 红色通道位置(而不是旧蓝格)

TURRET_DISABLE_DURATION = 6.0  # 炮停持续6秒
TURRET_DISABLE_COOLDOWN = 40.0 # 炮停冷却40秒
TURRET_DISABLE_CHANCE = 0.06   # 红裙小女孩炮停触发概率(每次攻击)

# 难度→猎梦者配置: (种类列表, 数量)
DIFF_HUNTER_CONFIG = {
    DIFF_EASY:       ([HUNTER_SUNNY], 1),
    DIFF_NORMAL:     ([HUNTER_BIGHEAD], 1),
    DIFF_HARD:       ([HUNTER_BIGHEAD, HUNTER_GRANDMA, HUNTER_BANDAGE, HUNTER_REDDRESS], 1),
    DIFF_NIGHTMARE:  ([HUNTER_BIGHEAD, HUNTER_GRANDMA, HUNTER_BANDAGE, HUNTER_REDDRESS], 2),
    DIFF_HELL:       ([HUNTER_BIGHEAD, HUNTER_GRANDMA, HUNTER_BANDAGE, HUNTER_REDDRESS], 3),
    DIFF_PURGATORY:  ([HUNTER_BIGHEAD, HUNTER_GRANDMA, HUNTER_BANDAGE, HUNTER_REDDRESS], 4),
}

# 无尽模式初始猎梦者数量
ENDLESS_START_COUNT = 1
# 无尽模式每波猎梦者数量递增
ENDLESS_COUNT_PER_WAVE = 1
# 无尽模式每波属性倍率递增
ENDLESS_STAT_MULT_PER_WAVE = 0.15

# ── 猎梦者升级阈值与属性 (Lv1~Lv5) ──
HUNTER_THRESHOLDS = [0, 350, 1200, 3500, 8000]
HUNTER_MAX_HP = [500, 800, 1200, 1700, 2500]    # 提高血量 (~+30%)
HUNTER_ATK = [10, 15, 24, 35, 52]               # 提高攻击力 (~+30%)
HUNTER_ATK_SPEED = [0.7, 0.9, 1.1, 1.4, 1.7]   # 提高攻速 (~+15%)
HUNTER_SPEED = [3.5, 3.5, 3.5, 3.8, 4.2]

# ── 门类型 ──
DOOR_WOOD = 0    # 木门
DOOR_IRON = 1    # 铁门
DOOR_GOLD = 2    # 金门

DOOR_TYPE_NAMES = {
    DOOR_WOOD: '木门',
    DOOR_IRON: '铁门',
    DOOR_GOLD: '金门',
}

DOOR_TYPE_COLORS = {
    DOOR_WOOD: BROWN,
    DOOR_IRON: IRON,
    DOOR_GOLD: GOLD,
}

# 门升级: 每阶段5级(木1-5→铁1-5→金1-5)，共15级
# 等级 0-4: 木门1-5, 5-9: 铁门1-5, 10-14: 金门1-5
DOOR_MAX_HP = [
    # 木门1-5
    500, 850, 1400, 2200, 3500,
    # 铁门1-5
    5000, 7000, 9500, 13000, 17000,
    # 金门1-5
    22000, 28000, 35000, 43000, 52000,
]

DOOR_UPGRADE_COST = [
    # 木门升级(1→2→3→4→5)
    0, 40, 100, 230, 500,
    # 铁门升级(1→2→3→4→5)
    800, 1200, 1800, 2500, 3500,
    # 金门升级(1→2→3→4→5)
    5000, 7000, 9500, 13000, 18000,
]

DOOR_MAX_LEVEL = 14  # 最高14级(索引)，即金门5

# ── 床升级数据 ──
BED_UPGRADE_COST = [0, 30, 70, 180, 450, 1000]
BED_GOLD_PER_SEC = [1, 2, 4, 8, 16, 32]

# ── 炮塔数据 ──
TURRET_UPGRADE_COST = [40, 35, 80, 200]   # 降低升级费用
TURRET_DPS = [12, 20, 32, 50]             # 提升DPS
TURRET_RANGE = [5, 6, 7, 8]
TURRET_ATK_SPEED = [0.7, 0.9, 1.2, 1.5]

# ── 维修台 ──
REPAIR_COST = 30                          # 降低建造成本(原35)
REPAIR_UPGRADE_COST = [0, 30, 75, 200, 450] # 降低升级费用
# 维修台回血效率已提升, 帮助玩家扛过狂暴期: [40, 70, 110, 170, 260] -> [70, 120, 190, 290, 420]
REPAIR_HPS = [70, 120, 190, 290, 420]

# ── 游戏机 (Lv1~Lv5) ──
GAMEMACHINE_COST = [200, 250, 500, 1000, 2000]
GAMEMACHINE_POWER_PER_SEC = [1, 2, 4, 8, 16]
GAMEMACHINE_UPGRADE_COST = [250, 500, 1000, 2000]

# ── 矿坑（消耗电力 + 金币双门槛，每秒产金币）──
# 铜矿 Lv1/Lv2/Lv3/Lv4 分别 4/12/40/120 金币/秒
MINE_COST_GOLD = [40, 120, 300, 800]
MINE_COST_POWER = [8, 16, 32, 64]
MINE_GOLD_PER_SEC = [4, 12, 40, 120]

# ── 冰箱（高科技）──
FRIDGE_COST_GOLD = 80
FRIDGE_COST_POWER = 30
FRIDGE_ATK_SLOW = 0.2  # 减攻速20%

# ── 能量罩（高科技）──
SHIELD_COST_GOLD = 100
SHIELD_COST_POWER = 40
SHIELD_THRESHOLD = 0.30      # 门血 < 30% 触发
SHIELD_DURATION = 3.0         # 持续 3 秒
SHIELD_COOLDOWN = 30.0        # 冷却 30 秒

# ── 诱捕网（黑科技）──
TRAP_COST_GOLD = 150
TRAP_COST_POWER = 60
TRAP_DURATION = 2.0           # 定身 2 秒
TRAP_COOLDOWN = 10.0          # 冷却 10 秒
TRAP_PROC_HP_RATIO = 0.3      # 猎梦者 HP < 30% 且逃跑时触发

# ── 断头台（黑科技）──
GUILLOTINE_COST_GOLD = 400
GUILLOTINE_COST_POWER = 200
GUILLOTINE_THRESHOLD = 0.20   # 猎梦者 HP < 20% 触发
GUILLOTINE_DAMAGE_RATIO = 0.10  # 造成 10% 最大 HP 伤害
GUILLOTINE_COOLDOWN = 20.0

# ── 一根小草（特殊）──
GRASS_S_COST = 30
GRASS_S_GOLD_PER_HIT = 1     # 门被攻击时每次给 1 金币

# ── 一盆小草（特殊）──
GRASS_L_COST = 80
GRASS_L_BASE_GOLD_PER_HIT = 2
GRASS_L_STACK_BONUS = 1       # 每次被攻击 +1 额外金币（封顶 5）

# ── 镜子（特殊）──
MIRROR_COST = 60
MIRROR_GOLD_FAR = 1.0         # 猎梦者远时 1 金币/秒(8格外)
MIRROR_GOLD_NEAR = 2.0        # 猎梦者近时 2 金币/秒(8格内)
MIRROR_NEAR_DIST = 8           # 8 格内算"近"
MIRROR_BURN_CHANCE = 0.05     # 5%概率触发灼热红光
MIRROR_BURN_DURATION = 5.0    # 灼热红光持续5秒
MIRROR_BURN_COOLDOWN = 90.0   # 灼热红光冷却90秒
MIRROR_BURN_GOLD = 8.0        # 灼热红光期间8金/秒
MIRROR_BURN_DAMAGE = 5        # 灼热红光每秒对猎梦者造成伤害

# ── 大蒜（特殊）──
GARLIC_COST = 80
GARLIC_THRESHOLD = 0.30       # 门血 < 30% 触发
GARLIC_FEAR_DURATION = 2.0    # 熏走 2 秒
GARLIC_COOLDOWN = 30.0

# ── 蛤蟆（特殊）──
FROG_COST = 50
FROG_RANGE = 7                # 攻击范围 7 格
FROG_DPS = 3                  # 3 伤害/秒(原1, 提升便于观察效果)
FROG_COOLDOWN = 0.5           # 冷却 0.5 秒, 每秒攻击 2 次

# ── 小熊睡床（特殊）──
BEAR_BED_COST = 120
BEAR_BED_GOLD_PER_SEC = 1     # 基础 1 金币/秒
BEAR_BED_MAX_BONUS = 32        # 队友死时翻倍封顶 32

# ── 屠龙刀（特殊）──
SWORD_COST = 200
SWORD_DAMAGE_RATIO = 0.20      # 一刀 20% 最大血量
SWORD_COOLDOWN = 15.0
SWORD_ANIM_FLY_DURATION = 0.25   # 飞向猎梦者(秒)
SWORD_ANIM_SLASH_DURATION = 0.15 # 砍击动作(秒)
SWORD_ANIM_RETURN_DURATION = 0.30 # 飞回原位(秒)

# ── 音频 ──
BGM_VOLUME_DEFAULT = 0.5
SFX_VOLUME_DEFAULT = 0.7
HUNTER_INTENSE_LEVEL = 3  # 猎梦者升级到该等级后切换紧张BGM

# ── 通用 ──
HUMAN_INIT_GOLD = 30         # 初始金币
SAFE_TIME = 30                # 秒(原25)
AI_DECISION_MIN = 3.0
AI_DECISION_MAX = 5.0
BULLET_SPEED = 360  # px/秒
HUMAN_SPEED = 4.0   # 格/秒

# ── 人类玩家颜色 ──
PLAYER_COLOR = (60, 120, 255)
AI_HUMAN_COLORS = [
    (80, 180, 80),    # 绿
    (220, 180, 40),   # 金
    (220, 100, 60),   # 橙
    (100, 200, 200),  # 青
    (200, 100, 180),  # 粉
]

# ── 建筑分类（建造菜单分组）──
CATEGORY_BASIC = '基础'
CATEGORY_EARNING = '赚钱'
CATEGORY_HIGHTECH = '高科技'
CATEGORY_BLACKTECH = '黑科技'
CATEGORY_SPECIAL = '特殊'
CATEGORY_DEFENSE = '防御'

BUILDING_CATEGORIES = {
    BLDG_TURRET: CATEGORY_DEFENSE,
    BLDG_REPAIR: CATEGORY_DEFENSE,
    BLDG_GAMEMACHINE: CATEGORY_BASIC,
    BLDG_MINE_COPPER: CATEGORY_EARNING,
    BLDG_MINE_SILVER: CATEGORY_EARNING,
    BLDG_MINE_GOLD: CATEGORY_EARNING,
    BLDG_MINE_DIAMOND: CATEGORY_EARNING,
    BLDG_FRIDGE: CATEGORY_HIGHTECH,
    BLDG_SHIELD: CATEGORY_HIGHTECH,
    BLDG_TRAP: CATEGORY_BLACKTECH,
    BLDG_GUILLOTINE: CATEGORY_BLACKTECH,
    BLDG_GRASS_S: CATEGORY_SPECIAL,
    BLDG_GRASS_L: CATEGORY_SPECIAL,
    BLDG_MIRROR: CATEGORY_SPECIAL,
    BLDG_GARLIC: CATEGORY_SPECIAL,
    BLDG_FROG: CATEGORY_SPECIAL,
    BLDG_BEAR_BED: CATEGORY_SPECIAL,
    BLDG_SWORD: CATEGORY_SPECIAL,
}
