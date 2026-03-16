import re


class ContentQualityScorer:
    def score(self, html: str, text: str, title: str, keywords: list[str]) -> int:
        score = 0

        text_len = len(text)
        if 400 <= text_len <= 4000:
            score += 30
        elif 200 <= text_len < 400 or 4000 < text_len <= 8000:
            score += 15

        if title and len(title.strip()) > 8:
            score += 20

        ratio = (len(text) / max(len(html), 1)) * 100
        if ratio > 20:
            score += 20
        elif ratio > 10:
            score += 10

        lower = text.lower()
        if keywords:
            hits = sum(1 for k in keywords if k.lower() in lower)
            if hits >= 2:
                score += 15
            elif hits == 1:
                score += 8

        # crude boilerplate penalty
        nav_tokens = ["cookie", "privacy", "terms", "subscribe", "menu"]
        penalty = sum(1 for t in nav_tokens if t in lower[:1500])
        score -= min(20, penalty * 4)

        return max(0, min(100, score))


class ConfidenceScorer:
    def score(self, keyword: str, in_title: bool, quality_score: int, keyword_weights: dict[str, float]) -> float:
        base = keyword_weights.get(keyword, 0.5)
        if keyword.startswith("regex:"):
            base += 0.1
        if in_title:
            base += 0.15
        base += (quality_score / 100.0) * 0.2
        return max(0.0, min(1.0, base))


class FalsePositiveFilter:
    def __init__(self, suppress_if_contains: list[str]):
        self.suppress = [s.lower() for s in suppress_if_contains]

    def is_suppressed(self, snippet: str) -> bool:
        s = snippet.lower()
        return any(tok in s for tok in self.suppress)