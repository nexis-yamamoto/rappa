# rappa

ABC記法のテキストを再生するpythonプログラム

再生手段はpygameを使う

## 通常の使用方法

```bash
python rappa.py "C D E F G A B c"
python rappa.py "C2 D2 E2 F2"
python rappa.py "C D E z E F G z"
```

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
uv add mcp pygame numpy

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

2. **parse_abc_note** - ABC記法の音符を解析
   - 引数: `note` (文字列) - 解析する音符
   - 例: `"C2"`, `"D/2"`, `"z"`

3. **get_note_frequencies** - 利用可能な音符と周波数の一覧を取得

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
  - `_`: フラット（半音下げる） 例: `_B`にB♭
  - `=`: ナチュラル（臨時記号を打ち消す） 例: `=A`
