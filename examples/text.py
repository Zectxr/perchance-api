import asyncio
from perchance import TextGenerator


async def main():
    # A browser window opens so the embed can complete its anti-bot
    # verification. Pass headless=True to hide it (may fail verification).
    async with TextGenerator() as gen:
        prompt = input("Prompt: ")

        print("Result: ", end="")
        async for chunk in gen.stream(prompt):
            print(chunk, end="")
        print()


if __name__ == "__main__":
    asyncio.run(main())