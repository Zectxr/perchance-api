from __future__ import annotations

from typing import Self

from playwright.async_api import Browser, BrowserContext, async_playwright, Playwright

from .utils import generate_user_agent


class Generator:
    def __init__(self) -> None:
        super().__init__()

        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.close()

    async def _start(self) -> None:
        if not self._pw:
            self._pw = await async_playwright().start()
        if not self._browser:
            self._browser = await self._pw.chromium.launch(headless=True)
        if not self._context:
            self._context = await self._browser.new_context(
                user_agent=generate_user_agent()
            )

    async def close(self) -> None:
        """Close the generator and release resources."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()