"""
基于 CGEventTap 的全局热键监听
热键：Ctrl+Shift 同时按（释放后可再次触发）
取消：Esc
"""

import threading

from Quartz import (
    CGEventTapCreate, kCGSessionEventTap, kCGHeadInsertEventTap,
    CGEventTapEnable, CFMachPortCreateRunLoopSource,
    CGEventMaskBit, CGEventGetFlags, CGEventGetIntegerValueField,
    kCGEventFlagsChanged, kCGEventKeyDown, kCGKeyboardEventKeycode,
    kCGEventFlagMaskControl, kCGEventFlagMaskShift,
    kCGEventFlagMaskCommand, kCGEventFlagMaskAlternate,
)
from CoreFoundation import (
    CFRunLoopGetCurrent, CFRunLoopAddSource, CFRunLoopRun,
    kCFRunLoopCommonModes,
)

ESC_KEYCODE = 53
# listen-only tap 不会因 callback 耗时被 macOS 自动禁用
_TAP_LISTEN_ONLY = 0x00000001


class HotkeyListener:
    def __init__(self, on_hotkey, on_escape=None):
        self._on_hotkey = on_hotkey
        self._on_escape = on_escape
        self._last_both = False

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        mask = (
            CGEventMaskBit(kCGEventFlagsChanged) |
            CGEventMaskBit(kCGEventKeyDown)
        )
        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            _TAP_LISTEN_ONLY,
            mask,
            self._callback,
            None,
        )
        if not tap:
            print("[HotkeyListener] 无法创建事件监听，请在系统设置→隐私→辅助功能中授权终端")
            return

        print("[HotkeyListener] 热键监听已启动（Ctrl+Shift = 开始/停止，Esc = 取消）")
        source = CFMachPortCreateRunLoopSource(None, tap, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopCommonModes)
        CGEventTapEnable(tap, True)
        CFRunLoopRun()

    def _callback(self, proxy, event_type, event, refcon):
        try:
            if event_type == kCGEventFlagsChanged:
                flags = CGEventGetFlags(event)
                ctrl  = bool(flags & kCGEventFlagMaskControl)
                shift = bool(flags & kCGEventFlagMaskShift)
                cmd   = bool(flags & kCGEventFlagMaskCommand)
                alt   = bool(flags & kCGEventFlagMaskAlternate)

                both = ctrl and shift and not cmd and not alt
                if both and not self._last_both:
                    # 派发到新线程，避免阻塞 run loop
                    threading.Thread(target=self._on_hotkey, daemon=True).start()
                self._last_both = both

            elif event_type == kCGEventKeyDown:
                keycode = int(CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode))
                if keycode == ESC_KEYCODE and self._on_escape:
                    threading.Thread(target=self._on_escape, daemon=True).start()
        except Exception as e:
            print(f"[HotkeyListener] callback 异常: {e}")

        return event
