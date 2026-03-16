import hashlib
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from slugify import slugify


class SnapshotArchiver:
    def __init__(self, snapshot_dir: str):
        self.base = Path(snapshot_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def _safe_name(self, url: str) -> str:
        parsed = urlparse(url)
        seed = f"{parsed.netloc}{parsed.path}".strip("/") or "root"
        seed = slugify(seed)[:120]
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
        return f"{seed}-{digest}.html"

    def save(self, topic: str, url: str, html: str) -> str:
        day = datetime.utcnow().strftime("%Y-%m-%d")
        topic_slug = slugify(topic)
        target_dir = self.base / day / topic_slug
        target_dir.mkdir(parents=True, exist_ok=True)

        fname = self._safe_name(url)
        fp = target_dir / fname
        fp.write_text(html, encoding="utf-8", errors="ignore")
        return str(fp)