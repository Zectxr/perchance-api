import asyncio
from perchance import TextGenerator


async def main():
    async with TextGenerator() as gen:
        prompt = input("Prompt: ")

        print("Result: ", end="")
        async for chunk in gen.stream(prompt):
            print(chunk, end="")


if __name__ == "__main__":
    asyncio.run(main())
