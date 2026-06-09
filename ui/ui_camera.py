"""
镜头系统: 跟随/视口变换/坐标转换
屏幕显示 = 视野范围, 渲染到viewport再scale填满屏幕
"""
from core.config import *
import core.config as _cfg

VIEW_RADIUS = 6  # 视野半径(格), 提供约6格范围的局部视野
VIEW_TILES = VIEW_RADIUS * 2 + 1  # 13x13格
VIEWPORT_SIZE = VIEW_TILES * TILE_SIZE  # 416 px


class Camera:
    def __init__(self):
        # 视野中心在地图上的像素坐标
        self.cx = float(_cfg.MAP_COLS * TILE_SIZE // 2)  # 地图中心X(px)
        self.cy = float(_cfg.MAP_ROWS * TILE_SIZE // 2)  # 地图中心Y(px)
        self.target_entity = None
        self.follow_player = True
        self.scale = 1.0  # 由renderer计算

    def reset(self):
        """重置镜头到地图中心"""
        self.cx = float(_cfg.MAP_PIXEL_W // 2)
        self.cy = float(_cfg.MAP_PIXEL_H // 2)
        self.target_entity = None
        self.follow_player = True

    def set_target(self, entity):
        self.target_entity = entity
        self.follow_player = True

    def clear_target(self):
        self.follow_player = False

    def snap_to_entity(self, entity):
        """立即将视野中心对准指定实体"""
        if entity is None:
            return
        self.cx = entity.px
        self.cy = entity.py
        self._clamp()

    def update(self, dt):
        """每帧更新: 跟随目标(lerp平滑插值)"""
        if self.follow_player and self.target_entity:
            tx = self.target_entity.px
            ty = self.target_entity.py
            self.cx += (tx - self.cx) * min(dt * 12, 1.0)
            self.cy += (ty - self.cy) * min(dt * 12, 1.0)
        self._clamp()

    def _clamp(self):
        """限制视野不超出地图范围"""
        half = VIEWPORT_SIZE // 2
        self.cx = max(half, min(_cfg.MAP_PIXEL_W - half, self.cx))
        self.cy = max(half, min(_cfg.MAP_PIXEL_H - half, self.cy))

    @property
    def center_grid(self):
        """视野中心所在的网格坐标"""
        return int(self.cx // TILE_SIZE), int(self.cy // TILE_SIZE)

    @property
    def viewport_map_rect(self):
        """viewport在地图像素坐标中的范围(left, top, width, height)"""
        half = VIEWPORT_SIZE // 2
        left = self.cx - half
        top = self.cy - half
        return left, top, VIEWPORT_SIZE, VIEWPORT_SIZE

    @property
    def viewport_grid_bounds(self):
        """viewport覆盖的网格范围(col_min, row_min, col_max, row_max)"""
        left, top, _, _ = self.viewport_map_rect
        c0 = max(0, int(left // TILE_SIZE))
        r0 = max(0, int(top // TILE_SIZE))
        c1 = min(_cfg.MAP_COLS - 1, int((left + VIEWPORT_SIZE) // TILE_SIZE))
        r1 = min(_cfg.MAP_ROWS - 1, int((top + VIEWPORT_SIZE) // TILE_SIZE))
        return c0, r0, c1, r1

    def screen_to_grid(self, screen_x, screen_y, game_area_x, game_area_y, scale):
        """屏幕点击坐标→地图网格坐标"""
        # 屏幕坐标→viewport坐标
        vx = (screen_x - game_area_x) / scale
        vy = (screen_y - game_area_y) / scale
        # viewport坐标→地图像素坐标
        left, top, _, _ = self.viewport_map_rect
        mx = left + vx
        my = top + vy
        return int(mx // TILE_SIZE), int(my // TILE_SIZE)
