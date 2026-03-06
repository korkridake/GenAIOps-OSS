"""
Standalone example: chat completions with different models via LiteLLM proxy.

Run directly:
    python -m app.examples.chat_completion
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.utils.llm_client import create_llm_client


MODELS = [
    "gpt-4o-mini",
    "gpt-3.5-turbo",
    "claude-3-haiku",
]

QUESTION = "Explain the difference between fine-tuning and RAG in two sentences."


def run_model(model: str) -> None:
    """Send the demo question to *model* and print the response."""
    client = create_llm_client()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a concise technical assistant."},
                {"role": "user", "content": QUESTION},
            ],
            max_tokens=200,
        )
        print(f"\n[{model}]")
        print(response.choices[0].message.content)
        if response.usage:
            total = response.usage.total_tokens
            print(f"  → {total} tokens used")
    except Exception as exc:
        print(f"\n[{model}] ERROR: {exc}")


def main() -> None:
    print("Chat Completion Example — multiple models via LiteLLM proxy")
    print(f"Question: {QUESTION}\n")
    for model in MODELS:
        run_model(model)
    print("\nDone.")


if __name__ == "__main__":
    main()
