from __future__ import annotations

import asyncio
import io
import json
import random
import urllib.error
import urllib.request
import uuid
from typing import Literal
from urllib.parse import urljoin

import aiofiles

from . import errors

API = "https://image-generation.perchance.org/api"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://image-generation.perchance.org/embed",
    "Origin": "https://image-generation.perchance.org",
}


async def _request(url: str, body: dict | None = None, timeout: int = 60) -> bytes:
    data = json.dumps(body).encode() if body is not None else None
    headers = dict(_HEADERS)
    if data:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        response = await asyncio.to_thread(
            lambda: urllib.request.urlopen(request, timeout=timeout).read()
        )
        return response
    except urllib.error.HTTPError as error:
        raise errors.ConnectionError(error.read().decode("utf-8", "replace")) from error


async def _verify_user() -> str:
    url = (
        f"{API}/verifyUser"
        f"?browserId={uuid.uuid4().hex}"
        f"&thread=0"
        f"&__cacheBust={random.random()}"
    )
    result = json.loads(await _request(url))
    if result.get("status") == "success":
        return result["userKey"]
    if result.get("status") == "too_many_requests":
        raise errors.RateLimitError("Rate limit exceeded")
    raise errors.AuthenticationError(f"Failed to retrieve user key: {result}")


class ImageResult:
    """Image generation result."""

    def __init__(
        self, 
        *, 
        generator: ImageGenerator,
        image_id: str,
        file_extension: str,
        seed: int,
        prompt: str,
        width: int,
        height: int,
        guidance_scale: float,
        negative_prompt: str | None,
        maybe_nsfw: bool,
        proxy_download: str | None = None,
    ) -> None:
        self._generator: ImageGenerator = generator

        self.image_id: str = image_id
        """Image ID."""
        self.file_extension: str = file_extension
        """File extension."""
        self.seed: int = seed
        """Generation seed."""
        self.prompt: str = prompt
        """Image prompt."""
        self.width: int = width
        """Image width."""
        self.height: int = height
        """Image height."""
        self.guidance_scale: float = guidance_scale
        """Guidance scale."""
        self.negative_prompt: str | None = negative_prompt
        """Negative prompt."""
        self.maybe_nsfw: bool = maybe_nsfw
        """Whether the image may be NSFW."""
        self.proxy_download: str | None = proxy_download
        """Proxy download URL returned by Perchance, when available."""
    
    def __str__(self) -> str:
        return f"{self.image_id}.{self.file_extension}"

    @property
    def size(self) -> tuple[int, int]:
        """Image size as (width, height)."""
        return self.width, self.height

    async def download(self) -> io.BytesIO:
        """Download the image."""
        urls = []
        if self.proxy_download:
            urls.append(urljoin(API + "/", self.proxy_download))
        urls.append(f"{API}/downloadTemporaryImage?imageId={self.image_id}")

        last_error: Exception | None = None
        for url in urls:
            try:
                return io.BytesIO(await _request(url, timeout=120))
            except errors.ConnectionError as error:
                last_error = error
        raise last_error

    async def save(self, filename: str | None = None) -> None:
        """Download and save the image.

        Parameters
        ----------
        filename: str | None
            Name of the output file.
        """
        file = filename or f"{self.image_id}.{self.file_extension}"

        async with aiofiles.open(file, 'wb') as f:
            img = await self.download()
            await f.write(img.read())
            

class ImageGenerator:
    """AI image generator"""

    BASE_URL = API

    async def __aenter__(self) -> ImageGenerator:
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None

    async def image(
        self,
        prompt: str,
        *,
        negative_prompt: str | None = None,
        seed: int = -1,
        shape: Literal['portrait', 'square', 'landscape'] = 'square',
        guidance_scale: float = 7.0
    ) -> ImageResult:
        """
        Generate image.

        Parameters
        ----------
        prompt: str
            Image description.
        negative_prompt: str | None
            Things you do NOT want to see in the image.
        seed: int
            Generation seed.
        shape: str
            Image shape. Can be either `portrait`, `square` or `landscape`.
        guidance_scale: float
            Accuracy of the prompt in range `1-30`. 
        """
        if shape == 'portrait':
            resolution = '512x768'
        elif shape == 'square':
            resolution = '768x768'
        elif shape == 'landscape':
            resolution = '768x512'
        else:
            raise ValueError(f"Invalid shape: {shape}")

        key = await _verify_user()

        url = (
            f"{API}/generate"
            f"?userKey={key}"
            f"&requestId=aiImageCompletion{random.randint(0, 2**30)}"
            f"&__cacheBust={random.random()}"
        )
        body = {
            "generatorName": "ai-image-generator",
            "channel": "ai-text-to-image-generator",
            "subChannel": "public",
            "prompt": prompt,
            "negativePrompt": negative_prompt or "",
            "seed": seed,
            "resolution": resolution,
            "guidanceScale": guidance_scale
        }

        response = json.loads(await _request(url, body))
        if response.get("status") != "success":
            raise errors.ConnectionError(f"Failed to generate image: {response}")

        return ImageResult(
            generator=self,
            image_id=response['imageId'],
            file_extension=response['fileExtension'],
            seed=response['seed'],
            prompt=response['prompt'],
            width=response['width'],
            height=response['height'],
            guidance_scale=response['guidanceScale'],
            negative_prompt=response['negativePrompt'],
            maybe_nsfw=response['maybeNsfw'],
            proxy_download=response.get('imageDownloadUrl'),
        )