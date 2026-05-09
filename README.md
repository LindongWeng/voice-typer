# VoiceTyper

macOS 个人语音听写工具，Typeless / SuperWhisper 的开源平替。

按下热键说话，松开自动转文字并粘贴到当前光标位置。支持中英文混说，AI 润色去除口头禅。

## 功能

- **本地语音识别**：SenseVoice（阿里 DAMO，中英混说准确率高）
- **AI 润色**：Groq API（llama-3.1-8b-instant，< 1 秒响应）
- **实时波形**：录音时显示音量响应的悬浮波形窗
- **状态栏图标**：🎙 空闲 / ⏺ 录音中 / ⏳ 处理中
- **智能注入**：自动 Cmd+V 粘贴，无光标时复制到剪贴板

## 快捷键

| 操作 | 热键 |
|------|------|
| 开始 / 停止录音 | `Ctrl + Shift` |
| 取消录音 | `Esc` |

## 安装

**依赖环境**：macOS，Python 3.10+，Apple Silicon 或 Intel

```bash
git clone https://github.com/LindongWeng/voice-typer.git
cd voice-typer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**配置 API Key**（Groq 免费注册）：

```bash
cp .env.example .env
# 编辑 .env，填入 GROQ_API_KEY
```

**首次运行**（会自动下载 SenseVoice 模型 ~300MB）：

```bash
python app.py
```

**辅助功能授权**：系统设置 → 隐私与安全性 → 辅助功能 → 添加终端或 VoiceTyper.app

## 配置

编辑 `config.json`：

```json
{
  "engine": "sensevoice",
  "hotkey": "ctrl+shift",
  "polish_enabled": true,
  "polish_style": "light"
}
```

| 字段 | 说明 |
|------|------|
| `engine` | `sensevoice`（推荐）或 `whisper` |
| `hotkey` | 热键，格式同 CGEventTap |
| `polish_enabled` | 是否启用 AI 润色 |
| `polish_style` | `raw` / `light` / `heavy` |

## 开机自启（可选）

```bash
# 创建 launchd 服务
cp com.voicetyper.plist.example ~/Library/LaunchAgents/com.voicetyper.plist
# 编辑 plist，替换路径为实际路径
launchctl load ~/Library/LaunchAgents/com.voicetyper.plist
```

## 技术栈

- 语音识别：[FunASR SenseVoice](https://github.com/FunAudioLLM/SenseVoice)
- AI 润色：[Groq](https://groq.com) + llama-3.1-8b-instant
- 状态栏：[rumps](https://github.com/jaredks/rumps)
- 热键：macOS CGEventTap（PyObjC）
- 悬浮窗：PyObjC NSWindow + 自定义 NSView

## License

MIT
