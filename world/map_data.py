"""
地图网格定义、多地图加载、矩阵地图支持、A*寻路
"""
import os
import json
import random
import heapq
from core.config import *
import core.config as _cfg


class RoomTemplate:
    """房间模板（支持不规则形状）"""
    def __init__(self, room_id, cells, door_col, door_row, door_dir='right', bed_col=None, bed_row=None):
        self.id = room_id
        self.cells = set(cells)
        self.door_col = door_col
        self.door_row = door_row
        self.door_dir = door_dir
        self.bed_col = bed_col
        self.bed_row = bed_row
        self.door_arrow_col = None  # 箭头位置(门移动后的目标位置)
        self.door_arrow_row = None
        self.door_blue_col = door_col  # 门的原始蓝格位置(用于开门时滑回)
        self.door_blue_row = door_row

        self.min_col = min(c[0] for c in cells)
        self.max_col = max(c[0] for c in cells)
        self.min_row = min(c[1] for c in cells)
        self.max_row = max(c[1] for c in cells)
        self.w = self.max_col - self.min_col + 1
        self.h = self.max_row - self.min_row + 1

        self.door_exit = self._get_door_exit()
        self.door_approach = [self.door_exit]
        self.interior = list(self.cells)

    def _get_door_exit(self):
        """门外第一格（走廊侧，远离房间的方向）
        door_dir表示房间在门的哪一侧，exit在相反方向"""
        if self.door_dir == 'right':
            return (self.door_col - 1, self.door_row)
        elif self.door_dir == 'left':
            return (self.door_col + 1, self.door_row)
        elif self.door_dir == 'up':
            return (self.door_col, self.door_row + 1)
        else:  # down
            return (self.door_col, self.door_row - 1)

    def contains(self, col, row):
        return (col, row) in self.cells

    @property
    def bounds(self):
        return self.min_col, self.min_row, self.w, self.h

    @property
    def door_pos(self):
        return self.door_col, self.door_row

    @property
    def bed_pos(self):
        return self.bed_col, self.bed_row


class MapConfig:
    """地图配置"""
    def __init__(self, data):
        self.map_type = data['map_type']
        self.map_name = data.get('map_name', data['map_type'])
        self.corridor_style = data.get('corridor_style', 'wood')
        self.grid_width = data['grid_width']
        self.grid_height = data['grid_height']
        self.room_count = data.get('room_count', len(data.get('rooms', [])))
        self.rooms = data.get('rooms', [])
        self.path_cells = data.get('path_cells', [])
        # 矩阵地图(优先于 rects 房间定义)
        self.matrix = data.get('matrix', None)
        # 门对与出生点统一由 build_map 阶段从矩阵自动生成(不依赖 JSON 顶层字段)
        self.door_pairs = []
        self.spawn_points_cfg = []
        # 泉水已废弃, 保留字段兼容旧配置
        self.fountain = []


def _infer_door_dir(x, y, w, h, door_c, door_r):
    """根据门位置自动推断门朝向(left/right/up/down)
    优先匹配墙壁位置(门在房间外围), 再匹配房间边界, 最后按最近边界推断"""
    # 门在墙壁上(房间外围一格)
    if door_c == x - 1:
        return "left"
    if door_c == x + w:
        return "right"
    if door_r == y - 1:
        return "up"
    if door_r == y + h:
        return "down"
    # 门在房间边界上
    if door_c == x:
        return "left"
    if door_c == x + w - 1:
        return "right"
    if door_r == y:
        return "up"
    if door_r == y + h - 1:
        return "down"
    # 门在房间内部: 找最近边界
    dist_top = door_r - y
    dist_bottom = (y + h - 1) - door_r
    dist_left = door_c - x
    dist_right = (x + w - 1) - door_c
    min_dist = min(dist_top, dist_bottom, dist_left, dist_right)
    if min_dist == dist_top:
        return "up"
    if min_dist == dist_bottom:
        return "down"
    if min_dist == dist_left:
        return "left"
    return "right"


def _infer_door_dir_from_cells(cells, door_c, door_r):
    """根据房间格子集合推断门朝向：检查门的哪一侧有房间格子"""
    cell_set = set(cells)
    # 门朝向 = 房间在门的哪一侧
    if (door_c + 1, door_r) in cell_set:
        return "right"
    if (door_c - 1, door_r) in cell_set:
        return "left"
    if (door_c, door_r + 1) in cell_set:
        return "down"
    if (door_c, door_r - 1) in cell_set:
        return "up"
    # 默认朝下
    return "down"


