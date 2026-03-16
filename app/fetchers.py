import os
import httpx
from playwright.async_api import async_playwright


class StaticFetcher:
    def __init__(self, user_agent: str, timeout_sec: int):
        self.user_agent = user_agent
        self.timeout_sec = timeout_sec

    async def fetch(self, url: str):
        async with httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout_sec,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text, str(resp.url)


class BrowserFetcher:
    def __init__(self, state_dir: str, user_agent: str, timeout_sec: int):
        self.state_dir = state_dir
        self.user_agent = user_agent
        self.timeout_ms = timeout_sec * 1000

    def _state_file(self, topic_slug: str) -> str:
        return os.path.join(self.state_dir, f"{topic_slug}_storage_state.json")

    async def login_if_needed(self, topic_cfg, topic_slug: str):
        auth = topic_cfg.crawl.auth
        if not auth or auth.mode != "playwright_form":
            return

        username = os.getenv(auth.username_env or "", "")
        password = os.getenv(auth.password_env or "", "")
        if not username or not password:
            raise RuntimeError(f"Missing credentials in env for topic '{topic_cfg.name}'")

        state_file = self._state_file(topic_slug)
        if topic_cfg.crawl.session_persist and os.path.exists(state_file):
            return

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=self.user_agent)
            page = await context.new_page()
            await page.goto(auth.login_url, timeout=self.timeout_ms)
            await page.fill(auth.selectors.username, username)
            await page.fill(auth.selectors.password, password)
            await page.click(auth.selectors.submit)
            await page.wait_for_selector(auth.selectors.success_indicator, timeout=self.timeout_ms)

            if topic_cfg.crawl.session_persist:
                await context.storage_state(path=state_file)

            await context.close()
            await browser.close()

    async def fetch(self, url: str, topic_slug: str):
        state_file = self._state_file(topic_slug)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context_kwargs = {"user_agent": self.user_agent}
            if os.path.exists(state_file):
                context_kwargs["storage_state"] = state_file

            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()
            await page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
            html = await page.content()
            final_url = page.url
            await context.close()
            await browser.close()
            return html, final_url