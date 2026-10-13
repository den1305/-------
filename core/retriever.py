"""本地词典检索。

检索优先级：精确名称/别名 → 拼音完全匹配 → 模糊匹配 → 未收录（并给出相近建议）。
全程不联网，仅依赖标准库；若安装了 pypinyin 则额外启用拼音匹配。
"""

from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher

try:  # pypinyin 为可选依赖，缺失时自动降级
    from pypinyin import lazy_pinyin
except ImportError:  # pragma: no cover
    lazy_pinyin = None

# 需要忽略的空白与常见中英文标点
_PUNCT = re.compile(r"[\s,，.。、!！?？:：;；\-—_'\"“”‘’()（）《》【】\[\]·]+")

# 模糊匹配的相似度阈值
FUZZY_THRESHOLD = 0.5


def normalize(text: str) -> str:
    """归一化：全角转半角、转小写、去除空白与标点。"""
    text = unicodedata.normalize("NFKC", text or "").strip().lower()
    return _PUNCT.sub("", text)


def to_pinyin(text: str) -> str:
    """转为无声调拼音串（如“故宫”→ gugong）；未安装 pypinyin 时返回空串。"""
    if lazy_pinyin is None:
        return ""
    return "".join(lazy_pinyin(text))


class SpotRetriever:
    """基于本地 JSON 词典的景点检索器。"""

    def __init__(self, data_path: str):
        with open(data_path, encoding="utf-8") as f:
            payload = json.load(f)
        self.spots = payload["spots"]

        # 归一化后的 名称/别名 -> 词条
        self._index: dict[str, dict] = {}
        # 用于模糊与拼音匹配的候选：(归一化串, 拼音串, 词条)
        self._candidates: list[tuple[str, str, dict]] = []

        for spot in self.spots:
            keys = [spot["name"], *spot.get("aliases", [])]
            for key in keys:
                norm = normalize(key)
                if not norm:
                    continue
                self._index.setdefault(norm, spot)
                self._candidates.append((norm, to_pinyin(key), spot))

    def names(self) -> list[str]:
        """返回全部景点名称，供前端提示使用。"""
        return [s["name"] for s in self.spots]

    def search(self, query: str) -> tuple[dict | None, str, list[str]]:
        """检索景点。

        返回 (命中的词条或 None, 匹配方式, 相近建议列表)。
        匹配方式取值：exact / pinyin / fuzzy / not_found / empty。
        """
        q = normalize(query)
        if not q:
            return None, "empty", []

        # 1) 精确匹配名称或别名
        if q in self._index:
            return self._index[q], "exact", []

        # 2) 拼音完全匹配
        q_pinyin = to_pinyin(q)
        if q_pinyin:
            for _, py, spot in self._candidates:
                if py and py == q_pinyin:
                    return spot, "pinyin", []

        # 3) 模糊匹配（中文字符串或拼音串相似度取较大者）
        best_spot: dict | None = None
        best_score = 0.0
        for norm, py, spot in self._candidates:
            score = SequenceMatcher(None, q, norm).ratio()
            if q_pinyin and py:
                score = max(score, SequenceMatcher(None, q_pinyin, py).ratio() * 0.95)
            if score > best_score:
                best_score = score
                best_spot = spot

        if best_spot is not None and best_score >= FUZZY_THRESHOLD:
            return best_spot, "fuzzy", []

        # 4) 未收录：给出最相近的几个名称作为建议
        ranked = sorted(
            self._candidates,
            key=lambda c: -SequenceMatcher(None, q, c[0]).ratio(),
        )
        suggestions: list[str] = []
        for _, _, spot in ranked:
            if spot["name"] not in suggestions:
                suggestions.append(spot["name"])
            if len(suggestions) >= 3:
                break
        return None, "not_found", suggestions