def _adjust_door_to_wall(x, y, w, h, door_c, door_r, door_dir):
    """将门位置调整到墙壁上(房间外围一格)
    如果门已在墙壁或边界上则不调整; 如果门在内部则移到对应边界的外墙"""
    # 已在墙壁上
    if door_c == x - 1 or door_c == x + w or door_r == y - 1 or door_r == y + h:
        return door_c, door_r
    # 在边界上 → 移到外墙
    if door_dir == 'up':
        return door_c, y - 1
    if door_dir == 'down':
        return door_c, y + h
    if door_dir == 'left':
        return x - 1, door_r
    if door_dir == 'right':
        return x + w, door_r
    return door_c, door_r


def load_map_config(map_type):
    """加载指定类型的地图配置"""
    filename = f"map_{map_type}.json"
    path = os.path.join(os.path.dirname(__file__), "config", filename)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return MapConfig(data)


# ── 矩阵值与 Tile 一一对应 (不再需要映射) ──
# 0 走廊 / 1 房间 / 2 墙 / 3 蓝格门 / 4 红格(进门箭头, 踏入触发门滑入) / 5 猎梦者出生点


def _build_from_matrix(matrix, cols, rows):
    """从用户提供的二维矩阵生成 grid + rooms 列表
    矩阵元素与 Tile 值一一对应:
        0 = 走廊  → TILE_EMPTY
        1 = 房间  → TILE_ROOM
        2 = 墙体  → TILE_WALL
        3 = 蓝格房门(初始位置) → TILE_DOOR
        4 = 红格(进门箭头) → TILE_RED_CHANNEL
        5 = 猎梦者出生点 → TILE_SPAWN
    返回 (grid, rooms_data)
        rooms_data: [{'rid':1, 'cells':[(c,r),...], 'door':(c,r), 'bed':(c,r), 'arrow':(c,r)|None}, ...]
    """
    grid = [[TILE_EMPTY for _ in range(cols)] for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            v = matrix[r][c]
            if v == TILE_EMPTY:
                grid[r][c] = TILE_EMPTY
            elif v == TILE_ROOM:
                grid[r][c] = TILE_ROOM
            elif v == TILE_WALL:
                grid[r][c] = TILE_WALL
            elif v == TILE_DOOR:
                grid[r][c] = TILE_DOOR
            elif v == TILE_RED_CHANNEL:
                grid[r][c] = TILE_RED_CHANNEL
            elif v == TILE_SPAWN:
                grid[r][c] = TILE_SPAWN
            else:
                grid[r][c] = TILE_EMPTY

    # 找房间: 从每个房间地砖出发 BFS, 收集连通 1-区域
    visited = set()
    rooms_data = []
    rid_counter = 1
    used_doors = set()  # 跟踪已被分配的门, 防止多个房间共享同一门
    for r in range(rows):
        for c in range(cols):
            if (c, r) in visited:
                continue
            if grid[r][c] != TILE_ROOM:
                continue
            # BFS 收集 4 方向连通的房间格
            cells = []
            queue = [(c, r)]
            visited.add((c, r))
            while queue:
                cc, cr = queue.pop(0)
                cells.append((cc, cr))
                for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nc, nr = cc + dc, cr + dr
                    if 0 <= nc < cols and 0 <= nr < rows:
                        if (nc, nr) not in visited and grid[nr][nc] == TILE_ROOM:
                            visited.add((nc, nr))
                            queue.append((nc, nr))

            # 找门: 优先选择非共享门(门的另一侧不是房间格子), 然后才是共享门
            # 这样可以避免两个房间共享同一个门(如 Room5 和 Room7 共享 (5,16) 门的问题)
            door_pos = None
            cell_set = set(cells)

            def _is_shared_door(nc, nr, dc, dr):
                """检查门是否是共享门：门的"另一侧"(从房间格子沿dc,dr方向再走一格)也是房间格子
                dc,dr 是从房间格子指向门的方向, 所以"另一侧" = (nc+dc, nr+dr)"""
                oc, or_ = nc + dc, nr + dr
                if 0 <= oc < cols and 0 <= or_ < rows:
                    return grid[or_][oc] == TILE_ROOM
                return False

            # 第一遍: 4 方向找未使用的非共享门
            for (cc, cr) in cells:
                for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nc, nr = cc + dc, cr + dr
                    if 0 <= nc < cols and 0 <= nr < rows and grid[nr][nc] == TILE_DOOR:
                        if (nc, nr) not in used_doors and not _is_shared_door(nc, nr, dc, dr):
                            door_pos = (nc, nr)
                            break
                if door_pos:
                    break

            # 第二遍: 8 方向找未使用的非共享门
            if door_pos is None:
                for (cc, cr) in cells:
                    for dc in [-1, 0, 1]:
                        for dr in [-1, 0, 1]:
                            if dc == 0 and dr == 0:
                                continue
                            nc, nr = cc + dc, cr + dr
                            if 0 <= nc < cols and 0 <= nr < rows and grid[nr][nc] == TILE_DOOR:
                                if (nc, nr) not in used_doors and not _is_shared_door(nc, nr, dc, dr):
                                    door_pos = (nc, nr)
                                    break
                        if door_pos:
                            break
                    if door_pos:
                        break

            # 第三遍: 4 方向找未使用的门(允许共享门, 兜底)
            if door_pos is None:
                for (cc, cr) in cells:
                    for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nc, nr = cc + dc, cr + dr
                        if 0 <= nc < cols and 0 <= nr < rows and grid[nr][nc] == TILE_DOOR:
                            if (nc, nr) not in used_doors:
                                door_pos = (nc, nr)
                                break
                    if door_pos:
                        break

            # 第四遍: 8 方向找未使用的门(允许共享门)
            if door_pos is None:
                for (cc, cr) in cells:
                    for dc in [-1, 0, 1]:
                        for dr in [-1, 0, 1]:
                            if dc == 0 and dr == 0:
                                continue
                            nc, nr = cc + dc, cr + dr
                            if 0 <= nc < cols and 0 <= nr < rows and grid[nr][nc] == TILE_DOOR:
                                if (nc, nr) not in used_doors:
                                    door_pos = (nc, nr)
                                    break
                        if door_pos:
                            break
                    if door_pos:
                        break

            # 第五遍: 4 方向找已被使用的门(兜底)
            if door_pos is None:
                for (cc, cr) in cells:
                    for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nc, nr = cc + dc, cr + dr
                        if 0 <= nc < cols and 0 <= nr < rows and grid[nr][nc] == TILE_DOOR:
                            door_pos = (nc, nr)
                            break
                    if door_pos:
                        break
            
            if door_pos is None:
                # 房间无门, 跳过(异常配置)
                continue

            # 标记此门已被使用
            used_doors.add(door_pos)

            # 找红格(进门箭头): 与门相邻的 TILE_RED_CHANNEL 格子
            arrow_pos = None
            dc, dr = door_pos
            for adc, adr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nc, nr = dc + adc, dr + adr
                if 0 <= nc < cols and 0 <= nr < rows and grid[nr][nc] == TILE_RED_CHANNEL:
                    if (nc, nr) not in cell_set:
                        arrow_pos = (nc, nr)
                        break

            # 床位置: 房间 (min_col+1, min_row+1) 角落(房间内部)
            min_c = min(x[0] for x in cells)
            min_r = min(x[1] for x in cells)
            bed_c, bed_r = min_c + 1, min_r + 1
            attempts = 0
            while (bed_c, bed_r) == door_pos or (bed_c, bed_r) not in cell_set:
                attempts += 1
                if attempts > 20:
                    bed_c, bed_r = cells[0]
                    break
                bed_c += 1
                if bed_c > max(x[0] for x in cells):
                    bed_c = min_c + 1
                    bed_r += 1
                if bed_r > max(x[1] for x in cells):
                    break

            rooms_data.append({
                'rid': rid_counter,
                'cells': cells,
                'door': door_pos,
                'bed': (bed_c, bed_r),
                'arrow': arrow_pos,
            })
            rid_counter += 1

    return grid, rooms_data


def build_map(map_type='easy'):
    """
    构建网格：房间 + 墙壁 + 门 + 走廊。
    支持不规则房间（rects/cells格式）和基于格子的墙壁生成。
    支持 matrix 格式(用户提供的二维矩阵)。
    返回 (grid, rooms, map_config)
    """
    map_config = load_map_config(map_type)
    cols = map_config.grid_width
    rows = map_config.grid_height

    # 更新全局配置
    _cfg.set_map_size(cols, rows)
    _cfg._current_map_config = map_config

    grid = [[TILE_EMPTY for _ in range(cols)] for _ in range(rows)]
    rooms = []

    # ── 矩阵地图路径 ──
    if map_config.matrix is not None:
        matrix = map_config.matrix
        if len(matrix) != rows or any(len(row) != cols for row in matrix):
            raise ValueError(
                f"matrix 尺寸({len(matrix)}x{len(matrix[0]) if matrix else 0}) "
                f"与 grid_width/grid_height({cols}x{rows}) 不一致")

        grid, rooms_data = _build_from_matrix(matrix, cols, rows)

        # 把 rooms_data 转成 RoomTemplate 实例
        for rd in rooms_data:
            cells = rd['cells']
            door_c, door_r = rd['door']
            bed_c, bed_r = rd['bed']
            arrow_pos = rd.get('arrow')
            door_dir = _infer_door_dir_from_cells(cells, door_c, door_r)
            room = RoomTemplate(rd['rid'], cells, door_c, door_r, door_dir, bed_c, bed_r)
            if arrow_pos:
                room.door_arrow_col, room.door_arrow_row = arrow_pos
            rooms.append(room)

        # ── 自动从矩阵生成门对(蓝→红滑动) ──
        # 规则: 扫描每对相邻的 蓝格(value 3) / 红格(value 4), 推算方向
        door_pairs = []
        for r in range(rows):
            for c in range(cols):
                if matrix[r][c] != TILE_DOOR:
                    continue
                # 红格必须在门的 4 方向邻居中, 且不在房间内
                for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nc, nr = c + dc, r + dr
                    if not (0 <= nc < cols and 0 <= nr < rows):
                        continue
                    if matrix[nr][nc] != TILE_RED_CHANNEL:
                        continue
                    # 方向: 从蓝指向红
                    if dc == -1: ddir = 'W'
                    elif dc ==  1: ddir = 'E'
                    elif dr == -1: ddir = 'N'
                    else:          ddir = 'S'
                    door_pairs.append({
                        'blue': [c, r],
                        'red':  [nc, nr],
                        'dir':  ddir,
                    })
                    break  # 每个蓝格只配对一个红格
        map_config.door_pairs = door_pairs

        # ── 猎梦者出生点: 扫描矩阵中值 5 的格子 ──
        spawn_pts = []
        for r in range(rows):
            for c in range(cols):
                if matrix[r][c] == TILE_SPAWN:
                    spawn_pts.append({'col': c, 'row': r})
        # 矩阵中没有标记值 5 时, 兜底使用 4 个分散出生点(四边正中央)
        if not spawn_pts:
            mid_c = 18 if cols >= 33 else cols // 2
            mid_r = 19 if rows >= 39 else rows // 2
            spawn_pts = [
                {'col': mid_c, 'row': 0},
                {'col': mid_c, 'row': rows - 1},
                {'col': 0, 'row': mid_r},
                {'col': cols - 1, 'row': mid_r},
            ]
        map_config.spawn_points_cfg = spawn_pts
        for sp in spawn_pts:
            cc, rr = int(sp['col']), int(sp['row'])
            if 0 <= cc < cols and 0 <= rr < rows:
                # 出生点必须是走廊: 强制清除墙体
                if grid[rr][cc] == TILE_WALL:
                    grid[rr][cc] = TILE_EMPTY
                grid[rr][cc] = TILE_SPAWN
                # 打通出生点向内延伸 1 格(防止被墙堵死)
                if cc == 0 and grid[rr][1] == TILE_WALL:
                    grid[rr][1] = TILE_EMPTY
                elif cc == cols - 1 and grid[rr][cols - 2] == TILE_WALL:
                    grid[rr][cols - 2] = TILE_EMPTY
                elif rr == 0 and grid[1][cc] == TILE_WALL:
                    grid[1][cc] = TILE_EMPTY
                elif rr == rows - 1 and grid[rows - 2][cc] == TILE_WALL:
                    grid[rows - 2][cc] = TILE_EMPTY

        # ── 矩阵地图已含完整墙壁, 跳过墙壁/连通性自动生成 ──
        # 但仍需确保外圈边界(防止矩阵中 0 出现在最外圈时被误用)
        # 保留四条边正中间的"凸出走廊"格(不改为墙)
        mid_c = 18 if cols >= 33 else cols // 2
        mid_r = 19 if rows >= 39 else rows // 2
        protrusion_cells = {
            (0, mid_c), (rows - 1, mid_c),
            (mid_r, 0), (mid_r, cols - 1),
        }
        for c in range(cols):
            if grid[0][c] == TILE_EMPTY and (0, c) not in protrusion_cells:
                grid[0][c] = TILE_WALL
            if grid[rows - 1][c] == TILE_EMPTY and (rows - 1, c) not in protrusion_cells:
                grid[rows - 1][c] = TILE_WALL
        for r in range(rows):
            if grid[r][0] == TILE_EMPTY and (r, 0) not in protrusion_cells:
                grid[r][0] = TILE_WALL
            if grid[r][cols - 1] == TILE_EMPTY and (r, cols - 1) not in protrusion_cells:
                grid[r][cols - 1] = TILE_WALL

        return grid, rooms, map_config

    # ── 普通 rooms/rects 路径 ──
    for room_data in map_config.rooms:
        rid = room_data['rid']
        door_c, door_r = room_data['door']
        bed_pos = room_data.get('bed')
        bed_c = bed_pos[0] if bed_pos else None
        bed_r = bed_pos[1] if bed_pos else None

        # 生成房间格子：支持 cells / rects / (x,y,w,h) 三种格式
        if 'cells' in room_data:
            cells = [tuple(c) for c in room_data['cells']]
        elif 'rects' in room_data:
            cells = []
            for rect in room_data['rects']:
                rx, ry, rw, rh = rect[0], rect[1], rect[2], rect[3]
                for r in range(ry, ry + rh):
                    for c in range(rx, rx + rw):
                        cells.append((c, r))
        else:
            x, y, w, h = room_data['x'], room_data['y'], room_data['w'], room_data['h']
            cells = [(c, r) for r in range(y, y + h) for c in range(x, x + w)]

        # 推断门方向（基于格子集合）
        door_dir = _infer_door_dir_from_cells(cells, door_c, door_r)

        room = RoomTemplate(rid, cells, door_c, door_r, door_dir, bed_c, bed_r)
        rooms.append(room)

    # ── 1. 收集所有房间格子和门格子 ──
    all_room_cells = {}   # (c,r) -> room_id
    door_cells = set()
    for room in rooms:
        for cx, cy in room.cells:
            all_room_cells[(cx, cy)] = room.id
        door_cells.add(room.door_pos)

    # ── 2. 标记房间和门 ──
    for (cx, cy), _ in all_room_cells.items():
        grid[cy][cx] = TILE_ROOM
    for cx, cy in door_cells:
        if 0 <= cx < cols and 0 <= cy < rows:
            grid[cy][cx] = TILE_DOOR

    # ── 3. 基于格子的墙壁生成 ──
    # 对每个房间格子，检查4方向邻居放墙(边)
    # 对角线邻居：只在形成"外角"时放墙(两个相邻边都是墙)
    for room in rooms:
        for c, r in room.cells:
            # 4方向: 上下左右 → 放墙
            for nc, nr in [(c - 1, r), (c + 1, r), (c, r - 1), (c, r + 1)]:
                if 0 <= nc < cols and 0 <= nr < rows:
                    if (nc, nr) not in all_room_cells and (nc, nr) not in door_cells:
                        if grid[nr][nc] == TILE_EMPTY:
                            grid[nr][nc] = TILE_WALL
            # 对角线: 两个相邻边都是边界(墙或门)时放墙(形成角落)
            # 确保房间拐角不漏墙，门旁边的角落也必须补上
            for dc, dr, ec1, er1, ec2, er2 in [
                (c-1, r-1, c-1, r, c, r-1),   # 左上角
                (c+1, r-1, c+1, r, c, r-1),   # 右上角
                (c-1, r+1, c-1, r, c, r+1),   # 左下角
                (c+1, r+1, c+1, r, c, r+1),   # 右下角
            ]:
                if 0 <= dc < cols and 0 <= dr < rows:
                    if (dc, dr) not in all_room_cells and (dc, dr) not in door_cells:
                        # 两个相邻边都是边界(墙或门)时才放对角墙
                        b1 = (0 <= ec1 < cols and 0 <= er1 < rows and grid[er1][ec1] in (TILE_WALL, TILE_DOOR))
                        b2 = (0 <= ec2 < cols and 0 <= er2 < rows and grid[er2][ec2] in (TILE_WALL, TILE_DOOR))
                        if b1 and b2 and grid[dr][dc] == TILE_EMPTY:
                            grid[dr][dc] = TILE_WALL

    # ── 3b. 墙壁完整性验证 ──
    # 确保房间外轮廓一圈全部有墙体，边角无镂空、无缺口
    for room in rooms:
        for c, r in room.cells:
            # 验证4方向边界：非房间/非门的位置必须是墙
            for nc, nr in [(c-1,r),(c+1,r),(c,r-1),(c,r+1)]:
                if 0 <= nc < cols and 0 <= nr < rows:
                    if (nc, nr) not in all_room_cells and (nc, nr) not in door_cells:
                        if grid[nr][nc] != TILE_WALL:
                            grid[nr][nc] = TILE_WALL
            # 验证对角线角落：两个相邻边都是边界时，角落必须是墙
            for dc, dr, ec1, er1, ec2, er2 in [
                (c-1, r-1, c-1, r, c, r-1),   # 左上角
                (c+1, r-1, c+1, r, c, r-1),   # 右上角
                (c-1, r+1, c-1, r, c, r+1),   # 左下角
                (c+1, r+1, c+1, r, c, r+1),   # 右下角
            ]:
                if 0 <= dc < cols and 0 <= dr < rows:
                    if (dc, dr) not in all_room_cells and (dc, dr) not in door_cells:
                        b1 = (0 <= ec1 < cols and 0 <= er1 < rows and grid[er1][ec1] in (TILE_WALL, TILE_DOOR))
                        b2 = (0 <= ec2 < cols and 0 <= er2 < rows and grid[er2][ec2] in (TILE_WALL, TILE_DOOR))
                        if b1 and b2 and grid[dr][dc] != TILE_WALL:
                            grid[dr][dc] = TILE_WALL

    # ── 4. 确保门外(door_exit)可通行 ──
    for room in rooms:
        ec, er = room.door_exit
        if 0 <= ec < cols and 0 <= er < rows:
            if grid[er][ec] == TILE_WALL:
                grid[er][ec] = TILE_EMPTY

    # ── 4a. 计算房间边界墙壁集合（不可清除）──
    # 房间边界墙 = 8方向邻接任何房间格子的墙壁
    # 走廊连通算法不得清除这些墙壁，防止破坏房间封闭性
    protected_walls = set()
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == TILE_WALL:
                for nc, nr in [(c-1,r),(c+1,r),(c,r-1),(c,r+1),
                               (c-1,r-1),(c+1,r-1),(c-1,r+1),(c+1,r+1)]:
                    if 0 <= nc < cols and 0 <= nr < rows:
                        if (nc, nr) in all_room_cells:
                            protected_walls.add((c, r))
                            break

    # ── 4b. 连通走廊：确保所有走廊区域互相连通 ──
    # 从出生点BFS，找到所有可达的空地；对不可达的空地，清除阻隔墙壁
    # 注意：不得清除房间边界墙壁（protected_walls）
    spawn_c, spawn_r = cols // 2, rows // 2

    # 确保出生地（至少2x2=4格）范围内没有房间格子
    # 注意：不得清除房间边界墙壁（protected_walls），防止破坏房间封闭性
    for dc in range(2):
        for dr in range(2):
            sc, sr = spawn_c + dc, spawn_r + dr
            if 0 <= sc < cols and 0 <= sr < rows:
                if (sc, sr) in all_room_cells:
                    # 出生点范围内有房间格子，清除该房间在此区域内的格子
                    all_room_cells.pop((sc, sr), None)
                    grid[sr][sc] = TILE_EMPTY
                if grid[sr][sc] == TILE_WALL and (sc, sr) not in protected_walls:
                    grid[sr][sc] = TILE_EMPTY

    if 0 <= spawn_c < cols and 0 <= spawn_r < rows:
        if grid[spawn_r][spawn_c] == TILE_WALL and (spawn_c, spawn_r) not in protected_walls:
            grid[spawn_r][spawn_c] = TILE_EMPTY

    def _bfs_empty(start_c, start_r):
        """BFS从指定点找到所有连通的空地"""
        vis = set()
        q = [(start_c, start_r)]
        vis.add((start_c, start_r))
        while q:
            c, r = q.pop(0)
            for nc, nr in [(c-1,r),(c+1,r),(c,r-1),(c,r+1)]:
                if 0 <= nc < cols and 0 <= nr < rows and (nc,nr) not in vis:
                    if grid[nr][nc] in (TILE_EMPTY, TILE_DOOR):
                        vis.add((nc,nr))
                        q.append((nc,nr))
        return vis

    # 找到出生点连通区域
    main_area = _bfs_empty(spawn_c, spawn_r)

    # 对每个门的door_exit，如果不连通，向远离房间方向清除墙壁直到连通
    # door_dir表示房间在门的哪一侧，exit在相反方向，继续沿exit方向清除
    # 注意：不得清除房间边界墙壁
    for room in rooms:
        ec, er = room.door_exit
        if (ec, er) in main_area:
            continue
        dc, dr = 0, 0
        # exit方向 = 远离房间的方向 = door_dir的反方向
        if room.door_dir == 'right': dc = -1
        elif room.door_dir == 'left': dc = 1
        elif room.door_dir == 'up': dr = 1
        elif room.door_dir == 'down': dr = -1

        for step in range(1, 8):
            nc, nr = ec + dc * step, er + dr * step
            if not (0 <= nc < cols and 0 <= nr < rows):
                break
            if (nc, nr) in main_area:
                break
            if grid[nr][nc] == TILE_WALL:
                if (nc, nr) not in protected_walls:
                    grid[nr][nc] = TILE_EMPTY
                else:
                    break  # 房间边界墙不可清除，停止
            if grid[nr][nc] == TILE_EMPTY:
                new_area = _bfs_empty(nc, nr)
                main_area |= new_area
                break

    # ── 4c. 连通所有走廊区域 ──
    # 反复找到不连通的空地，清除墙壁连接到主区域
    # 注意：不得清除房间边界墙壁（protected_walls）
    max_iterations = 200
    for _ in range(max_iterations):
        # 找到所有空地
        all_empty = set()
        for r in range(1, rows - 1):
            for c in range(1, cols - 1):
                if grid[r][c] == TILE_EMPTY:
                    all_empty.add((c, r))

        disconnected = all_empty - main_area
        if not disconnected:
            break  # 所有空地都连通了

        # 找到不连通区域中离主区域最近的点
        found = False
        for c, r in disconnected:
            for nc, nr in [(c-1,r),(c+1,r),(c,r-1),(c,r+1)]:
                if 0 <= nc < cols and 0 <= nr < rows:
                    if (nc, nr) in main_area:
                        # (c,r)与主区域只隔0格(已在边界)
                        main_area.add((c, r))
                        new_area = _bfs_empty(c, r)
                        main_area |= new_area
                        found = True
                        break
                    if grid[nr][nc] == TILE_WALL and nr > 0 and nr < rows-1 and nc > 0 and nc < cols-1:
                        if (nc, nr) in protected_walls:
                            continue  # 房间边界墙不可清除，跳过
                        # 清除这面墙连接
                        grid[nr][nc] = TILE_EMPTY
                        main_area.add((nc, nr))
                        new_area = _bfs_empty(nc, nr)
                        main_area |= new_area
                        found = True
                        break
            if found:
                break

        if not found:
            # 没有直接相邻的，尝试BFS穿过墙壁找最短路径
            # 找disconnected中离main_area最近的点
            best_dist = float('inf')
            best_wall = None
            for c, r in list(disconnected)[:100]:
                for nc, nr in [(c-1,r),(c+1,r),(c,r-1),(c,r+1)]:
                    if 0 <= nc < cols and 0 <= nr < rows:
                        if grid[nr][nc] == TILE_WALL and nr > 0 and nr < rows-1 and nc > 0 and nc < cols-1:
                            if (nc, nr) in protected_walls:
                                continue  # 房间边界墙不可清除，跳过
                            # 检查这面墙的另一侧是否是main_area
                            for nnc, nnr in [(nc-1,nr),(nc+1,nr),(nc,nr-1),(nc,nr+1)]:
                                if (nnc, nnr) in main_area:
                                    dist = abs(nc - spawn_c) + abs(nr - spawn_r)
                                    if dist < best_dist:
                                        best_dist = dist
                                        best_wall = (nc, nr)
            if best_wall:
                wc, wr = best_wall
                grid[wr][wc] = TILE_EMPTY
                main_area.add((wc, wr))
                new_area = _bfs_empty(wc, wr)
                main_area |= new_area
            else:
                break  # 无法再连通

    # ── 5. 外墙边界 ──
    for c in range(cols):
        if grid[0][c] == TILE_EMPTY:
            grid[0][c] = TILE_WALL
        if grid[rows - 1][c] == TILE_EMPTY:
            grid[rows - 1][c] = TILE_WALL
    for r in range(rows):
        if grid[r][0] == TILE_EMPTY:
            grid[r][0] = TILE_WALL
        if grid[r][cols - 1] == TILE_EMPTY:
            grid[r][cols - 1] = TILE_WALL

    return grid, rooms, map_config


def is_walkable_for(grid, col, row, entity_type, door_hp_map=None, rooms=None):
    """检查某格是否可通行"""
    cols = _cfg.MAP_COLS
    rows = _cfg.MAP_ROWS
    if col < 0 or col >= cols or row < 0 or row >= rows:
        return False
    tile = grid[row][col]

    if entity_type == 'hunter':
        if tile in (TILE_EMPTY, TILE_RED_CHANNEL, TILE_SPAWN):
            return True
        if tile == TILE_ROOM:
            if rooms is not None:
                for room in rooms:
                    if room.contains(col, row):
                        if door_hp_map:
                            dc, dr = room.door_pos
                            hp = door_hp_map.get((dc, dr), 1)
                            return hp <= 0
                        return True
            return True
        if tile == TILE_DOOR:
            if door_hp_map:
                hp = door_hp_map.get((col, row), 1)
                return hp <= 0
            return False
        return False

    if entity_type == 'human_wandering':
        # 人类只能通过红色箭头标记进入房间, 不能通过门
        return tile in (TILE_EMPTY, TILE_RED_CHANNEL, TILE_SPAWN, TILE_ROOM, TILE_BED)

    if entity_type == 'human_bed':
        return False

    return False


def get_neighbors(col, row):
    """四方向邻居"""
    return [(col, row-1), (col, row+1), (col-1, row), (col+1, row)]


def heuristic(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


def astar(grid, start, goal, walkable_check, door_hp_map=None, rooms=None):
    """A*寻路"""
    if start == goal:
        return []

    frontier = []
    heapq.heappush(frontier, (0, start))
    came_from = {start: None}
    cost_so_far = {start: 0}

    while frontier:
        _, current = heapq.heappop(frontier)
        if current == goal:
            break
        for nxt in get_neighbors(*current):
            if not is_walkable_for(grid, nxt[0], nxt[1], walkable_check, door_hp_map, rooms):
                continue
            new_cost = cost_so_far[current] + 1
            if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                cost_so_far[nxt] = new_cost
                priority = new_cost + heuristic(goal, nxt)
                heapq.heappush(frontier, (priority, nxt))
                came_from[nxt] = current

    if goal not in came_from:
        return []

    path = []
    cur = goal
    while cur != start:
        path.append(cur)
        cur = came_from[cur]
    path.reverse()
    return path


def find_path(grid, start, goal, entity_type, door_hp_map=None, rooms=None):
    return astar(grid, start, goal, entity_type, door_hp_map, rooms)


def get_room_by_id(rooms, room_id):
    for r in rooms:
        if r.id == room_id:
            return r
    return None


def get_room_at(rooms, col, row):
    """返回(col,row)所在的房间"""
    for room in rooms:
        if room.contains(col, row):
            return room
    return None


def get_door_adjacent_corridor(room, grid):
    """获取门邻接的走廊格子"""
    return room.door_exit


# 苔藓地图猎梦者出生点(四边绿色通道中间缺口)
HUNTER_SPAWN_POINTS_NORMAL = [(18, 0), (18, 38), (0, 19), (32, 19)]

# 雪地地图猎梦者出生点(从 map_snow.json.spawn_points 加载, 此处为后备默认值)
HUNTER_SPAWN_POINTS_SNOW_DEFAULT = [(18, 0), (18, 38), (0, 19), (32, 19)]


def get_hunter_spawn_points(map_type=None):
    """获取猎梦者出生点列表 [(col, row), ...]
    所有地图统一使用 4 个分散出生点(地图四边正中央的"凸出走廊格"):
        顶部 (mid_c, 0) / 底部 (mid_c, rows-1) / 左侧 (0, mid_r) / 右侧 (cols-1, mid_r)
    其中 mid_c=18, mid_r=19 (针对 33x39 地图, 与原始设计一致)
    雪地地图优先从 map_snow.json.spawn_points 加载(以防自定义)
    """
    cols = _cfg.MAP_COLS
    rows = _cfg.MAP_ROWS
    # 33x39 地图使用 (col=18, mid_r=19) 以保持与原设计兼容
    mid_c = 18 if cols >= 33 else cols // 2
    mid_r = 19 if rows >= 39 else rows // 2
    default_pts = [
        (mid_c, 0),            # 顶部
        (mid_c, rows - 1),     # 底部
        (0, mid_r),            # 左侧
        (cols - 1, mid_r),     # 右侧
    ]

    # 雪地地图: 优先从 map_config.spawn_points_cfg 加载(保留自定义能力)
    if map_type == MAP_TYPE_SNOW:
        mc = getattr(_cfg, '_current_map_config', None)
        if mc and getattr(mc, 'spawn_points_cfg', None):
            pts = []
            for sp in mc.spawn_points_cfg:
                c = sp.get('col') if isinstance(sp, dict) else sp[0]
                r = sp.get('row') if isinstance(sp, dict) else sp[1]
                pts.append((int(c), int(r)))
            if pts:
                return pts
        return list(default_pts)

    # 其他地图: 尝试从 map_config.spawn_points_cfg 加载(已自动回写)
    mc = getattr(_cfg, '_current_map_config', None)
    if mc and getattr(mc, 'spawn_points_cfg', None):
        pts = []
        for sp in mc.spawn_points_cfg:
            c = sp.get('col') if isinstance(sp, dict) else sp[0]
            r = sp.get('row') if isinstance(sp, dict) else sp[1]
            pts.append((int(c), int(r)))
        if pts:
            return pts

    return default_pts


def get_door_transitions(map_type=None):
    """获取地图的门滑动对列表 [(blue_pos, red_pos, dir), ...]
    所有地图统一支持门滑入动画(door close), 不再局限于雪地地图"""
    mc = getattr(_cfg, '_current_map_config', None)
    if not mc or not getattr(mc, 'door_pairs', None):
        return []
    result = []
    for dp in mc.door_pairs:
        blue = dp.get('blue')
        red = dp.get('red')
        ddir = dp.get('dir', 'S')
        if blue and red:
            result.append(
                ((int(blue[0]), int(blue[1])), (int(red[0]), int(red[1])), ddir)
            )
    return result


def get_spawn_point():
    """人类出生点: 地图中央的走廊格(自动寻最近空地)"""
    cols = _cfg.MAP_COLS
    rows = _cfg.MAP_ROWS
    spawn_c, spawn_r = cols // 2, rows // 2
    return spawn_c, spawn_r
