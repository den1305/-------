"""把词典词条组装成「屏幕展示内容」与「口语朗读稿」。

屏幕展示内容按结构化字段分栏呈现；朗读稿优先使用词条自带的 narrate 字段，
若缺失则用各字段自动拼出一段连贯的话术。
"""

from __future__ import annotations


def build_view(spot: dict) -> dict:
    """生成前端展示用的结构化内容。"""
    return {
        "name": spot["name"],
        "category": spot.get("category", ""),
        "location": spot.get("location", ""),
        "tags": spot.get("tags", []),
        "intro": spot.get("intro", ""),
        "history": spot.get("history", ""),
        "highlights": spot.get("highlights", []),
        "open_info": spot.get("open_info", ""),
    }


def build_narrate(spot: dict) -> str:
    """生成用于语音合成的连贯朗读文本。"""
    if spot.get("narrate"):
        return spot["narrate"]

    parts = [spot["name"]]
    if spot.get("location"):
        parts.append(f"位于{spot['location']}")
    text = "，".join(parts) + "。"

    if spot.get("intro"):
        text += spot["intro"]
    if spot.get("history"):
        text += spot["history"]
    if spot.get("highlights"):
        text += "主要看点有" + "、".join(spot["highlights"]) + "。"
    if spot.get("open_info"):
        text += f"开放时间：{spot['open_info']}。"
    return text
