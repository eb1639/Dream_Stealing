"""
AudioManager — 背景音乐 + 音效 + 音量控制

BGM: 优先从 assets/audio/bgm/ 加载 .ogg 文件, 失败时用程序化生成的环境音回退
SFX: 全部由代码程序化生成, 零外部音频文件
"""
import os
import io
import math
import struct
import wave
import random
import pygame

# ─── BGM 轨道名 ───
BGM_MENU = 'menu'
BGM_SAFE = 'safe'
BGM_BATTLE = 'battle'
BGM_BATTLE_INTENSE = 'battle_intense'

# ─── SFX 名 ───
SFX_DOOR_HIT = 'door_hit'
SFX_TURRET_FIRE = 'turret_fire'
SFX_BULLET_HIT = 'bullet_hit'
SFX_HUMAN_DEATH = 'human_death'
SFX_HUNTER_UPGRADE = 'hunter_upgrade'
SFX_DRAGON_SWORD = 'dragon_sword'
SFX_BUTTON_CLICK = 'button_click'
SFX_BUILD_COMPLETE = 'build_complete'
SFX_UPGRADE_COMPLETE = 'upgrade_complete'

# ─── BGM 文件名映射 ───
BGM_FILENAMES = {
    BGM_MENU: 'menu.ogg',
    BGM_SAFE: 'safe.ogg',
    BGM_BATTLE: 'battle.ogg',
    BGM_BATTLE_INTENSE: 'battle_intense.ogg',
}

# 猎梦者升级到该等级后切换为紧张 BGM
HUNTER_INTENSE_LEVEL = 3


