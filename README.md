# perchance
[![pypi](https://img.shields.io/pypi/v/perchance)](https://pypi.org/project/perchance)
[![python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads)
[![BuyMeACoffee](https://img.shields.io/badge/support-yellow)](https://www.buymeacoffee.com/eeemoon)

Unofficial Python API for [Perchance](https://perchance.org).

## Installation
To install this module, run the following command:
```
pip install perchance
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