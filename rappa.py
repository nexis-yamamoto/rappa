"""
rappa - ABC記法のテキストを再生するプログラム
MIDI再生にも対応
"""

import pygame
import re
import sys
from typing import List, Tuple
from pathlib import Path
from lilypond_converter import convert_lilypond_to_midi_path

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
LILYPOND_MARKERS = ["\\relative", "\\version", "\\score", "\\new", "\\tempo", "\\time", "\\key"]


def looks_like_lilypond(text: str) -> bool:
    """LilyPondらしいテキストか簡易判定する。"""
    stripped = text.strip()
    return any(marker in stripped for marker in LILYPOND_MARKERS)


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
    
    def midi_note_to_frequency(self, note_number: int) -> float:
        """
        MIDIノート番号を周波数に変換
        
        Args:
            note_number: MIDIノート番号 (0-127, A4=69=440Hz)
            
        Returns:
            周波数(Hz)
        """
        return 440.0 * (2 ** ((note_number - 69) / 12))
    
    def play_midi(self, midi_path: str):
        """
        MIDIファイルを再生
        
        Args:
            midi_path: MIDIファイルのパス
        """
        try:
            import mido
        except ImportError:
            print("エラー: midoライブラリがインストールされていません")
            print("インストール: pip install mido または uv add mido")
            return
        
        try:
            mid = mido.MidiFile(midi_path)
        except Exception as e:
            print(f"MIDIファイルの読み込みエラー: {e}")
            return
        
        print(f"MIDI再生中: {midi_path}")
        print(f"トラック数: {len(mid.tracks)}")
        print(f"ティック/ビート: {mid.ticks_per_beat}")
        print(f"総時間: {mid.length:.2f}秒\n")
        
        # 現在再生中のノート情報を管理
        active_notes = {}
        
        for i, track in enumerate(mid.tracks):
            print(f"トラック {i}: {track.name}")
        
        print("\n再生開始...")
        
        # MIDIメッセージを順次処理
        for msg in mid.play():
            if msg.type == 'note_on' and msg.velocity > 0:
                # ノートオン
                frequency = self.midi_note_to_frequency(msg.note)
                # デフォルトの長さを設定（実際の長さはnote_offで決まる）
                duration = 500  # 仮の長さ
                
                sound = self.generate_tone(frequency, duration)
                channel = sound.play()
                
                # アクティブなノートとして記録
                active_notes[msg.note] = {
                    'frequency': frequency,
                    'channel': channel,
                    'sound': sound
                }
                
                print(f"  ノートオン: {msg.note} ({frequency:.2f}Hz) vel={msg.velocity}")
                
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                # ノートオフ
                if msg.note in active_notes:
                    # サウンドを停止
                    channel = active_notes[msg.note]['channel']
                    if channel:
                        channel.stop()
                    del active_notes[msg.note]
                    print(f"  ノートオフ: {msg.note}")
        
        print("\n再生完了")
        
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
    
    def frequency_to_midi_note(self, frequency: float) -> int:
        """
        周波数をMIDIノート番号に変換
        
        Args:
            frequency: 周波数(Hz)
            
        Returns:
            MIDIノート番号 (0-127)
        """
        if frequency == 0:
            return 0
        import math
        # A4=440Hz=MIDIノート69
        note_number = round(69 + 12 * math.log2(frequency / 440.0))
        return max(0, min(127, note_number))  # 0-127に制限
    
    def save_to_midi(self, abc_notation: str, output_path: str, tempo: int = 120):
        """
        ABC記法の文字列をMIDIファイルとして保存
        
        Args:
            abc_notation: ABC記法の文字列
            output_path: 出力MIDIファイルのパス
            tempo: テンポ (BPM, デフォルト120)
        """
        try:
            import mido
            from mido import Message, MidiFile, MidiTrack, MetaMessage
        except ImportError:
            print("エラー: midoライブラリがインストールされていません")
            print("インストール: pip install mido または uv add mido")
            return
        
        # 新しいMIDIファイルとトラックを作成
        mid = MidiFile()
        track = MidiTrack()
        mid.tracks.append(track)
        
        # トラック名とテンポを設定
        track.append(MetaMessage('track_name', name='rappa ABC', time=0))
        track.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo), time=0))
        
        # スペースで分割して各音符を取得
        notes = abc_notation.split()
        
        print(f"MIDI保存中: {output_path}")
        print(f"テンポ: {tempo} BPM")
        
        for note_str in notes:
            frequency, duration = self.parse_note(note_str)
            
            # ミリ秒をMIDIティックに変換 (480 ticks per beat)
            ticks_per_beat = 480
            beats_per_second = tempo / 60.0
            ticks_per_second = ticks_per_beat * beats_per_second
            ticks = int((duration / 1000.0) * ticks_per_second)
            
            if frequency > 0:
                # 音符
                midi_note = self.frequency_to_midi_note(frequency)
                velocity = 64  # 中程度の音量
                
                # ノートオン
                track.append(Message('note_on', note=midi_note, velocity=velocity, time=0))
                # ノートオフ
                track.append(Message('note_off', note=midi_note, velocity=velocity, time=ticks))
                
                print(f"  音符: {note_str} -> MIDI note {midi_note}, {duration}ms")
            else:
                # 休符 (単に時間を進める)
                if len(track) > 0:
                    # 最後のメッセージの時間を延長
                    track[-1].time += ticks
                print(f"  休符: {note_str} -> {duration}ms")
        
        # ファイルに保存
        mid.save(output_path)
        print(f"\nMIDIファイル保存完了: {output_path}")
    
    def play(self, abc_notation: str, save_midi: str = None):
        """
        ABC記法の文字列を再生
        
        Args:
            abc_notation: ABC記法の文字列(例: "C D E F G A B c")
            save_midi: MIDIファイルとして保存する場合のパス (省略可)
        """
        # MIDI保存が指定されている場合
        if save_midi:
            self.save_to_midi(abc_notation, save_midi)
        
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
        print("使用法: python rappa.py <ABC記法の文字列 または MIDIファイルパス> [オプション]")
        print("\nABC記法の例:")
        print("  python rappa.py \"C D E F G A B c\"")
        print("  python rappa.py \"C2 D2 E2 F2 G2 A2 B2 c2\"")
        print("  python rappa.py \"C D E z E F G z\"")
        print("  python rappa.py \"C ^C D _E E\"  # 臨時記号付き")
        print("\nMIDI再生の例:")
        print("  python rappa.py song.mid")
        print("  python rappa.py path/to/music.midi")
        print("\nMIDI保存の例:")
        print("  python rappa.py \"C D E F G A B c\" --save output.mid")
        print("  python rappa.py \"C _E F G\" -s blues.mid")
        sys.exit(1)
    
    # コマンドライン引数を解析
    args = sys.argv[1:]
    save_midi_path = None
    input_parts = []
    
    i = 0
    while i < len(args):
        if args[i] in ['--save', '-s']:
            if i + 1 < len(args):
                save_midi_path = args[i + 1]
                i += 2
            else:
                print("エラー: --save オプションには出力ファイル名が必要です")
                sys.exit(1)
        else:
            input_parts.append(args[i])
            i += 1
    
    input_str = ' '.join(input_parts)
    
    try:
        player = ABCPlayer()
        
        # 入力がファイルパスかどうかをチェック
        input_path = Path(input_str)
        if input_path.exists():
            suffix = input_path.suffix.lower()
            if suffix in ['.mid', '.midi']:
                # MIDIファイルとして再生
                player.play_midi(str(input_path))
            elif suffix in ['.ly', '.lilypond']:
                lily_text = input_path.read_text(encoding="utf-8")
                midi_path = convert_lilypond_to_midi_path(lily_text, output_path=save_midi_path)
                player.play_midi(str(midi_path))
                if not save_midi_path:
                    Path(midi_path).unlink(missing_ok=True)
            else:
                # ABC記法として再生（MIDI保存オプション付き）
                player.play(input_str, save_midi=save_midi_path)
        else:
            if looks_like_lilypond(input_str):
                midi_path = convert_lilypond_to_midi_path(input_str, output_path=save_midi_path)
                player.play_midi(str(midi_path))
                if not save_midi_path:
                    Path(midi_path).unlink(missing_ok=True)
            else:
                # ABC記法として再生（MIDI保存オプション付き）
                player.play(input_str, save_midi=save_midi_path)
            
    except KeyboardInterrupt:
        print("\n中断されました")
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
