import os
import smtplib
import httpx
from email.mime.text import MIMEText


class EmailNotifier:
    def __init__(self, email_cfg):
        self.cfg = email_cfg

    def send(self, topic: str, findings_count: int, report_path: str, highlights: list[str]):
        if not self.cfg.enabled:
            return

        pwd = os.getenv(self.cfg.smtp_password_env, "")
        if not pwd:
            raise RuntimeError("SMTP password env var not set")

        subject = f"{self.cfg.subject_prefix} {topic} - {findings_count} findings"
        body = [
            f"Topic: {topic}",
            f"Findings: {findings_count}",
            f"Report: {report_path}",
            "",
            "Highlights:",
            *[f"- {h}" for h in highlights[:15]],
        ]

        msg = MIMEText("\n".join(body), "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self.cfg.from_email
        msg["To"] = ", ".join(self.cfg.to)

        with smtplib.SMTP(self.cfg.smtp_host, self.cfg.smtp_port) as server:
            server.starttls()
            server.login(self.cfg.smtp_user, pwd)
            server.sendmail(self.cfg.from_email, self.cfg.to, msg.as_string())


class TeamsNotifier:
    def __init__(self, teams_cfg):
        self.cfg = teams_cfg

    def send(self, topic: str, findings_count: int, report_path: str, highlights: list[str]):
        if not self.cfg.enabled:
            return

        webhook = os.getenv(self.cfg.webhook_url_env, "")
        if not webhook:
            raise RuntimeError("Teams webhook env var not set")

        text_lines = [
            f"**Crawler Alert**",
            f"- Topic: {topic}",
            f"- Findings: {findings_count}",
            f"- Report: `{report_path}`",
            "",
            "**Highlights**",
            *[f"- {h}" for h in highlights[:10]],
        ]

        payload = {"text": "\n".join(text_lines)}
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(webhook, json=payload)
            resp.raise_for_status()