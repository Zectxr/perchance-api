from __future__ import annotations

import asyncio
import uuid
from typing import AsyncGenerator

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from . import errors

EMBED_URL = "https://text-generation.perchance.org/embed"

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


class TextGenerator:
    """AI text generator.

    Drives the official Perchance embed in a browser so its built-in
    Cloudflare verification is handled automatically.
    """

    def __init__(self, *, headless: bool = False) -> None:
        self._headless = headless
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

        self._lock: asyncio.Lock = asyncio.Lock()

    def is_running(self) -> bool:
        return self._lock.locked()

    async def __aenter__(self) -> TextGenerator:
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the generator and release resources."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        self._pw = self._browser = self._context = None

    async def _start(self) -> None:
        if not self._pw:
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(headless=self._headless)
            self._context = await self._browser.new_context(user_agent=_USER_AGENT)

    async def stream(
        self,
        prompt: str,
        *,
        start_with: str | None = None,
        stop_sequences: list[str] | None = None,
        timeout: float = 60.0,
    ) -> AsyncGenerator[str, None]:
        """Stream generated text.

        Parameters
        ----------
        prompt: str
            The prompt to generate text from.
        start_with: str | None
            Text to start the generation with.
        stop_sequences: list[str] | None
            List of sequences to stop the generation at.
        timeout: float | None
            Maximum time to wait for the next chunk in seconds.
        """
        async with self._lock:
            await self._start()

            request_id = uuid.uuid4().hex
            messages: asyncio.Queue = asyncio.Queue()

            async with await self._context.new_page() as page:
                await page.expose_function(
                    "_pc_on_message", lambda msg: messages.put_nowait(msg)
                )
                await page.add_init_script("""
                    window.addEventListener("message", (event) => {
                        window._pc_on_message({
                            type: event.data.type,
                            value: event.data.value,
                            requestId: event.data.requestId,
                            status: event.data.status,
                        });
                    });
                """)
                await page.goto(EMBED_URL, wait_until="domcontentloaded")

                async def send(data: dict) -> None:
                    await page.evaluate(
                        "data => window.postMessage(data, '*')", data
                    )

                await _wait_for(messages, "embedIsReady", timeout)
                await send({"type": "verifyUser"})
                try:
                    await _wait_for(messages, "verified", timeout)
                except asyncio.TimeoutError as error:
                    raise errors.AuthenticationError(
                        "Anti-bot verification did not complete in time."
                    ) from error
                await send({
                    "type": "startStream",
                    "requestId": request_id,
                    "postData": {
                        "instruction": prompt,
                        "startWith": start_with or "",
                        "stopSequences": stop_sequences or [],
                    },
                })

                keepalive = asyncio.create_task(_keepalive(page, request_id))
                try:
                    while True:
                        message = await _wait_for_chunk(messages, timeout)
                        kind = message["type"]

                        if kind == "streamError":
                            raise errors.ConnectionError(
                                f"Failed to generate text: {message.get('status')}"
                            )
                        if kind == "streamEnd":
                            return
                        if kind == "streamData":
                            value = message.get("value") or {}
                            if value.get("text"):
                                yield value["text"]
                finally:
                    keepalive.cancel()
                    await send({"type": "stopStream", "requestId": request_id})

    async def text(
        self,
        prompt: str,
        *,
        start_with: str | None = None,
        stop_sequences: list[str] | None = None,
        timeout: float = 60.0,
    ) -> str:
        """Generate text.

        Parameters
        ----------
        prompt: str
            The prompt to generate text from.
        start_with: str | None
            Text to start the generation with.
        stop_sequences: list[str] | None
            List of sequences to stop the generation at.
        timeout: float | None
            Maximum time to wait for the next chunk in seconds.
        """
        result = []
        async for chunk in self.stream(
            prompt,
            start_with=start_with,
            stop_sequences=stop_sequences,
            timeout=timeout,
        ):
            result.append(chunk)

        return "".join(result)


async def _keepalive(page, request_id: str) -> None:
    while True:
        await asyncio.sleep(5)
        await page.evaluate(
            "data => window.postMessage(data, '*')",
            {"type": "streamKeepAlive", "requestId": request_id},
        )


async def _pump(messages, predicate, timeout: float):
    while True:
        message = await asyncio.wait_for(messages.get(), timeout=timeout)
        if predicate(message):
            return message


async def _wait_for(messages, type: str, timeout: float) -> dict:
    return await _pump(messages, lambda m: m["type"] == type, timeout)


async def _wait_for_chunk(messages, timeout: float) -> dict:
    return await _pump(
        messages,
        lambda m: m["type"] in ("streamData", "streamEnd", "streamError"),
        timeout,
    )