import re
from app.models import KeywordConfig


class KeywordAnalyzer:
    @staticmethod
    def _mk_snippet(text: str, idx: int, length: int = 180) -> str:
        start = max(0, idx - 80)
        end = min(len(text), idx + length)
        return text[start:end].replace("\n", " ").strip()

    def find_matches(self, text: str, keywords_cfg: KeywordConfig):
        results = []
        lower = text.lower()

        for kw in keywords_cfg.include:
            idx = lower.find(kw.lower())
            if idx >= 0:
                results.append({"keyword": kw, "snippet": self._mk_snippet(text, idx)})

        for rx in keywords_cfg.regex:
            m = re.search(rx, text)
            if m:
                results.append(
                    {"keyword": f"regex:{rx}", "snippet": self._mk_snippet(text, m.start())}
                )

        excludes = [e.lower() for e in keywords_cfg.exclude]
        if excludes:
            results = [
                r for r in results
                if not any(ex in r["snippet"].lower() for ex in excludes)
            ]

        return results