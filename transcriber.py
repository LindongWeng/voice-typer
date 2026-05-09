import os


class Transcriber:
    def __init__(self, engine="sensevoice", model_size="base", language=None):
        self.engine = engine
        self.language = language

        if engine == "sensevoice":
            self._load_sensevoice()
        else:
            self._load_whisper(model_size)

    def _load_sensevoice(self):
        from funasr import AutoModel
        print("[Transcriber] 加载 SenseVoice 模型（首次需下载约 300MB）...")
        self.model = AutoModel(
            model="iic/SenseVoiceSmall",
            trust_remote_code=True,
            disable_update=True,
        )
        print("[Transcriber] SenseVoice 加载完成")

    def _load_whisper(self, model_size):
        from faster_whisper import WhisperModel
        print(f"[Transcriber] 加载 Whisper 模型: {model_size}")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        print("[Transcriber] Whisper 加载完成")

    def transcribe(self, wav_path: str) -> str:
        if self.engine == "sensevoice":
            return self._transcribe_sensevoice(wav_path)
        else:
            return self._transcribe_whisper(wav_path)

    def _transcribe_sensevoice(self, wav_path: str) -> str:
        res = self.model.generate(
            input=wav_path,
            cache={},
            language="auto",
            use_itn=True,
            batch_size_s=60,
        )
        if not res:
            return ""
        text = res[0]["text"]
        # 去掉 SenseVoice 输出的情感标签，如 <|NEUTRAL|><|Speech|><|woitn|>
        import re
        text = re.sub(r"<\|[^|]+\|>", "", text).strip()
        return text

    def _transcribe_whisper(self, wav_path: str) -> str:
        segments, _ = self.model.transcribe(
            wav_path,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            initial_prompt="以下是中英文混合的语音转文字内容：",
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
