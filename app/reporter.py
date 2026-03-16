from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
from slugify import slugify


class MarkdownReporter:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)

    @staticmethod
    def _next_report_path(day_dir: Path, topic_slug: str, now_utc: datetime) -> Path:
        base = day_dir / f"{topic_slug}.md"
        if not base.exists():
            return base

        run_stamp = now_utc.strftime("%H%M%S")
        candidate = day_dir / f"{topic_slug}-{run_stamp}.md"
        idx = 2
        while candidate.exists():
            candidate = day_dir / f"{topic_slug}-{run_stamp}-{idx}.md"
            idx += 1

        return candidate

    @staticmethod
    def _group_findings_by_url(findings):
        grouped = {}
        keyword_url_counts = Counter()

        for finding in findings:
            canonical = (getattr(finding, "canonical_url", "") or "").strip()
            report_key = canonical or finding.url

            if report_key not in grouped:
                grouped[report_key] = {
                    "finding": finding,
                    "keywords": [],
                    "keyword_set": set(),
                }

            bucket = grouped[report_key]
            if finding.keyword not in bucket["keyword_set"]:
                bucket["keyword_set"].add(finding.keyword)
                bucket["keywords"].append(finding.keyword)
                keyword_url_counts[finding.keyword] += 1

        return grouped, keyword_url_counts

    def write_daily_topic_report(self, result):
        now_utc = datetime.now(timezone.utc)
        day = now_utc.strftime("%Y-%m-%d")
        day_dir = self.output_dir / day
        day_dir.mkdir(parents=True, exist_ok=True)

        topic_slug = slugify(result.topic)
        fp = self._next_report_path(day_dir, topic_slug, now_utc)

        grouped_findings, counts = self._group_findings_by_url(result.findings)
        unique_findings = list(grouped_findings.values())
        raw_matches = len(result.findings)

        lines = []
        lines.append(f"# Crawl Report - {result.topic}")
        lines.append(f"**Date:** {day}  ")
        lines.append(f"**Pages Scanned:** {result.pages_scanned}  ")
        lines.append(f"**Findings:** {len(unique_findings)}  ")
        lines.append(f"**Raw Matches:** {raw_matches}\n")

        lines.append("## Summary")
        if counts:
            for k, v in counts.items():
                lines.append(f"- `{k}`: {v} matches")
        else:
            lines.append("- No findings")

        lines.append("\n## Findings")
        if unique_findings:
            for idx, entry in enumerate(unique_findings, start=1):
                f = entry["finding"]
                keywords = ", ".join(entry["keywords"])
                lines.append(f"### {idx}) {keywords}")
                lines.append(f"- **URL:** {f.url}")
                lines.append(f"- **Title:** {f.title or '(no title)'}")
                lines.append(f"- **Keywords:** {keywords}")
                lines.append(f"- **Snippet:** {f.snippet}")
                lines.append(f"- **Timestamp (UTC):** {f.timestamp}\n")
        else:
            lines.append("- No findings\n")

        lines.append("## Errors")
        if result.errors:
            for err in result.errors:
                lines.append(f"- {err['url']} -> {err['error']}")
        else:
            lines.append("- No errors")

        fp.write_text("\n".join(lines), encoding="utf-8")
        return str(fp)