class AudioManager:
    """音频管理器: BGM(背景音乐) + SFX(音效) + 音量控制"""

    def __init__(self):
        self.bgm_volume = 0.5
        self.sfx_volume = 0.7
        self.sfx_enabled = True
        self.bgm_enabled = True
        self.current_bgm = None
        self._bgm_channel = None       # 程序化 BGM 播放频道
        self._bgm_is_procedural = False
        self._audio_ok = False
        self.sounds = {}

        # 尝试初始化混音器
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            pygame.mixer.set_num_channels(16)
            self._audio_ok = True
        except pygame.error:
            print("[audio] pygame.mixer 初始化失败, 游戏将以静音模式运行")
            return

        # 生成所有 SFX
        self._generate_sfx()

        # BGM 目录
        self._bgm_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'assets', 'audio', 'bgm'
        )

    @property
    def available(self):
        return self._audio_ok

    # ─── BGM ───

    def play_bgm(self, track_name):
        """播放背景音乐(优先从文件加载, 失败则用程序化回退)"""
        if not self._audio_ok or not self.bgm_enabled:
            return
        if self.current_bgm == track_name:
            return

        self.stop_bgm()

        # 尝试从文件加载
        filepath = os.path.join(self._bgm_dir, BGM_FILENAMES.get(track_name, ''))
        loaded = False
        if os.path.isfile(filepath):
            try:
                pygame.mixer.music.load(filepath)
                pygame.mixer.music.set_volume(self.bgm_volume)
                pygame.mixer.music.play(loops=-1)
                self._bgm_is_procedural = False
                loaded = True
            except pygame.error as e:
                print(f"[audio] 加载 BGM {filepath} 失败({e}), 使用程序化回退")

        if not loaded:
            self._play_procedural_bgm(track_name)

        self.current_bgm = track_name

    def stop_bgm(self):
        """停止背景音乐"""
        if not self._audio_ok:
            return
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except pygame.error:
            pass
        if self._bgm_channel is not None:
            self._bgm_channel.stop()
            self._bgm_channel = None
        self._bgm_is_procedural = False
        self.current_bgm = None

    def pause_bgm(self):
        """暂停背景音乐"""
        if not self._audio_ok:
            return
        if self._bgm_is_procedural and self._bgm_channel:
            self._bgm_channel.pause()
        else:
            try:
                pygame.mixer.music.pause()
            except pygame.error:
                pass

    def unpause_bgm(self):
        """恢复背景音乐"""
        if not self._audio_ok:
            return
        if self._bgm_is_procedural and self._bgm_channel:
            self._bgm_channel.unpause()
        else:
            try:
                pygame.mixer.music.unpause()
            except pygame.error:
                pass

    def set_bgm_volume(self, vol):
        """设置 BGM 音量 (0.0 ~ 1.0)"""
        self.bgm_volume = max(0.0, min(1.0, vol))
        if not self._audio_ok:
            return
        v = self.bgm_volume if self.bgm_enabled else 0
        try:
            pygame.mixer.music.set_volume(v)
        except pygame.error:
            pass
        if self._bgm_channel:
            self._bgm_channel.set_volume(v)

    def toggle_bgm(self):
        """切换 BGM 开关"""
        self.bgm_enabled = not self.bgm_enabled
        v = self.bgm_volume if self.bgm_enabled else 0
        if not self._audio_ok:
            return
        try:
            pygame.mixer.music.set_volume(v)
        except pygame.error:
            pass
        if self._bgm_channel:
            self._bgm_channel.set_volume(v)

    # ─── SFX ───

    def play_sfx(self, name):
        """播放音效"""
        if not self._audio_ok or not self.sfx_enabled:
            return
        sound = self.sounds.get(name)
        if sound:
            sound.set_volume(self.sfx_volume)
            sound.play()

    def set_sfx_volume(self, vol):
        """设置 SFX 音量 (0.0 ~ 1.0)"""
        self.sfx_volume = max(0.0, min(1.0, vol))

    def toggle_sfx(self):
        """切换 SFX 开关"""
        self.sfx_enabled = not self.sfx_enabled

    # ─── 猎梦者升级 BGM 切换 ───

    def update_bgm_for_hunter_level(self, hunter_level):
        """根据猎梦者等级切换 BGM 紧张度"""
        if not self._audio_ok or not self.bgm_enabled:
            return
        if self.current_bgm in (BGM_BATTLE, BGM_BATTLE_INTENSE):
            target = BGM_BATTLE_INTENSE if hunter_level >= HUNTER_INTENSE_LEVEL else BGM_BATTLE
            if self.current_bgm != target:
                self.play_bgm(target)

    # ─── 暂停/恢复全部 ───

    def pause_all(self):
        """暂停所有音频(游戏暂停时调用)"""
        self.pause_bgm()

    def unpause_all(self):
        """恢复所有音频(游戏恢复时调用)"""
        self.unpause_bgm()

    # ─── 程序化 BGM 生成 ───

    def _play_procedural_bgm(self, track_name):
        """用程序化生成的简单环境音作为 BGM 回退"""
        try:
            wav_data = self._generate_bgm_wav(track_name)
            sound = pygame.mixer.Sound(file=wav_data)
            sound.set_volume(self.bgm_volume)
            ch = sound.play(loops=-1)
            self._bgm_channel = ch
            self._bgm_is_procedural = True
        except Exception as e:
            print(f"[audio] 程序化 BGM 生成失败({e}), 静音运行")

    def _generate_bgm_wav(self, track_name):
        """生成简单环境音 WAV (BytesIO)"""
        sr = 44100
        duration = 12.0
        n = int(sr * duration)
        samples = []

        for i in range(n):
            t = i / sr
            val = 0.0

            if track_name == BGM_MENU:
                val = 0.12 * math.sin(2 * math.pi * 110 * t)
                val += 0.08 * math.sin(2 * math.pi * 164.81 * t)
                val += 0.06 * math.sin(2 * math.pi * 220 * t)
                val *= 0.5 + 0.5 * math.sin(2 * math.pi * 0.15 * t)

            elif track_name == BGM_SAFE:
                val = 0.10 * math.sin(2 * math.pi * 130.81 * t)
                val += 0.08 * math.sin(2 * math.pi * 196 * t)
                val += 0.06 * math.sin(2 * math.pi * 261.63 * t)
                val += 0.03 * math.sin(2 * math.pi * 523.25 * t)
                val *= 0.5 + 0.5 * math.sin(2 * math.pi * 0.25 * t)
                val *= 0.8 + 0.2 * math.sin(2 * math.pi * 1.5 * t)

            elif track_name == BGM_BATTLE:
                val = 0.12 * math.sin(2 * math.pi * 146.83 * t)
                val += 0.10 * math.sin(2 * math.pi * 207.65 * t)
                val += 0.08 * math.sin(2 * math.pi * 293.66 * t)
                val += 0.04 * math.sin(2 * math.pi * 440 * t)
                val *= 0.5 + 0.5 * math.sin(2 * math.pi * 2.0 * t)
                val *= 0.7 + 0.3 * math.sin(2 * math.pi * 4.0 * t)

            elif track_name == BGM_BATTLE_INTENSE:
                val = 0.14 * math.sin(2 * math.pi * 146.83 * t)
                val += 0.12 * math.sin(2 * math.pi * 207.65 * t)
                val += 0.10 * math.sin(2 * math.pi * 293.66 * t)
                val += 0.06 * math.sin(2 * math.pi * 415.30 * t)
                val += 0.04 * math.sin(2 * math.pi * 587.33 * t)
                val *= 0.5 + 0.5 * math.sin(2 * math.pi * 3.0 * t)
                val *= 0.6 + 0.4 * math.sin(2 * math.pi * 6.0 * t)

            sample = max(-32767, min(32767, int(val * 32767)))
            samples.append(sample)

        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(struct.pack(f'<{len(samples)}h', *samples))
        buf.seek(0)
        return buf

    # ─── 程序化 SFX 生成 ───

    def _generate_sfx(self):
        """程序化生成所有音效"""
        self.sounds = {
            SFX_DOOR_HIT: self._make_door_hit(),
            SFX_TURRET_FIRE: self._make_turret_fire(),
            SFX_BULLET_HIT: self._make_bullet_hit(),
            SFX_HUMAN_DEATH: self._make_human_death(),
            SFX_HUNTER_UPGRADE: self._make_hunter_upgrade(),
            SFX_DRAGON_SWORD: self._make_dragon_sword(),
            SFX_BUTTON_CLICK: self._make_button_click(),
            SFX_BUILD_COMPLETE: self._make_build_complete(),
            SFX_UPGRADE_COMPLETE: self._make_upgrade_complete(),
        }

    def _synth(self, freq, dur, vol=0.5, wave_type='sine', attack=0.005, release=0.05):
        """合成一个音调, 返回 pygame.mixer.Sound"""
        sr = 44100
        n = int(sr * dur)
        buf = bytearray(n * 2)
        for i in range(n):
            t = i / sr
            if wave_type == 'sine':
                v = math.sin(2 * math.pi * freq * t)
            elif wave_type == 'square':
                v = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
            elif wave_type == 'saw':
                v = 2.0 * (t * freq - math.floor(t * freq + 0.5))
            elif wave_type == 'noise':
                v = random.uniform(-1, 1)
            else:
                v = math.sin(2 * math.pi * freq * t)
            env = 1.0
            if t < attack:
                env = t / attack
            if t > dur - release:
                env = min(env, (dur - t) / release)
            v *= vol * env
            s = max(-32767, min(32767, int(v * 32767)))
            struct.pack_into('<h', buf, i * 2, s)
        return pygame.mixer.Sound(buffer=bytes(buf))

    def _make_door_hit(self):
        """门被击打: 低频闷响"""
        sr = 44100
        dur = 0.15
        n = int(sr * dur)
        buf = bytearray(n * 2)
        for i in range(n):
            t = i / sr
            v = 0.4 * math.sin(2 * math.pi * 80 * t)
            v += 0.2 * random.uniform(-1, 1) * max(0, 1 - t / 0.03)
            env = max(0, 1 - t / dur)
            v *= env
            s = max(-32767, min(32767, int(v * 32767)))
            struct.pack_into('<h', buf, i * 2, s)
        return pygame.mixer.Sound(buffer=bytes(buf))

    def _make_turret_fire(self):
        """炮塔开火: 短促高频"""
        sr = 44100
        dur = 0.1
        n = int(sr * dur)
        buf = bytearray(n * 2)
        for i in range(n):
            t = i / sr
            v = 0.3 * math.sin(2 * math.pi * 800 * t * max(0.2, 1 - t / dur))
            v += 0.15 * random.uniform(-1, 1) * max(0, 1 - t / 0.02)
            env = max(0, 1 - t / dur)
            v *= env
            s = max(-32767, min(32767, int(v * 32767)))
            struct.pack_into('<h', buf, i * 2, s)
        return pygame.mixer.Sound(buffer=bytes(buf))

    def _make_bullet_hit(self):
        """子弹命中: 金属撞击"""
        sr = 44100
        dur = 0.12
        n = int(sr * dur)
        buf = bytearray(n * 2)
        for i in range(n):
            t = i / sr
            v = 0.25 * math.sin(2 * math.pi * 1200 * t * max(0.3, 1 - t / dur))
            v += 0.15 * math.sin(2 * math.pi * 600 * t)
            v += 0.1 * random.uniform(-1, 1) * max(0, 1 - t / 0.03)
            env = max(0, 1 - t / dur)
            v *= env
            s = max(-32767, min(32767, int(v * 32767)))
            struct.pack_into('<h', buf, i * 2, s)
        return pygame.mixer.Sound(buffer=bytes(buf))

    def _make_human_death(self):
        """人类死亡: 下降音调"""
        sr = 44100
        dur = 0.4
        n = int(sr * dur)
        buf = bytearray(n * 2)
        for i in range(n):
            t = i / sr
            freq = 400 - 300 * (t / dur)
            v = 0.3 * math.sin(2 * math.pi * freq * t)
            v += 0.1 * math.sin(2 * math.pi * freq * 0.5 * t)
            env = max(0, 1 - t / dur)
            v *= env
            s = max(-32767, min(32767, int(v * 32767)))
            struct.pack_into('<h', buf, i * 2, s)
        return pygame.mixer.Sound(buffer=bytes(buf))

    def _make_hunter_upgrade(self):
        """猎梦者升级: 上升琶音警告"""
        sr = 44100
        dur = 0.5
        n = int(sr * dur)
        buf = bytearray(n * 2)
        notes = [(0.0, 200), (0.15, 300), (0.3, 450)]
        for i in range(n):
            t = i / sr
            v = 0.0
            for start, freq in notes:
                if t >= start:
                    lt = t - start
                    local_dur = dur - start
                    v += 0.25 * math.sin(2 * math.pi * freq * lt) * max(0, 1 - lt / local_dur)
            env = max(0, 1 - t / dur) ** 0.5
            v *= env
            s = max(-32767, min(32767, int(v * 32767)))
            struct.pack_into('<h', buf, i * 2, s)
        return pygame.mixer.Sound(buffer=bytes(buf))

    def _make_dragon_sword(self):
        """屠龙刀: 强力斩击"""
        sr = 44100
        dur = 0.35
        n = int(sr * dur)
        buf = bytearray(n * 2)
        for i in range(n):
            t = i / sr
            freq = 1000 - 700 * (t / dur)
            v = 0.35 * math.sin(2 * math.pi * freq * t)
            v += 0.2 * random.uniform(-1, 1) * max(0, 1 - t / 0.05)
            v += 0.1 * math.sin(2 * math.pi * 150 * t)
            env = max(0, 1 - t / dur)
            v *= env
            s = max(-32767, min(32767, int(v * 32767)))
            struct.pack_into('<h', buf, i * 2, s)
        return pygame.mixer.Sound(buffer=bytes(buf))

    def _make_button_click(self):
        """按钮点击: 短促清脆"""
        return self._synth(600, 0.05, 0.3, 'sine', 0.002, 0.02)

    def _make_build_complete(self):
        """建造完成: 满足感音效"""
        sr = 44100
        dur = 0.25
        n = int(sr * dur)
        buf = bytearray(n * 2)
        for i in range(n):
            t = i / sr
            v = 0.25 * math.sin(2 * math.pi * 523.25 * t)
            v += 0.2 * math.sin(2 * math.pi * 659.25 * t)
            env = max(0, 1 - t / dur)
            v *= env
            s = max(-32767, min(32767, int(v * 32767)))
            struct.pack_into('<h', buf, i * 2, s)
        return pygame.mixer.Sound(buffer=bytes(buf))

    def _make_upgrade_complete(self):
        """升级完成: 上升和弦"""
        sr = 44100
        dur = 0.3
        n = int(sr * dur)
        buf = bytearray(n * 2)
        for i in range(n):
            t = i / sr
            freq = 400 + 200 * (t / dur)
            v = 0.25 * math.sin(2 * math.pi * freq * t)
            v += 0.15 * math.sin(2 * math.pi * freq * 1.5 * t)
            env = max(0, 1 - t / dur) ** 0.7
            v *= env
            s = max(-32767, min(32767, int(v * 32767)))
            struct.pack_into('<h', buf, i * 2, s)
        return pygame.mixer.Sound(buffer=bytes(buf))
