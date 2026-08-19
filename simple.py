"""
A simple chat REPL — no tools, just conversation.

Uses invoke_model() to talk to any supported backend:
  claude, gemini, ollama, api, vertex.

Usage:
  MODEL=ollama:gemma3:27b python simple.py
  MODEL=claude python simple.py
"""

import os
import sys

from llm import invoke_model


def main():
    model = os.environ.get("MODEL", "claude")

    print(f"Simple Chat — model: {model} — type 'quit' to exit")
    print()

    while True:
        try:
            user_input = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.strip().lower() in ("quit", "exit"):
            break

        if not user_input.strip():
            continue

        try:
            response = invoke_model(user_input, model=model)
            print()
            print(response)
            print()
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
