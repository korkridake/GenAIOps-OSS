"""
Standalone example: creating and using Langfuse prompt management.

Demonstrates:
- Creating a prompt via the Langfuse SDK
- Fetching a versioned prompt for use in a chat completion
- Compiling a prompt template with variable substitution

Run directly:
    python -m app.examples.prompt_management
"""

from __future__ import annotations

import os
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import openai
from langfuse import Langfuse

from app.utils.llm_client import create_llm_client


PROMPT_NAME = "customer-support-system"
PROMPT_TEMPLATE = (
    "You are a helpful customer support agent for {{company_name}}. "
    "Your tone is {{tone}}. "
    "Always acknowledge the customer's concern before providing a solution. "
    "Keep responses concise and actionable."
)


def ensure_prompt_exists(lf: Langfuse) -> None:
    """Create the demo prompt in Langfuse if it doesn't already exist."""
    try:
        lf.create_prompt(
            name=PROMPT_NAME,
            prompt=PROMPT_TEMPLATE,
            labels=["production"],
            config={
                "model": "gpt-4o-mini",
                "temperature": 0.3,
                "max_tokens": 300,
            },
        )
        print(f"Prompt '{PROMPT_NAME}' created in Langfuse.")
    except Exception as exc:
        # Prompt likely already exists — not a fatal error
        print(f"Prompt creation skipped ({exc})")


def fetch_and_compile_prompt(lf: Langfuse, variables: dict[str, str]) -> str:
    """Fetch the prompt and compile it with *variables*.

    Returns the raw template if compilation fails.
    """
    try:
        prompt_obj = lf.get_prompt(PROMPT_NAME)
        compiled = prompt_obj.compile(**variables)
        return compiled
    except Exception as exc:
        print(f"[warn] Could not fetch prompt from Langfuse: {exc}")
        # Apply simple string substitution as fallback
        result = PROMPT_TEMPLATE
        for key, value in variables.items():
            result = result.replace("{{" + key + "}}", value)
        return result


def demo_prompt_usage(lf: Langfuse, client: openai.OpenAI) -> None:
    """Run a chat completion using a managed prompt."""
    variables = {"company_name": "Acme Corp", "tone": "friendly and professional"}
    system_prompt = fetch_and_compile_prompt(lf, variables)
    print(f"\nCompiled system prompt:\n{system_prompt}\n")

    user_message = "I ordered a product 10 days ago and it still hasn't arrived."
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=200,
        )
        print(f"Customer: {user_message}")
        print(f"Agent   : {response.choices[0].message.content}")
    except Exception as exc:
        print(f"[error] Chat completion failed: {exc}")


def main() -> None:
    print("Prompt Management Example — Langfuse prompt versioning")
    print("=" * 60)

    pk = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    sk = os.getenv("LANGFUSE_SECRET_KEY", "")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    if not pk or not sk:
        print("[warn] LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set.")
        print("       Set them in .env to use Langfuse prompt management.")
        return

    lf = Langfuse(public_key=pk, secret_key=sk, host=host)
    client = create_llm_client()

    ensure_prompt_exists(lf)
    demo_prompt_usage(lf, client)

    lf.flush()
    print("\nDone.")


if __name__ == "__main__":
    main()
