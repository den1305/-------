"""本地网页服务：景点介绍 + 离线语音合成 + 离线语音识别。

接口：
    GET  /             首页
    GET  /api/spots    词典中的全部景点名称
    POST /api/intro    入参 {"name": "故宫"}，返回介绍内容与朗读稿
    POST /api/tts      入参 {"text": ..., "speed": ..., "sid": ...}，返回 WAV 音频
    POST /api/asr      请求体为 WAV 字节，返回识别文本
    GET  /api/health   模型与词典状态

全程不访问任何网络或外部模型接口。
"""

from __future__ import annotations

import os
import threading

from flask import Flask, Response, jsonify, render_template, request

from core.content import build_narrate, build_view
from core.retriever import SpotRetriever

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.environ.get("SCENIC_MODELS_DIR") or os.path.join(BASE_DIR, "models")
SPOTS_PATH = os.environ.get("SCENIC_SPOTS_PATH") or os.path.join(BASE_DIR, "data", "spots.json")

TTS_MODEL_DIR = os.path.join(MODELS_DIR, "sherpa-onnx-vits-zh-ll")
ASR_MODEL_DIR = os.path.join(MODELS_DIR, "sherpa-onnx-paraformer-zh-small-2024-03-09")

app = Flask(__name__)
retriever = SpotRetriever(SPOTS_PATH)

# 引擎体积较大，按需懒加载（首次调用时初始化），并加锁避免重复初始化
_tts_engine = None
_tts_lock = threading.Lock()
_asr_engine = None
_asr_lock = threading.Lock()


def get_tts():
    global _tts_engine
    if _tts_engine is None:
        with _tts_lock:
            if _tts_engine is None:
                from core.tts import TtsEngine

                _tts_engine = TtsEngine(TTS_MODEL_DIR)
    return _tts_engine


def get_asr():
    global _asr_engine
    if _asr_engine is None:
        with _asr_lock:
            if _asr_engine is None:
                from core.asr import AsrEngine

                _asr_engine = AsrEngine(ASR_MODEL_DIR)
    return _asr_engine


@app.get("/")
def index():
    return render_template("index.html", spots=retriever.names())


@app.get("/api/spots")
def api_spots():
    return jsonify({"spots": retriever.names()})


@app.post("/api/intro")
def api_intro():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    if not name:
        return jsonify({"found": False, "error": "请输入景点名称"}), 400

    spot, match, suggestions = retriever.search(name)
    if spot is None:
        return jsonify({"found": False, "match": match, "suggestions": suggestions})

    return jsonify(
        {
            "found": True,
            "match": match,
            "view": build_view(spot),
            "narrate": build_narrate(spot),
        }
    )


@app.post("/api/tts")
def api_tts():
    # 用 POST + JSON 传文本，避免中文/long 文本放进 URL 导致的编码问题
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", "")).strip()
    if not text:
        return jsonify({"error": "缺少 text 参数"}), 400

    try:
        speed = float(payload.get("speed", 1.0))
    except (TypeError, ValueError):
        speed = 1.0
    try:
        sid = int(payload.get("sid", 0))
    except (TypeError, ValueError):
        sid = 0

    try:
        wav = get_tts().synthesize_wav_bytes(text, sid=sid, speed=speed)
    except Exception as exc:  # 模型缺失或合成异常时给出可读提示
        return jsonify({"error": f"语音合成失败：{exc}"}), 500

    return Response(
        wav,
        mimetype="audio/wav",
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/asr")
def api_asr():
    data = request.get_data()
    if not data:
        return jsonify({"error": "缺少音频数据"}), 400

    try:
        text = get_asr().transcribe_wav_bytes(data)
    except Exception as exc:
        return jsonify({"error": f"语音识别失败：{exc}"}), 500

    return jsonify({"text": text})


@app.get("/api/health")
def api_health():
    return jsonify(
        {
            "spots": len(retriever.spots),
            "tts_model": os.path.isdir(TTS_MODEL_DIR),
            "asr_model": os.path.isdir(ASR_MODEL_DIR),
        }
    )


if __name__ == "__main__":
    host = os.environ.get("SCENIC_HOST", "127.0.0.1")
    port = int(os.environ.get("SCENIC_PORT", "5000"))
    print(f"服务已启动：http://{host}:{port}  （按 Ctrl+C 停止）")
    app.run(host=host, port=port, debug=False)
