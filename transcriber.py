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
        print("[Transcriber] 加载 SenseVoice 模型...")
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
        text = res[0].get("text", "")
        # 去掉 SenseVoice 输出的情绪/事件标签，如 <|zh|><|NEUTRAL|><|Speech|><|woitn|>
        import re
        text = re.sub(r"<\|[^|]*\|>", "", text).strip()
        return text

    def _transcribe_whisper(self, wav_path: str) -> str:
        segments, _ = self.model.transcribe(
            wav_path,
            language=self.language,
            beam_size=7,
            vad_filter=True,
            initial_prompt="以下是普通话与英文混合的对话，请用汉字转写中文部分：",
        )
        return "".join(seg.text for seg in segments).strip()
