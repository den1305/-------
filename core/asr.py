"""离线语音识别（ASR）封装，基于 sherpa-onnx 的 Paraformer 中文模型。

前端会上传 16kHz 单声道 WAV，这里解析后送入识别器，返回文本。
"""

from __future__ import annotations

import io
import os
import wave

import numpy as np
import sherpa_onnx

TARGET_SAMPLE_RATE = 16000


def read_wav_bytes(data: bytes) -> tuple[np.ndarray, int]:
    """解析 WAV 字节，返回 ([-1,1] 浮点采样, 采样率)。"""
    with wave.open(io.BytesIO(data), "rb") as w:
        channels = w.getnchannels()
        sample_width = w.getsampwidth()
        sample_rate = w.getframerate()
        frames = w.readframes(w.getnframes())

    if sample_width == 2:
        arr = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    elif sample_width == 1:  # 8bit 无符号
        arr = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sample_width == 4:
        arr = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"不支持的位深：{sample_width * 8}bit")

    if channels > 1:
        arr = arr.reshape(-1, channels).mean(axis=1)
    return arr, sample_rate


def resample(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """线性插值重采样（够用且无需额外依赖）。"""
    if src_rate == dst_rate or samples.size == 0:
        return samples
    n_dst = int(round(samples.size * dst_rate / src_rate))
    idx = np.linspace(0, samples.size - 1, n_dst)
    return np.interp(idx, np.arange(samples.size), samples).astype(np.float32)


class AsrEngine:
    """封装 OfflineRecognizer 的懒加载引擎。"""

    def __init__(self, model_dir: str, provider: str = "cpu", num_threads: int = 2):
        self.model_dir = model_dir
        self._recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
            paraformer=os.path.join(model_dir, "model.int8.onnx"),
            tokens=os.path.join(model_dir, "tokens.txt"),
            num_threads=num_threads,
            sample_rate=TARGET_SAMPLE_RATE,
            feature_dim=80,
            decoding_method="greedy_search",
            debug=False,
            provider=provider,
        )

    def transcribe_wav_bytes(self, data: bytes) -> str:
        """识别 WAV 字节并返回文本。"""
        samples, sample_rate = read_wav_bytes(data)
        samples = resample(samples, sample_rate, TARGET_SAMPLE_RATE)
        stream = self._recognizer.create_stream()
        stream.accept_waveform(TARGET_SAMPLE_RATE, samples)
        self._recognizer.decode_stream(stream)
        return stream.result.text.strip()
