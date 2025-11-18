"""
rappa - ABC記法のテキストを再生するプログラム
"""

import pygame
import re
import sys
from typing import List, Tuple

# 音符の長さ（ミリ秒）
BASE_DURATION = 500  # 四分音符の長さ

# ABC記法の音符から周波数への変換テーブル
NOTE_FREQUENCIES = {
    'C': 261.63, 'D': 293.66, 'E': 329.63, 'F': 349.23,
    'G': 392.00, 'A': 440.00, 'B': 493.88,
    'c': 523.25, 'd': 587.33, 'e': 659.25, 'f': 698.46,
    'g': 783.99, 'a': 880.00, 'b': 987.77,
}

# 半音の周波数比（12平均律）
SEMITONE_RATIO = 2 ** (1/12)


class ABCPlayer:
    """ABC記法を解析して音楽を再生するクラス"""
    
    def __init__(self, sample_rate: int = 22050):
        """
        初期化
        
        Args:
            sample_rate: サンプリングレート
        """
        pygame.mixer.init(frequency=sample_rate, size=-16, channels=1, buffer=512)
        self.sample_rate = sample_rate
        
    def parse_note(self, note_str: str) -> Tuple[float, int]:
        """
        ABC記法の音符文字列を解析
        
        Args:
            note_str: 音符文字列（例: "C2", "D/2", "E", "^F", "_B", "=A"）
            
        Returns:
            (周波数, 長さ) のタプル
        """
        # 休符の処理
        if note_str.startswith('z'):
            duration_str = note_str[1:] if len(note_str) > 1 else ""
            duration = self._parse_duration(duration_str)
            return (0, duration)
        
        # 音符の処理（臨時記号対応: ^はシャープ、_はフラット、=はナチュラル）
        note_match = re.match(r'([\^_=]?)([A-Ga-g])([/\d]*)', note_str)
        if not note_match:
            return (0, BASE_DURATION)
        
        accidental = note_match.group(1)  # 臨時記号
        note_name = note_match.group(2)   # 音符名
        duration_str = note_match.group(3) # 長さ
        
        # 基本周波数を取得
        frequency = NOTE_FREQUENCIES.get(note_name, 0)
        
        # 臨時記号の処理
        if accidental == '^':  # シャープ（半音上げる）
            frequency *= SEMITONE_RATIO
        elif accidental == '_':  # フラット（半音下げる）
            frequency /= SEMITONE_RATIO
        # '='はナチュラルなので何もしない
        
        duration = self._parse_duration(duration_str)
        
        return (frequency, duration)
    
    def _parse_duration(self, duration_str: str) -> int:
        """
        長さ記号を解析してミリ秒に変換
        
        Args:
            duration_str: 長さ記号（例: "2", "/2", ""）
            
        Returns:
            長さ（ミリ秒）
        """
        if not duration_str:
            return BASE_DURATION
        
        if duration_str.startswith('/'):
            # 分数記号(短くする)
            divisor = int(duration_str[1:]) if len(duration_str) > 1 else 2
            return BASE_DURATION // divisor
        else:
            # 数字(長くする)
            multiplier = int(duration_str)
            return BASE_DURATION * multiplier
    
    def generate_tone(self, frequency: float, duration: int) -> pygame.mixer.Sound:
        """
        指定された周波数と長さの音を生成
        
        Args:
            frequency: 周波数(Hz)
            duration: 長さ(ミリ秒)
            
        Returns:
            pygame.mixer.Sound オブジェクト
        """
        import numpy as np
        
        # 休符の場合
        if frequency == 0:
            samples = np.zeros(int(duration * self.sample_rate / 1000))
        else:
            # 正弦波を生成
            num_samples = int(duration * self.sample_rate / 1000)
            sample_array = np.arange(num_samples)
            waveform = np.sin(2 * np.pi * frequency * sample_array / self.sample_rate)
            
            # エンベロープを適用（フェードアウト）
            envelope = np.ones(num_samples)
            fade_length = min(int(num_samples * 0.1), 1000)
            envelope[-fade_length:] = np.linspace(1, 0, fade_length)
            
            samples = (waveform * envelope * 32767).astype(np.int16)
        
        # ステレオに変換
        stereo_samples = np.zeros((len(samples), 2), dtype=np.int16)
        stereo_samples[:, 0] = samples
        stereo_samples[:, 1] = samples
        
        return pygame.mixer.Sound(stereo_samples)
    
    def play(self, abc_notation: str):
        """
        ABC記法の文字列を再生
        
        Args:
            abc_notation: ABC記法の文字列(例: "C D E F G A B c")
        """
        # スペースで分割して各音符を取得
        notes = abc_notation.split()
        
        print(f"再生中: {abc_notation}")
        
        for note_str in notes:
            frequency, duration = self.parse_note(note_str)
            
            if frequency > 0:
                print(f"  音符: {note_str} -> {frequency:.2f}Hz, {duration}ms")
            else:
                print(f"  休符: {note_str} -> {duration}ms")
            
            sound = self.generate_tone(frequency, duration)
            sound.play()
            
            # 音が終わるまで待機
            pygame.time.wait(duration)
        
        print("再生完了")


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使用法: python rappa.py <ABC記法の文字列>")
        print("例: python rappa.py \"C D E F G A B c\"")
        print("例: python rappa.py \"C2 D2 E2 F2 G2 A2 B2 c2\"")
        print("例: python rappa.py \"C D E z E F G z\"")
        print("例: python rappa.py \"C ^C D _E E\"  # 臨時記号付き")
        sys.exit(1)
    
    abc_notation = ' '.join(sys.argv[1:])
    
    try:
        player = ABCPlayer()
        player.play(abc_notation)
    except KeyboardInterrupt:
        print("\n中断されました")
    except Exception as e:
        print(f"エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
