import sounddevice as sd
import numpy as np
import wave
import tempfile
import threading


class Recorder:
    def __init__(self, samplerate=16000, channels=1):
        self.samplerate = samplerate
        self.channels = channels
        self._frames = []
        self._recording = False
        self._lock = threading.Lock()
        self.on_volume = None  # callback(rms: float 0~1)

    def start(self, on_volume=None):
        self._frames = []
        self._recording = True
        self.on_volume = on_volume

        def callback(indata, frames, time, status):
            if self._recording:
                with self._lock:
                    self._frames.append(indata.copy())
                if self.on_volume:
                    rms = float(np.sqrt(np.mean(indata ** 2)))
                    self.on_volume(min(1.0, rms * 8))  # 放大到 0~1

        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="float32",
            callback=callback,
        )
        self._stream.start()

    def stop(self) -> str:
        self._recording = False
        self._stream.stop()
        self._stream.close()

        with self._lock:
            frames = list(self._frames)

        if not frames:
            return None

        audio = np.concatenate(frames, axis=0)

        # 峰值归一化：无论说话音量大小，都拉到 90% 满幅，支持低语模式
        peak = np.max(np.abs(audio))
        if peak > 0.001:  # 过滤纯静音
            audio = audio * (0.9 / peak)

        audio_int16 = (audio * 32767).astype(np.int16)

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(audio_int16.tobytes())

        return tmp.name
