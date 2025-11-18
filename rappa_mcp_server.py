"""
rappa MCP Server - ABC記法で音楽を再生するMCPサーバー
"""

import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server
from rappa import ABCPlayer
import json


# MCPサーバーのインスタンスを作成
app = Server("rappa-music-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """利用可能なツールのリストを返す"""
    return [
        Tool(
            name="play_abc_notation",
            description="ABC記法の音楽を再生します。音符はスペース区切りで指定してください。例: 'C D E F G A B c'。数字で長さを指定できます（例: C2は2倍の長さ）。/で短くできます（例: C/2は半分の長さ）。zは休符です。臨時記号: ^でシャープ、_でフラット、=でナチュラル。",
            inputSchema={
                "type": "object",
                "properties": {
                    "abc_notation": {
                        "type": "string",
                        "description": "ABC記法の文字列（例: 'C D E F G A B c'）",
                    },
                },
                "required": ["abc_notation"],
            },
        ),
        Tool(
            name="parse_abc_note",
            description="ABC記法の音符を解析して、周波数と長さの情報を返します。臨時記号（^, _, =）にも対応。",
            inputSchema={
                "type": "object",
                "properties": {
                    "note": {
                        "type": "string",
                        "description": "ABC記法の音符（例: 'C', 'D2', 'E/2', 'z', '^F', '_B', '=A'）",
                    },
                },
                "required": ["note"],
            },
        ),
        Tool(
            name="get_note_frequencies",
            description="利用可能な音符とその周波数の一覧を返します。",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """ツールの呼び出しを処理"""
    
    if name == "play_abc_notation":
        abc_notation = arguments.get("abc_notation", "")
        if not abc_notation:
            return [TextContent(type="text", text="エラー: ABC記法の文字列が指定されていません")]
        
        try:
            # 新しいイベントループで実行（pygameはメインスレッドで実行する必要がある）
            player = ABCPlayer()
            
            # 再生情報を収集
            notes = abc_notation.split()
            note_info = []
            
            for note_str in notes:
                frequency, duration = player.parse_note(note_str)
                if frequency > 0:
                    note_info.append(f"{note_str}: {frequency:.2f}Hz, {duration}ms")
                else:
                    note_info.append(f"{note_str}: 休符, {duration}ms")
            
            # 実際に再生
            player.play(abc_notation)
            
            result = f"再生完了: {abc_notation}\n\n再生した音符:\n" + "\n".join(note_info)
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"エラー: {str(e)}")]
    
    elif name == "parse_abc_note":
        note = arguments.get("note", "")
        if not note:
            return [TextContent(type="text", text="エラー: 音符が指定されていません")]
        
        try:
            player = ABCPlayer()
            frequency, duration = player.parse_note(note)
            
            if frequency > 0:
                result = f"音符: {note}\n周波数: {frequency:.2f}Hz\n長さ: {duration}ms ({duration/1000:.2f}秒)"
            else:
                result = f"休符: {note}\n長さ: {duration}ms ({duration/1000:.2f}秒)"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"エラー: {str(e)}")]
    
    elif name == "get_note_frequencies":
        from rappa import NOTE_FREQUENCIES
        
        result = "利用可能な音符と周波数:\n\n"
        result += "低いオクターブ (大文字):\n"
        for note in ['C', 'D', 'E', 'F', 'G', 'A', 'B']:
            freq = NOTE_FREQUENCIES[note]
            result += f"  {note}: {freq:.2f}Hz\n"
        
        result += "\n高いオクターブ (小文字):\n"
        for note in ['c', 'd', 'e', 'f', 'g', 'a', 'b']:
            freq = NOTE_FREQUENCIES[note]
            result += f"  {note}: {freq:.2f}Hz\n"
        
        result += "\nその他:\n"
        result += "  z: 休符\n"
        result += "\n臨時記号:\n"
        result += "  ^: シャープ（半音上げる） 例: ^FはF#\n"
        result += "  _: フラット（半音下げる） 例: _BにB♭\n"
        result += "  =: ナチュラル（臨時記号を打ち消す） 例: =A\n"
        result += "\n長さの指定:\n"
        result += "  数字を後ろに付けると長くなります (例: C2は2倍)\n"
        result += "  /数字で短くなります (例: C/2は半分)\n"
        
        return [TextContent(type="text", text=result)]
    
    else:
        return [TextContent(type="text", text=f"エラー: 不明なツール '{name}'")]


async def main():
    """メイン関数 - stdio経由でMCPサーバーを起動"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
