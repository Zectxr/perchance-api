# perchance-api
[![pypi](https://img.shields.io/pypi/v/perchance-api)](https://pypi.org/project/perchance-api)
[![python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads)

Unofficial Python API for [Perchance](https://perchance.org).

## Installation
To install this module, run the following command:
```
pip install perchance-api
```

## Examples
### Text generation
```python
import asyncio
from perchance import TextGenerator

async def main():
    async with TextGenerator() as gen:
        prompt = "How far is the Moon?"

        async for chunk in gen.stream(prompt):
            print(chunk, end='')

asyncio.run(main())
```

> The text generator drives the official Perchance embed in a browser so its
> anti-bot verification can complete. A browser window opens by default; pass
> `TextGenerator(headless=True)` to hide it (verification may then fail).

### Image generation
```python
import asyncio
from PIL import Image
from perchance import ImageGenerator

async def main():
    async with ImageGenerator() as gen:
        prompt = "Fantasy landscape"

        result = await gen.image(prompt, shape='landscape')
        binary = await result.download()
        image = Image.open(binary)
        image.show()

asyncio.run(main())
```

## Credits
Originally created by [eeemoonYurii](https://github.com/eeemoon) as the
[`perchance`](https://github.com/eeemoon/perchance) package. This fork
(`perchance-api`) rewrites the API calls and adds the describe/streaming
updates.