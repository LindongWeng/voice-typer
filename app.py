#!/usr/bin/env python3
"""
voice-typer 状态栏模式
用法：python app.py
"""

import json
import os
import queue
import threading

import rumps
from dotenv import load_dotenv

from recorder import Recorder
from transcriber import Transcriber
from polisher import Polisher
from injector import inject_text

load_dotenv()

with open(os.path.join(os.path.dirname(__file__), "config.json")) as f:
    CONFIG = json.load(f)

STATE_IDLE = "idle"
STATE_RECORDING = "recording"
STATE_PROCESSING = "processing"

ICONS = {STATE_IDLE: "🎙", STATE_RECORDING: "⏺", STATE_PROCESSING: "⏳"}

POLISH_LABELS = {"raw": "不润色", "light": "轻润色", "heavy": "重润色"}


class VoiceTyperApp(rumps.App):
    def __init__(self):
        super().__init__(ICONS[STATE_IDLE], quit_button=None)
        self._state = STATE_IDLE
        self._state_lock = threading.Lock()
        self._ui_queue = queue.Queue()  # ("title"|"notify"|"overlay", ...)

        initial_style = CONFIG.get("polish_style", "light")
        if not CONFIG.get("polish_enabled", True):
            initial_style = "raw"
        self.polish_style = initial_style

        self.polish_items = {}
        for key, label in POLISH_LABELS.items():
            item = rumps.MenuItem(label, callback=self._make_polish_cb(key))
            self.polish_items[key] = item
        self._update_polish_checkmarks()

        self.menu = [
            rumps.MenuItem("润色模式", callback=None),
            self.polish_items["raw"],
            self.polish_items["light"],
            self.polish_items["heavy"],
            None,
            rumps.MenuItem("退出", callback=lambda _: rumps.quit_application()),
        ]

        self.recorder = Recorder()
        self.polisher = Polisher(style=self.polish_style)
        self.transcriber = None
        self._overlay = None

    # ── timers（run loop 启动后才生效）───────────────────────────
    @rumps.timer(0.08)
    def _flush_ui(self, _):
        while not self._ui_queue.empty():
            msg = self._ui_queue.get_nowait()
            cmd = msg[0]
            if cmd == "title":
                self.title = msg[1]
            elif cmd == "notify":
                rumps.notification("voice-typer", msg[1], msg[2])
            elif cmd == "overlay_recording":
                if self._overlay:
                    self._overlay.show_recording()
            elif cmd == "overlay_processing":
                if self._overlay:
                    self._overlay.show_processing()
            elif cmd == "overlay_hide":
                if self._overlay:
                    self._overlay.hide()

    @rumps.timer(0.5)
    def _startup(self, timer):
        timer.stop()
        # 悬浮窗（主线程创建）
        from overlay import Overlay
        self._overlay = Overlay()
        # 全局热键（CGEventTap，不依赖 pynput）
        from hotkey import HotkeyListener
        HotkeyListener(
            on_hotkey=self.on_hotkey,
            on_escape=self._cancel_recording,
        ).start()
        # 加载模型
        threading.Thread(target=self._load_model, daemon=True).start()

    # ── helpers ──────────────────────────────────────────────────
    def _q(self, *args):
        self._ui_queue.put(args)

    def _get_state(self):
        with self._state_lock:
            return self._state

    def _set_state(self, state):
        with self._state_lock:
            self._state = state
        self._q("title", ICONS[state])

    # ── 模型加载 ─────────────────────────────────────────────────
    def _load_model(self):
        self._q("notify", "启动中…", "模型加载中，请稍候")
        self.transcriber = Transcriber(
            engine=CONFIG.get("engine", "sensevoice"),
            model_size=CONFIG.get("whisper_model", "base"),
            language=CONFIG.get("whisper_language"),
        )
        self._q("notify", "就绪", f"按 {CONFIG['hotkey']} 开始录音")

    # ── 热键 / 按钮回调 ──────────────────────────────────────────
    def on_hotkey(self):
        state = self._get_state()
        if state == STATE_IDLE:
            if self.transcriber is None:
                self._q("notify", "请稍候", "模型还在加载中")
                return
            self._start_recording()
        elif state == STATE_RECORDING:
            self._stop_recording(cancel=False)

    def _cancel_recording(self):
        if self._get_state() == STATE_RECORDING:
            self._stop_recording(cancel=True)

    def _confirm_recording(self):
        if self._get_state() == STATE_RECORDING:
            self._stop_recording(cancel=False)

    # ── 录音流程 ─────────────────────────────────────────────────
    def _start_recording(self):
        self._set_state(STATE_RECORDING)
        self._q("overlay_recording")
        self.recorder.start(on_volume=self._on_volume)

    def _on_volume(self, rms: float):
        """音频回调（后台线程），直接推给波形 view，不过队列"""
        if self._overlay:
            self._overlay.push_volume(rms)

    def _stop_recording(self, cancel=False):
        self._set_state(STATE_PROCESSING)
        wav_path = self.recorder.stop()
        if cancel:
            if wav_path and os.path.exists(wav_path):
                os.unlink(wav_path)
            self._q("overlay_hide")
            self._set_state(STATE_IDLE)
            return
        self._q("overlay_processing")
        threading.Thread(target=self._process, args=(wav_path,), daemon=True).start()

    def _process(self, wav_path):
        try:
            if not wav_path:
                return

            # 转文字
            raw_text = self.transcriber.transcribe(wav_path)
            os.unlink(wav_path)

            if not raw_text:
                self._q("notify", "未识别到内容", "")
                return

            # 润色（如需）
            if self.polisher.style == "raw":
                final_text = raw_text
            else:
                final_text = self.polisher.polish(raw_text) or raw_text

            # 转写+润色完成，立即收起悬浮窗
            self._q("overlay_hide")

            # 注入文字
            pasted = inject_text(final_text)
            if not pasted:
                # 无活动光标：文字已在剪贴板，通知用户手动粘贴
                self._q("notify", "已复制到剪贴板", "请手动 Cmd+V 粘贴")

        except Exception as e:
            self._q("overlay_hide")
            self._q("notify", "出错", str(e))
        finally:
            self._set_state(STATE_IDLE)

    # ── 菜单 ─────────────────────────────────────────────────────
    def _make_polish_cb(self, style):
        def cb(_):
            self.polish_style = style
            self.polisher = Polisher(style=style)
            self._update_polish_checkmarks()
        return cb

    def _update_polish_checkmarks(self):
        for key, item in self.polish_items.items():
            item.state = 1 if key == self.polish_style else 0


if __name__ == "__main__":
    VoiceTyperApp().run()
