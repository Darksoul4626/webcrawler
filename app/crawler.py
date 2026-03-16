import asyncio
from datetime import datetime, timezone
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from slugify import slugify

from app.models import Finding


class CrawlEngine:
    def __init__(
        self,
        static_fetcher,
        browser_fetcher,
        analyzer,
        state_store,
        archiver,
        discovery,
        policy_engine,
        quality_scorer,
        confidence_scorer,
        fp_filter,
        deduplicator,
        max_concurrency: int = 8,
        user_agent: str = "ResearchCrawler/2.0",
    ):
        self.static_fetcher = static_fetcher
        self.browser_fetcher = browser_fetcher
        self.analyzer = analyzer
        self.state_store = state_store
        self.archiver = archiver
        self.discovery = discovery
        self.policy_engine = policy_engine
        self.quality_scorer = quality_scorer
        self.confidence_scorer = confidence_scorer
        self.fp_filter = fp_filter
        self.deduplicator = deduplicator
        self.max_concurrency = max(1, max_concurrency)
        self.user_agent = user_agent

    def _topic_slug(self, topic_name: str) -> str:
        return slugify(topic_name)

    def _extract(self, html: str, base_url: str):
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        title = soup.title.text.strip() if soup.title else ""
        text = soup.get_text(" ", strip=True)
        links = [urljoin(base_url, a["href"]) for a in soup.select("a[href]")]
        return title, text, links

    def _allowed(self, url: str, topic_cfg) -> bool:
        u = url.lower()
        if topic_cfg.crawl.allowed_domains:
            if not any(d.lower() in u for d in topic_cfg.crawl.allowed_domains):
                return False
        inc = topic_cfg.crawl.include_url_patterns or []
        exc = topic_cfg.crawl.exclude_url_patterns or []
        if inc and not any(p.lower() in u for p in inc):
            return False
        if any(p.lower() in u for p in exc):
            return False
        return True

    @staticmethod
    def _deduplicate_findings_by_url(findings):
        unique = {}

        for finding in findings:
            canonical = (finding.canonical_url or "").strip()
            key = canonical or finding.url
            existing = unique.get(key)

            if existing is None:
                unique[key] = finding
                continue

            current_score = (finding.confidence, finding.quality_score, len(finding.snippet or ""))
            existing_score = (existing.confidence, existing.quality_score, len(existing.snippet or ""))
            if current_score > existing_score:
                unique[key] = finding

        return list(unique.values())

    async def crawl_topic(self, topic_cfg):
        topic_slug = self._topic_slug(topic_cfg.name)
        state = self.state_store.load_topic_state(topic_slug)

        seen_fingerprints = set(state.get("seen_fingerprints", []))
        canonical_url_hash = dict(state.get("canonical_url_hash", {}))
        simhash_values = list(state.get("simhash_values", []))

        if topic_cfg.crawl.render_js:
            await self.browser_fetcher.login_if_needed(topic_cfg, topic_slug)

        seeds = await self.discovery.discover(topic_cfg)
        frontier = {(u, 0) for u in seeds}
        visited = set()
        findings = []
        errors = []
        pages_scanned = 0

        sem = asyncio.Semaphore(self.max_concurrency)

        async def process(url: str, depth: int):
            nonlocal pages_scanned
            async with sem:
                if not self._allowed(url, topic_cfg):
                    return [], [], None
                can = await self.policy_engine.can_fetch(url, self.user_agent)
                if not can:
                    return [], [], None

                await self.policy_engine.apply_delay(url)

                if topic_cfg.crawl.render_js:
                    html, final_url = await self.browser_fetcher.fetch(url, topic_slug)
                else:
                    html, final_url = await self.static_fetcher.fetch(url)

                pages_scanned += 1
                snap = None
                if self.archiver is not None:
                    snap = self.archiver.save(topic_cfg.name, final_url, html)

                title, text, links = self._extract(html, final_url)
                quality = self.quality_scorer.score(
                    html=html,
                    text=text,
                    title=title,
                    keywords=topic_cfg.keywords.include,
                )

                canon = self.deduplicator.canonicalize_url(final_url)
                chash = self.deduplicator.content_hash(text)
                simv = self.deduplicator.simhash(text)

                if canonical_url_hash.get(canon) == chash:
                    return [], [], None
                if self.deduplicator.is_near_duplicate(simv, simhash_values):
                    return [], [], None

                canonical_url_hash[canon] = chash
                simhash_values.append(simv)

                local_findings = []
                matches = self.analyzer.find_matches(text, topic_cfg.keywords)

                for m in matches:
                    if self.fp_filter.is_suppressed(m["snippet"]):
                        continue

                    in_title = m["keyword"].replace("regex:", "").lower() in (title or "").lower()
                    conf = self.confidence_scorer.score(
                        keyword=m["keyword"],
                        in_title=in_title,
                        quality_score=quality,
                        keyword_weights=topic_cfg.alerting.keyword_weights,
                    )

                    if quality < topic_cfg.alerting.min_quality_score:
                        continue
                    if conf < topic_cfg.alerting.min_confidence:
                        continue

                    fkey = self.state_store.finding_key(canon, m["keyword"], m["snippet"])
                    if fkey in seen_fingerprints:
                        continue

                    seen_fingerprints.add(fkey)
                    snippet = m["snippet"]
                    if snap:
                        snippet = f"{snippet} [snapshot: {snap}]"
                    local_findings.append(
                        Finding(
                            topic=topic_cfg.name,
                            url=final_url,
                            title=title,
                            keyword=m["keyword"],
                            snippet=snippet,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            quality_score=quality,
                            confidence=conf,
                            canonical_url=canon,
                            content_hash=chash,
                        )
                    )

                nxt = []
                if depth < topic_cfg.crawl.max_depth:
                    for l in links:
                        if self._allowed(l, topic_cfg):
                            nxt.append((l, depth + 1))

                return local_findings, nxt, None

        while frontier and pages_scanned < topic_cfg.crawl.max_pages:
            batch = []
            next_frontier = set()

            while frontier and len(batch) < self.max_concurrency and (pages_scanned + len(batch)) < topic_cfg.crawl.max_pages:
                url, depth = frontier.pop()
                if url in visited:
                    continue
                visited.add(url)
                batch.append((url, depth))

            if not batch:
                break

            results = await asyncio.gather(
                *(process(url, depth) for url, depth in batch),
                return_exceptions=True,
            )

            for i, res in enumerate(results):
                src = batch[i][0]
                if isinstance(res, Exception):
                    errors.append({"url": src, "error": str(res)})
                    continue

                local_findings, nxt, _ = res
                findings.extend(local_findings)
                for n in nxt:
                    if n[0] not in visited:
                        next_frontier.add(n)

            frontier |= next_frontier

        state["seen_fingerprints"] = list(seen_fingerprints)[-200000:]
        state["canonical_url_hash"] = canonical_url_hash
        state["simhash_values"] = simhash_values[-200000:]
        self.state_store.save_topic_state(topic_slug, state)

        unique_findings = self._deduplicate_findings_by_url(findings)

        return {
            "topic": topic_cfg.name,
            "pages_scanned": pages_scanned,
            "findings": findings,
            "unique_findings": unique_findings,
            "errors": errors,
        }