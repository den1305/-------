"""把词典词条组装成「屏幕展示内容」与「口语朗读稿」，支持中英文。

每条例目顶层字段承载中文内容，另可提供 "en" 子对象承载英文内容。
"""

from __future__ import annotations


def build_view(spot: dict, lang: str = "zh") -> dict:
    """生成前端展示用的结构化内容（lang: zh / en）。"""
    if lang == "en":
        en = spot.get("en") or {}
        return {
            "name": en.get("name") or spot["name"],
            "category": en.get("category", ""),
            "location": en.get("location", ""),
            "tags": en.get("tags", spot.get("tags", [])),
            "intro": en.get("intro", ""),
            "history": en.get("history", ""),
            "highlights": en.get("highlights", []),
            "open_info": en.get("open_info", ""),
        }

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


def build_narrate(spot: dict, lang: str = "zh") -> str:
    """生成用于语音合成的连贯朗读文本（lang: zh / en）。"""
    view = build_view(spot, lang)

    if lang == "en":
        if (spot.get("en") or {}).get("narrate"):
            return spot["en"]["narrate"]
        parts = [view["name"]]
        if view["location"]:
            parts.append("located in " + view["location"])
        text = ", ".join(parts) + ". "
        if view["intro"]:
            text += view["intro"] + " "
        if view["history"]:
            text += view["history"] + " "
        if view["highlights"]:
            text += "Main highlights include " + ", ".join(view["highlights"]) + ". "
        if view["open_info"]:
            text += "Opening hours: " + view["open_info"] + ". "
        return text.strip()

    if spot.get("narrate"):
        return spot["narrate"]
    parts = [view["name"]]
    if view["location"]:
        parts.append(f"位于{view['location']}")
    text = "，".join(parts) + "。"
    if view["intro"]:
        text += view["intro"]
    if view["history"]:
        text += view["history"]
    if view["highlights"]:
        text += "主要看点有" + "、".join(view["highlights"]) + "。"
    if view["open_info"]:
        text += f"开放时间：{view['open_info']}。"
    return text
