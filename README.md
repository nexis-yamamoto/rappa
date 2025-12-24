# rappa

ABC記法のテキストを再生するpythonプログラム

MIDI出力ポートを使用して再生します。OS上のMIDI出力デバイス（仮想MIDIドライバ、DAW、ハードウェア音源など）が必要です。

## 前提条件

- Python 3.10以上
- MIDI出力デバイス（仮想MIDIドライバまたはDAW）が利用可能であること
  - **Windows**: loopMIDI、virtualMIDI、またはDAWの仮想ポート
  - **macOS**: IAC Driver または DAWの仮想ポート
  - **Linux**: ALSA MIDIデバイス または FluidSynth

## 通常の使用方法

### ABC記法で演奏

```bash
python rappa.py "C D E F G A B c"
python rappa.py "C2 D2 E2 F2"
python rappa.py "C D E z E F G z"
python rappa.py "C ^C D _E E"  # 臨時記号付き
```

### MIDIファイルを演奏

```bash
python rappa.py song.mid
uv run rappa.py music.midi
```

### LilyPond (.ly) を演奏

```bash
python rappa.py score.ly
python rappa.py "\\relative c' { c4 d e f }"
```

> 初期実装のため音高・音価・テンポのみ対応（ダイナミクスやアーティキュレーションは無視されます）。

#### LilyPond 打楽器パート（DrumStaff/drummode）対応

LilyPondの`\drummode`および`\DrumStaff`による打楽器記譜をサポートしています。打楽器イベントはMIDIチャンネル10（General MIDI準拠のパーカッションチャンネル）に出力されます。

**対応しているドラム名（LilyPond名 → GM打楽器）:**

| LilyPond名 | GM打楽器 | MIDIノート番号 |
|-----------|---------|--------------|
| `bd` | Acoustic Bass Drum | 36 |
| `sn` | Acoustic Snare | 38 |
| `hh` | Closed Hi-Hat | 42 |
| `hhc` | Closed Hi-Hat | 42 |
| `hho` | Open Hi-Hat | 46 |
| `cymc` | Crash Cymbal 1 | 49 |
| `toml` | Low Tom | 45 |
| `tomm` | Hi-Mid Tom | 48 |
| `tomh` | High Tom | 50 |

**使用例:**

```bash
# 単純なドラムパターン
python rappa.py "\\drummode { bd4 hh sn hh bd hh sn hh }"

# 同時打撃（コード記法）
python rappa.py "\\drummode { <bd hh>4 <sn hho>4 }"

# メロディとドラムの並行パート
python rappa.py "<< \\new Staff { c'4 d' e' f' } \\new DrumStaff \\drummode { bd4 sn hh cymc } >>"
```

**制限事項:**
- 上記リストに含まれないドラム名は警告を出力しスキップされます（エラーにはなりません）
- ベロシティ/アクセントは現在固定値（64）です
- ダイナミクスやロール等の装飾は無視されます

### ABC記法をMIDIファイルとして保存

```bash
python rappa.py "C D E F G A B c" --save output.mid
python rappa.py "C _E F G" -s blues.mid
uv run rappa.py "C D E F G A B c" --save scale.mid
```

保存されたMIDIファイルは、他のDAWソフトや音楽プレーヤーで再生・編集できます。

## MCPサーバーとして使用

rappaをMCP (Model Context Protocol) サーバーとして使用できます。

### 新しいPCでのセットアップ手順

