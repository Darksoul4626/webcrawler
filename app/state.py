import json
from pathlib import Path
from typing import Set, Dict, Any


class StateStore:
    def __init__(self, state_dir: str):
        self.base = Path(state_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        return self.base / name

    def load_json(self, name: str, default):
        fp = self._path(name)
        if not fp.exists():
            return default
        return json.loads(fp.read_text(encoding="utf-8"))

    def save_json(self, name: str, data):
        self._path(name).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_topic_state(self, topic_slug: str) -> Dict[str, Any]:
        return self.load_json(
            f"{topic_slug}_state.json",
            {
                "seen_fingerprints": [],
                "canonical_url_hash": {},
                "simhash_values": [],
                "feedback": {}  # finding_key -> true_positive|false_positive
            },
        )

    def save_topic_state(self, topic_slug: str, data: Dict[str, Any]):
        self.save_json(f"{topic_slug}_state.json", data)

    @staticmethod
    def finding_key(url: str, keyword: str, snippet: str) -> str:
        return f"{url}|{keyword}|{snippet}"[:1000]