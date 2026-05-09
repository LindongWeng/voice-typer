#!/usr/bin/env python3
"""
voice-typer：语音听写工具
用法：python main.py
热键：Ctrl+Space 开始/停止录音，Esc 取消
"""

import json
import os
import sys
import threading

from dotenv import load_dotenv
from pynput import keyboard

from recorder import Recorder
from transcriber import Transcriber
from polisher import Polisher
from injector import inject_text

load_dotenv()

with open(os.path.join(os.path.dirname(__file__), "config.json")) as f:
    CONFIG = json.load(f)

# 状态
STATE_IDLE = "idle"
STATE_RECORDING = "recording"
STATE_PROCESSING = "processing"


class VoiceTyper:
    def __init__(self):
        self.state = STATE_IDLE
        self._lock = threading.Lock()
        self._cancelled = False

        self.recorder = Recorder()
        self.transcriber = Transcriber(
            engine=CONFIG.get("engine", "sensevoice"),
            model_size=CONFIG.get("whisper_model", "base"),
            language=CONFIG.get("whisper_language"),
        )
        polish_style = CONFIG.get("polish_style", "light")
        if not CONFIG.get("polish_enabled", True):
            polish_style = "raw"
        self.polisher = Polisher(style=polish_style)

        print("=" * 40)
        print("voice-typer 启动")
        print(f"引擎: {CONFIG.get('engine', 'sensevoice')}")
        print(f"润色模式: {polish_style}")
        print(f"热键: {CONFIG['hotkey']}  开始/停止")
        print(f"取消: Esc")
        print("=" * 40)

    def _set_state(self, state):
        with self._lock:
            self.state = state

    def _get_state(self):
        with self._lock:
            return self.state

    def on_hotkey(self):
        state = self._get_state()
        if state == STATE_IDLE:
            self._start_recording()
        elif state == STATE_RECORDING:
            self._stop_recording(cancel=False)
        # processing 时忽略热键

    def on_escape(self):
        state = self._get_state()
        if state == STATE_RECORDING:
            print("\n[取消] 录音已取消")
            self._stop_recording(cancel=True)

    def _start_recording(self):
        self._cancelled = False
        self._set_state(STATE_RECORDING)
        print("\n● 录音中... (按热键停止，Esc 取消)")
        self.recorder.start()

    def _stop_recording(self, cancel=False):
        self._set_state(STATE_PROCESSING)
        wav_path = self.recorder.stop()
        if cancel:
            if wav_path and os.path.exists(wav_path):
                os.unlink(wav_path)
            self._set_state(STATE_IDLE)
            return
        threading.Thread(target=self._process, args=(wav_path,), daemon=True).start()

    def _process(self, wav_path):
        try:
            if not wav_path:
                print("[!] 录音为空")
                return

            print("  转文字中...")
            text = self.transcriber.transcribe(wav_path)
            os.unlink(wav_path)
            print(f"  原始: {text}")

            if not text:
                print("[!] 无内容")
                return

            polish_style = self.polisher.style
            if polish_style != "raw":
                print(f"  润色中 ({polish_style})...")
                text = self.polisher.polish(text)
                print(f"  润色: {text}")

            inject_text(text)
            print("✓ 已注入")
        finally:
            self._set_state(STATE_IDLE)

    def run(self):
        hotkey_str = CONFIG["hotkey"]
        listener = keyboard.GlobalHotKeys({hotkey_str: self.on_hotkey})
        listener.start()

        # 单独监听 Esc
        def on_key(key):
            if key == keyboard.Key.esc:
                self.on_escape()

        esc_listener = keyboard.Listener(on_press=on_key)
        esc_listener.start()

        print(f"等待热键 {hotkey_str}...")
        listener.join()


if __name__ == "__main__":
    vt = VoiceTyper()
    vt.run()