#### 前提条件
- Python 3.10以上がインストールされていること
- [uv](https://github.com/astral-sh/uv)がインストールされていること（推奨）

#### 手順

1. リポジトリをクローン:
```bash
git clone https://github.com/nexis-yamamoto/rappa.git
cd rappa
```

2. **uvを使う場合（推奨）**:
```bash
# 依存関係をインストール
uv add mcp mido python-rtmidi python-ly

# 動作確認
uv run rappa_mcp_server.py
```

3. **pipを使う場合**:
```bash
# 依存関係をインストール
pip install -e .

# 動作確認
python rappa_mcp_server.py
```

#### VS Codeでの設定

VS CodeのMCP設定ファイル（`%APPDATA%\Code\User\mcp.json`）に以下を追加:

```json
{
  "servers": {
    "rappa": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\gits\\rappa",
        "run",
        "rappa_mcp_server.py"
      ],
      "type": "stdio"
    }
  }
}
```

**注意**: `C:\\gits\\rappa`の部分は、あなたの環境でクローンした実際のパスに変更してください。

設定後、VS Codeのコマンドパレット（Ctrl+Shift+P）で「MCP: Restart Server」を実行してサーバーを起動します。

### MCPサーバーの起動（手動テスト）

```bash
python rappa_mcp_server.py
# または
uv run rappa_mcp_server.py
```

### 利用可能なツール

1. **play_abc_notation** - ABC記法の音楽を再生
   - 引数: `abc_notation` (文字列) - ABC記法の文字列
   - 例: `"C D E F G A B c"`

2. **play_lilypond** - LilyPondテキストをMIDIに変換して再生
   - 引数: `lilypond_content` (文字列) - LilyPondのソース
   - 例: `"\\relative c' { c4 d e f }"`

3. **parse_abc_note** - ABC記法の音符を解析
   - 引数: `note` (文字列) - 解析する音符
   - 例: `"C2"`, `"D/2"`, `"z"`

4. **get_note_frequencies** - 利用可能な音符と周波数の一覧を取得

### Claudeデスクトップアプリでの設定

`%APPDATA%\Claude\claude_desktop_config.json` に以下を追加:

```json
{
  "mcpServers": {
    "rappa": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\gits\\rappa",
        "run",
        "rappa_mcp_server.py"
      ]
    }
  }
}
```

**注意**: `C:\\gits\\rappa`の部分は、あなたの環境でクローンした実際のパスに変更してください。

設定後、Claudeデスクトップアプリを再起動してください。

### ABC記法について

- **音符**: C, D, E, F, G, A, B (低いオクターブ), c, d, e, f, g, a, b (高いオクターブ)
- **休符**: z
- **長さ**: 数字を後ろに付けると長くなります (例: C2は2倍)
- **短く**: /数字で短くなります (例: C/2は半分)
- **臨時記号**:
  - `^`: シャープ（半音上げる） 例: `^F`はF#
  - `_`: フラット（半音下げる） 例: `_B`はB♭
  - `=`: ナチュラル（臨時記号を打ち消す） 例: `=A`

## MIDI再生について

rappaは[mido](https://github.com/mido/mido)と[python-rtmidi](https://github.com/SpotlightKid/python-rtmidi)ライブラリを使ってMIDI出力ポート経由で再生します。LilyPond入力も一度MIDIに変換してから再生します。

### 主な機能

1. **MIDIファイルの再生**: 既存のMIDIファイルをMIDI出力ポートに送信して演奏
2. **MIDI保存**: ABC記法で作曲した音楽をMIDIファイルとして保存

### 必要なMIDI出力デバイス

rappaは音を鳴らすために、システムにMIDI出力ポートが必要です。MIDI出力ポートがない場合はエラーが表示されます。

#### 仮想MIDIドライバのセットアップ

- **Windows**: [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html)をインストール
- **macOS**: システム設定 > MIDI設定 > IAC Driverを有効化
- **Linux**: FluidSynthをインストール（`sudo apt install fluidsynth`）

または、DAW（Digital Audio Workstation）の仮想MIDI入力を使用することもできます。

### 技術的な詳細

- **MIDIパース**: `mido`ライブラリでMIDIイベントを解析
- **MIDI出力**: `python-rtmidi`を使用してOSのMIDI出力ポートに送信
- **周波数変換**: MIDIノート番号 ⇔ 周波数の相互変換
  - A4 (440Hz) = MIDIノート番号69を基準
  - 12平均律: `freq = 440 * 2^((note-69)/12)`

### 使用例

```bash
# ブルースを作曲してMIDI保存
uv run rappa.py "C _E F G F _E D C2" --save blues.mid

# 保存したMIDIを再生
uv run rappa.py blues.mid

# 複雑な曲をMIDI保存
uv run rappa.py "C E G c G E C2 D F A d A F D2" -s arpeggio.mid
```
