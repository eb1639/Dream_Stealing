"""
本地JSON存档: 难度解锁进度 + 无尽模式最高波数
"""
import json
import os
from core.config import DIFF_EASY, DIFF_PURGATORY, DIFF_ENDLESS

_SAVE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'save.json')


def _default_data():
    return {
        'max_unlocked_difficulty': DIFF_EASY,   # 已解锁的最高难度
        'purgatory_cleared': False,              # 是否通关炼狱
        'endless_best_wave': 0,                  # 无尽模式最高波数
    }


def load_save():
    """读取存档, 文件不存在则返回默认值"""
    try:
        if os.path.exists(_SAVE_PATH):
            with open(_SAVE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 补全缺失字段
            default = _default_data()
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        pass
    return _default_data()


def write_save(data):
    """写入存档"""
    try:
        with open(_SAVE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def is_difficulty_unlocked(difficulty):
    """检查难度是否已解锁"""
    data = load_save()
    if data.get('purgatory_cleared', False):
        return True  # 通关炼狱后全部解锁
    return difficulty <= data.get('max_unlocked_difficulty', DIFF_EASY)


def is_endless_unlocked():
    """无尽模式是否已解锁(通关炼狱后)"""
    data = load_save()
    return data.get('purgatory_cleared', False)


def on_difficulty_cleared(difficulty):
    """通关某个难度后更新存档"""
    data = load_save()
    # 更新最高解锁难度
    if difficulty + 1 <= DIFF_PURGATORY:
        data['max_unlocked_difficulty'] = max(data.get('max_unlocked_difficulty', DIFF_EASY), difficulty + 1)
    # 通关炼狱: 标记全部解锁
    if difficulty == DIFF_PURGATORY:
        data['purgatory_cleared'] = True
    write_save(data)


def update_endless_best_wave(wave):
    """更新无尽模式最高波数"""
    data = load_save()
    if wave > data.get('endless_best_wave', 0):
        data['endless_best_wave'] = wave
        write_save(data)


def get_endless_best_wave():
    """获取无尽模式最高波数"""
    data = load_save()
    return data.get('endless_best_wave', 0)
