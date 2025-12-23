"""
rappa - ABC記法のテキストを再生するプログラム
MIDI出力ポートを使用したMIDI再生に対応
"""

import re
import sys
from typing import Tuple
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


class MIDIPortError(Exception):
    """MIDI出力ポートが利用できない場合のエラー"""
    pass


def looks_like_lilypond(text: str) -> bool:
    """LilyPondらしいテキストか簡易判定する。"""
    stripped = text.strip()
    return any(marker in stripped for marker in LILYPOND_MARKERS)


class ABCPlayer:
    """ABC記法を解析して音楽を再生するクラス（MIDI出力ポート経由）"""
    
    def __init__(self, show_progress: bool = True):
        """
        初期化
        
        Args:
            show_progress: 進行状況を表示するかどうか（CLI: True, MCP: False）
        """
        self.show_progress = show_progress
        self._port = None
    
    def _get_midi_output_port(self):
        """
        MIDI出力ポートを取得
        
        Returns:
            mido.ports.BaseOutput: MIDI出力ポート
            
        Raises:
            MIDIPortError: MIDI出力ポートが利用できない場合
        """
        if self._port is not None:
            return self._port
            
        try:
            import mido
            import rtmidi
        except ImportError as e:
            raise MIDIPortError(
                "エラー: mido または python-rtmidi がインストールされていません\n"
                "インストール: pip install mido python-rtmidi または uv add mido python-rtmidi"
            ) from e
        
        # rtmidiバックエンドを設定
        mido.set_backend('mido.backends.rtmidi')
        
        # 利用可能なMIDI出力ポートを取得
        try:
            output_names = mido.get_output_names()
        except Exception as e:
            raise MIDIPortError(
                "エラー: MIDIシステムの初期化に失敗しました\n"
                f"詳細: {e}\n"
                "MIDI出力デバイス（仮想MIDIドライバやDAW）を起動してください"
            ) from e
        
        if not output_names:
            raise MIDIPortError(
                "エラー: 利用可能なMIDI出力ポートがありません\n"
                "MIDI出力デバイス（仮想MIDIドライバやDAW）を起動してください"
            )
        
        # 最初の利用可能なポートを使用
        port_name = output_names[0]
        if self.show_progress:
            print(f"MIDI出力ポート: {port_name}")
        
        try:
            self._port = mido.open_output(port_name)
        except Exception as e:
            raise MIDIPortError(
                f"エラー: MIDI出力ポート '{port_name}' を開けませんでした\n"
                f"詳細: {e}"
            ) from e
        return self._port
    
    def close(self):
        """MIDIポートを閉じる"""
        if self._port is not None:
            self._port.close()
            self._port = None
    
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
        MIDIファイルをMIDI出力ポート経由で再生
        
        Args:
            midi_path: MIDIファイルのパス
        """
        try:
            import mido
        except ImportError:
            raise MIDIPortError(
                "エラー: midoライブラリがインストールされていません\n"
                "インストール: pip install mido python-rtmidi または uv add mido python-rtmidi"
            )
        
        try:
            mid = mido.MidiFile(midi_path)
        except Exception as e:
            print(f"MIDIファイルの読み込みエラー: {e}")
            return
        
        # MIDI出力ポートを取得
        port = self._get_midi_output_port()
        
        if self.show_progress:
            print(f"MIDI再生中: {midi_path}")
            print(f"トラック数: {len(mid.tracks)}")
            print(f"ティック/ビート: {mid.ticks_per_beat}")
            print(f"総時間: {mid.length:.2f}秒\n")
            
            for i, track in enumerate(mid.tracks):
                print(f"トラック {i}: {track.name}")
            
            print("\n再生開始...")
        
        # MIDIメッセージを順次処理して送信
        for msg in mid.play():
            if not msg.is_meta:
                port.send(msg)
                
                if self.show_progress:
                    if msg.type == 'note_on' and msg.velocity > 0:
                        frequency = self.midi_note_to_frequency(msg.note)
                        print(f"  ノートオン: {msg.note} ({frequency:.2f}Hz) vel={msg.velocity}")
                    elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                        print(f"  ノートオフ: {msg.note}")
        
        if self.show_progress:
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
            raise MIDIPortError(
                "エラー: midoライブラリがインストールされていません\n"
                "インストール: pip install mido python-rtmidi または uv add mido python-rtmidi"
            )
        
        # 新しいMIDIファイルとトラックを作成
        mid = MidiFile()
        track = MidiTrack()
        mid.tracks.append(track)
        
        # トラック名とテンポを設定
        track.append(MetaMessage('track_name', name='rappa ABC', time=0))
        track.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo), time=0))
        
        # スペースで分割して各音符を取得
        notes = abc_notation.split()
        
        if self.show_progress:
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
                
                if self.show_progress:
                    print(f"  音符: {note_str} -> MIDI note {midi_note}, {duration}ms")
            else:
                # 休符 (単に時間を進める)
                if len(track) > 0:
                    # 最後のメッセージの時間を延長
                    track[-1].time += ticks
                if self.show_progress:
                    print(f"  休符: {note_str} -> {duration}ms")
        
        # ファイルに保存
        mid.save(output_path)
        if self.show_progress:
            print(f"\nMIDIファイル保存完了: {output_path}")
    
    def play(self, abc_notation: str, save_midi: str = None):
        """
        ABC記法の文字列をMIDI出力ポート経由で再生
        
        Args:
            abc_notation: ABC記法の文字列(例: "C D E F G A B c")
            save_midi: MIDIファイルとして保存する場合のパス (省略可)
        """
        import tempfile
        
        # MIDI保存が指定されている場合
        if save_midi:
            self.save_to_midi(abc_notation, save_midi)
        
        # 一時的なMIDIファイルを作成して再生
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp:
            temp_path = tmp.name
        
        try:
            self.save_to_midi(abc_notation, temp_path)
            self.play_midi(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)


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
    except MIDIPortError as e:
        print(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
