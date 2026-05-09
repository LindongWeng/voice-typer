"""
悬浮录音提示窗 — 纯波形版（无按钮，操作靠热键）
Ctrl+Shift 开始/停止，Esc 取消
"""

import math
import objc
from AppKit import (
    NSWindow, NSView, NSColor, NSBezierPath,
    NSFloatingWindowLevel, NSBorderlessWindowMask, NSBackingStoreBuffered,
    NSScreen,
)
from Foundation import NSMakeRect, NSObject, NSTimer

# ── 尺寸 ─────────────────────────────────────────────────────────
W, H   = 160, 36
RADIUS = 18.0
Y_BASE = 110
N_BARS = 7
BAR_W  = 2.5
BAR_GAP = 2.8
BG = (0.10, 0.10, 0.10, 0.88)


class _TimerTarget(NSObject):
    def setCallback_(self, cb):
        self._cb = cb
    def tick_(self, _timer):
        if hasattr(self, "_cb") and self._cb:
            self._cb()


class WaveformView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(WaveformView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._heights = [0.15] * N_BARS
        self._targets  = [0.15] * N_BARS
        self._phase    = 0.0
        self._mode     = "idle"
        self._volume   = 0.0
        return self

    def set_mode(self, mode):
        self._mode = mode
        if mode == "idle":
            self._targets = [0.12] * N_BARS

    def push_volume(self, rms):
        self._volume = rms

    def animate_tick(self):
        if self._mode == "recording":
            self._phase += 0.28
            vol = self._volume
            for i in range(N_BARS):
                sine = 0.5 + 0.5 * math.sin(self._phase + i * 0.8)
                base = 0.12 + 0.25 * sine
                self._targets[i] = base + vol * (0.55 * sine + 0.2)
        elif self._mode == "processing":
            self._phase += 0.10
            v = 0.18 + 0.22 * abs(math.sin(self._phase))
            self._targets = [v] * N_BARS

        for i in range(N_BARS):
            self._heights[i] += (self._targets[i] - self._heights[i]) * 0.35
        self.setNeedsDisplay_(True)

    def drawRect_(self, rect):
        NSColor.clearColor().setFill()
        NSBezierPath.fillRect_(rect)

        w = self.bounds().size.width
        h = self.bounds().size.height
        total_w = N_BARS * BAR_W + (N_BARS - 1) * BAR_GAP
        sx = (w - total_w) / 2

        NSColor.colorWithWhite_alpha_(1.0, 0.92).setFill()
        for i, ratio in enumerate(self._heights):
            bar_h = max(2.5, ratio * h * 0.88)
            x = sx + i * (BAR_W + BAR_GAP)
            y = (h - bar_h) / 2
            r = BAR_W / 2
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(x, y, BAR_W, bar_h), r, r
            ).fill()


class Overlay:
    def __init__(self):
        self._anim_timer = None
        self._refs = []
        self._waveform = None
        self._build()

    def _build(self):
        sw = NSScreen.mainScreen().frame().size.width
        x  = (sw - W) / 2

        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, Y_BASE, W, H),
            NSBorderlessWindowMask,
            NSBackingStoreBuffered,
            False,
        )
        win.setLevel_(NSFloatingWindowLevel)
        win.setOpaque_(False)
        win.setBackgroundColor_(NSColor.clearColor())
        win.setHasShadow_(True)
        win.setIgnoresMouseEvents_(True)  # 纯视觉，不抢鼠标焦点

        cv = win.contentView()
        cv.setWantsLayer_(True)
        layer = cv.layer()
        import Quartz
        bg_color = NSColor.colorWithRed_green_blue_alpha_(*BG)
        layer.setBackgroundColor_(bg_color.CGColor())
        layer.setCornerRadius_(RADIUS)
        layer.setMasksToBounds_(True)

        wv = WaveformView.alloc().initWithFrame_(NSMakeRect(0, 0, W, H))
        cv.addSubview_(wv)
        self._waveform = wv
        self._win = win

    # ── 公开接口（主线程）────────────────────────────────────────
    def show_recording(self):
        self._waveform.set_mode("recording")
        self._win.orderFrontRegardless()
        self._start_anim()

    def show_processing(self):
        self._waveform.set_mode("processing")

    def push_volume(self, rms: float):
        self._waveform.push_volume(rms)

    def hide(self):
        self._stop_anim()
        self._waveform.set_mode("idle")
        self._win.orderOut_(None)

    def _start_anim(self):
        tt = _TimerTarget.alloc().init()
        tt.setCallback_(self._waveform.animate_tick)
        self._refs.append(tt)
        self._anim_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.05, tt, objc.selector(tt.tick_, signature=b"v@:@"), None, True
        )

    def _stop_anim(self):
        if self._anim_timer:
            self._anim_timer.invalidate()
            self._anim_timer = None
