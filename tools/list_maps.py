"""一次性脚本: 列出所有地图的规模/房间/门/出生点情况."""
import json
import os

for f in ['map_easy.json', 'map_normal.json', 'map_snow.json', 'map_hell.json']:
    path = os.path.join('world', 'config', f)
    with open(path, encoding='utf-8') as fp:
        d = json.load(fp)
    matrix = d.get('matrix', [])
    rows = len(matrix)
    cols = len(matrix[0]) if rows else 0
    print(f"{f:20s}  type={d.get('map_type'):8s}  "
          f"size={d.get('grid_width')}x{d.get('grid_height')}  "
          f"matrix={rows}x{cols}  rooms={d.get('room_count')}")
