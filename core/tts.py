"""离线语音合成（TTS）封装，基于 sherpa-onnx 的 VITS 模型。

同一套逻辑支持两类模型目录，按目录内容自动识别：
  - 中文 VITS（sherpa-onnx-vits-zh-ll）：model.onnx + lexicon.txt + tokens.txt + dict/
  - 英文 Piper（vits-piper-en_US-*）：<voice>.onnx + tokens.txt + espeak-ng-data/
"""

from __future__ import annotations

import glob
import io
import os
import wave

import numpy as np
import sherpa_onnx

# 文本正则化所需的规则 fst（缺失的自动跳过）
_RULE_FSTS = ("phone.fst", "date.fst", "number.fst", "new_heteronym.fst")


def samples_to_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    """把 [-1, 1] 的浮点采样写成 16bit 单声道 WAV 字节。"""
    pcm = np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(sample_rate))
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def _find_model_file(model_dir: str) -> str:
    """定位 VITS 主模型：优先 model.onnx，否则取目录下第一个 *.onnx。"""
    preferred = os.path.join(model_dir, "model.onnx")
    if os.path.exists(preferred):
        return preferred
    candidates = sorted(glob.glob(os.path.join(model_dir, "*.onnx")))
    if not candidates:
        raise FileNotFoundError(f"未在 {model_dir} 找到 .onnx 模型文件")
    return candidates[0]


def _optional(model_dir: str, name: str) -> str:
    """目录下存在该文件/文件夹则返回其路径，否则返回空串（sherpa-onnx 视空串为未提供）。"""
    path = os.path.join(model_dir, name)
    return path if os.path.exists(path) else ""


class TtsEngine:
    """封装 OfflineTts 的懒加载引擎（进程内单例由调用方保证）。"""

    def __init__(self, model_dir: str, provider: str = "cpu", num_threads: int = 2,
                 default_sid: int = 0, default_speed: float = 1.0):
        self.model_dir = model_dir
        self.default_sid = default_sid
        self.default_speed = default_speed

        vits = sherpa_onnx.OfflineTtsVitsModelConfig(
            model=_find_model_file(model_dir),
            lexicon=_optional(model_dir, "lexicon.txt"),
            tokens=os.path.join(model_dir, "tokens.txt"),
            data_dir=_optional(model_dir, "espeak-ng-data"),
            dict_dir=_optional(model_dir, "dict"),
        )
        model_config = sherpa_onnx.OfflineTtsModelConfig(
            vits=vits,
            num_threads=num_threads,
            debug=False,
            provider=provider,
        )
        rule_fsts = ",".join(
            os.path.join(model_dir, name)
            for name in _RULE_FSTS
            if os.path.exists(os.path.join(model_dir, name))
        )
        config = sherpa_onnx.OfflineTtsConfig(
            model=model_config,
            rule_fsts=rule_fsts,
            max_num_sentences=1,
        )
        self._tts = sherpa_onnx.OfflineTts(config)
        self.sample_rate = self._tts.sample_rate

    @property
    def num_speakers(self) -> int:
        return getattr(self._tts, "num_speakers", 1)

    def synthesize(self, text: str, sid: int | None = None, speed: float | None = None):
        """合成语音，返回 (采样数组, 采样率)。"""
        audio = self._tts.generate(
            text,
            sid=self.default_sid if sid is None else sid,
            speed=self.default_speed if speed is None else speed,
        )
        return np.asarray(audio.samples, dtype=np.float32), int(audio.sample_rate)

    def synthesize_wav_bytes(self, text: str, sid: int | None = None,
                             speed: float | None = None) -> bytes:
        """合成并直接返回 WAV 字节，便于 HTTP 流式返回。"""
        samples, sample_rate = self.synthesize(text, sid=sid, speed=speed)
        return samples_to_wav_bytes(samples, sample_rate)
