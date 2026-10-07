import random


PLATFORMS: list[str] = [
    "X11; Linux x86_64",
    "Windows NT 6.1; WOW64",
    "Windows NT 10.0; Win64; x64",
    "Macintosh; Intel Mac OS X 10_10_5",
    "iPad; CPU OS 8_4_1 like Mac OS X",
    "Linux; U; Android 4.4.3; en-us"
]
ENGINES: list[str] = [
    "AppleWebKit/537.36 (KHTML, like Gecko)",
    "AppleWebKit/600.8.9 (KHTML, like Gecko)",
    "Gecko/20100101",
    "Trident/7.0; rv:11.0"
]
BROWSERS: list[str] = [
    "Chrome/45.0.2454.85 Safari/537.36",
    "Chromium/37.0.2062.94 Chrome/37.0.2062.94 Safari/537.36",
    "Firefox/40.0",
    "Version/8.0.8 Safari/600.8.9",
    "Mobile/12H321 Safari/600.1.4"
]


def generate_user_agent() -> str:
    return f"Mozilla/5.0 ({random.choice(PLATFORMS)}) {random.choice(ENGINES)} {random.choice(BROWSERS)}"
