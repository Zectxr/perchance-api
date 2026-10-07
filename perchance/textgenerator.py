from __future__ import annotations

import asyncio
import json
import random
from typing import AsyncGenerator

from . import errors
from .generator import Generator


class TextGenerator(Generator):
    """AI text generator"""

    BASE_URL = "https://text-generation.perchance.org/api"

    def __init__(self) -> None:
        super().__init__()

        self._lock: asyncio.Lock = asyncio.Lock()

    def is_running(self) -> bool:
        return self._lock.locked()

    async def stream(
        self,
        prompt: str,
        *,
        start_with: str | None = None,
        stop_sequences: list[str] | None = None,
        timeout: float | None = 5.0,
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
            Waiting timeout in seconds.
        """
        async with self._lock:
            await self._start()

            async with await self._context.new_page() as page:
                await page.goto(
                    f"{self.BASE_URL}/verifyUser"
                    f"?thread=0"
                    f"&__cacheBust={random.random()}"
                )

                content = await page.content()
                key_entry = content.find('"userKey":"')
                start_index = key_entry + len('"userKey":"')
                end_index = content.find('"', start_index)

                if key_entry == -1 or end_index == -1:
                    if "too_many_requests" in content:
                        raise errors.RateLimitError("Rate limit exceeded")
                    else:
                        raise errors.AuthenticationError("Failed to retrieve user key")

                key = content[start_index:end_index]

                url = (
                    f"{self.BASE_URL}/generate"
                    f"?userKey={key}"
                    f"&requestId=aiTextCompletion{random.randint(0, 2**30)}"
                    f"&__cacheBust={random.random()}"
                )
                body = {
                    "generatorName": "ai-text-generator",
                    "instruction": prompt,
                    "instructionTokenCount": 1,
                    "startWith": start_with or "",
                    "startWithTokenCount": 1,
                    "stopSequences": stop_sequences or [],
                }

                queue: asyncio.Queue[str] = asyncio.Queue()

                await page.expose_function("onChunk", queue.put)

                fetch_task = asyncio.create_task(page.evaluate("""
                    async ({ url, body }) => {
                        const controller = new AbortController();
                        window.abortFetch = () => controller.abort();

                        const response = await fetch(url, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(body),
                            signal: controller.signal
                        });

                        const reader = response.body.getReader();
                        const decoder = new TextDecoder();

                        while (true) {
                            const { value, done } = await reader.read();
                            if (done) break;
                            const chunk = decoder.decode(value, { stream: true });
                            await window.onChunk(chunk);
                        }
                    }
                """, {"url": url, "body": body}))

                while True:
                    try:
                        chunk = await asyncio.wait_for(queue.get(), timeout=timeout)
                        for line in chunk.splitlines():
                            if line.startswith("t:"):
                                yield json.loads(line[2:])
                            elif line.startswith("data:"):
                                return
                    except asyncio.TimeoutError:
                        await page.evaluate("window.abortFetch()")
                        fetch_task.cancel()
                        raise errors.ConnectionError()

    async def text(
        self,
        prompt: str,
        *,
        start_with: str | None = None,
        stop_sequences: list[str] | None = None,
        timeout: float | None = 5.0,
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
            Waiting timeout in seconds.
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
