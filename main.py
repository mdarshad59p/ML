"""
Thin wrapper so hosts/platforms that specifically look for "main.py" as the
entry point still work. All real logic lives in bot.py — this just calls it.
"""
from bot import main

if __name__ == "__main__":
    main()
