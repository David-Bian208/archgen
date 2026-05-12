from abc import ABC, abstractmethod
import os
import dashscope
from src.config import settings


class TTSProvider(ABC):
    """TTS 抽象接口 — 后期可替换为 CosyVoice"""

    @abstractmethod
    def synthesize(self, text: str, voice: str = "default", save_path: str = "audio.wav") -> str:
        """
        合成语音，返回音频文件路径
        """
        pass


class AliyunTTS(TTSProvider):
    """阿里云 TTS 实现 — 基于 DashScope sambert（HTTP API）

    已验证可用的模型：sambert-zhichu-v1, sambert-zhixiao-v1 等
    cosyvoice-v2 需账号单独激活，qwen3-tts-flash 暂不支持 SDK tts_v2
    """

    # 音色映射：友好名称 → DashScope sambert 音色
    VOICE_MAP = {
        "default": "zhichu",       # 知春（女声，默认）
        "female": "zhichu",
        "male": "zhinan",          # 知楠（男声）
        "zhichu": "zhichu",
        "zhinan": "zhinan",
        "zhixiao": "zhixiao",      # 知宵
    }

    def __init__(self):
        dashscope.api_key = settings.dashscope_api_key

    def synthesize(self, text: str, voice: str = "default", save_path: str = "data/audio.wav") -> str:
        """
        调用 DashScope sambert TTS API（HTTP 同步）
        """
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        actual_voice = self.VOICE_MAP.get(voice, "zhichu")

        from dashscope.audio.tts import SpeechSynthesizer

        result = SpeechSynthesizer.call(
            model='sambert-zhichu-v1',
            text=text,
            voice=actual_voice,
            sample_rate=16000,
            format='wav'
        )

        audio = result.get_audio_data()
        if not audio:
            raise RuntimeError(f"TTS 合成失败: {result.get_response()}")

        with open(save_path, "wb") as f:
            f.write(audio)

        return save_path
