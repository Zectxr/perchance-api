import asyncio
from PIL import Image
from perchance import ImageGenerator


async def main():
    async with ImageGenerator() as gen:
        prompt = input("Prompt: ")
        print("Generating...")

        result = await gen.image(prompt)
        binary = await result.download()
        image = Image.open(binary)
        image.show()


if __name__ == "__main__":
    asyncio.run(main())
