import re
import hashlib
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from simhash import Simhash


class Deduplicator:
    def __init__(self, near_dup_threshold: int = 3):
        self.near_dup_threshold = near_dup_threshold

    def canonicalize_url(self, url: str) -> str:
        p = urlparse(url)
        q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.startswith("utm_")]
        q.sort(key=lambda x: x[0])
        path = re.sub(r"/+", "/", p.path or "/")
        return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", urlencode(q), ""))

    def normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower()

    def content_hash(self, text: str) -> str:
        n = self.normalize_text(text)
        return hashlib.sha256(n.encode("utf-8")).hexdigest()

    def simhash(self, text: str) -> int:
        tokens = self.normalize_text(text).split(" ")
        return Simhash(tokens).value

    def is_near_duplicate(self, simhash_value: int, prior_values: list[int]) -> bool:
        for v in prior_values:
            # Hamming distance on 64-bit
            dist = (simhash_value ^ v).bit_count()
            if dist <= self.near_dup_threshold:
                return True
        return False