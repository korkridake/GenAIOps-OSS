"""
Standalone example: LLM-based evaluation using Langfuse scores API.

This script generates a sample LLM response, then uses a second LLM call to
evaluate the quality of that response (LLM-as-a-judge pattern).  The numeric
score is posted back to Langfuse so it appears in the evaluation dashboard.

Run directly:
    python -m app.examples.evaluation
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import openai

from app.utils.llm_client import create_llm_client
from app.utils.tracing import TracingClient


EVAL_SYSTEM_PROMPT = """You are an expert evaluator of AI responses.
Score the following AI response on a scale of 0.0 to 1.0 for:
- Accuracy (is the answer factually correct?)
- Helpfulness (does it directly address the question?)
- Conciseness (is it appropriately brief without being terse?)

Return ONLY a JSON object like:
{"accuracy": 0.9, "helpfulness": 0.8, "conciseness": 0.7, "overall": 0.8}
No additional text."""


def evaluate_response(client: openai.OpenAI, question: str, answer: str) -> dict[str, float]:
    """Use a second LLM call to judge *answer* for *question*.

    Returns a dict of dimension → score (0.0–1.0).
    """
    eval_prompt = f"Question: {question}\n\nAI Response: {answer}"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": EVAL_SYSTEM_PROMPT},
                {"role": "user", "content": eval_prompt},
            ],
            max_tokens=100,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)
    except Exception as exc:
        print(f"  [eval] Evaluation LLM call failed: {exc}")
        return {}


@contextlib.contextmanager
def _noop_ctx() -> Any:
    """Yield a minimal stub so the with-statement works without Langfuse."""
    class _Stub:
        id = "no-trace"
    yield _Stub()


def run_evaluation() -> None:
    """Run a single generate → evaluate → score cycle."""
    client = create_llm_client()

    pk = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    sk = os.getenv("LANGFUSE_SECRET_KEY", "")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    tracer: TracingClient | None = None
    if pk and sk:
        tracer = TracingClient(public_key=pk, secret_key=sk, host=host)

    question = "What is the difference between supervised and unsupervised learning?"
    print(f"Question: {question}\n")

    # Step 1 — generate the answer
    ctx = tracer.trace(name="evaluation-demo", user_id="evaluator") if tracer else _noop_ctx()
    with ctx as trace:
        try:
            gen_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful ML tutor."},
                    {"role": "user", "content": question},
                ],
                max_tokens=150,
            )
            answer = gen_response.choices[0].message.content or ""
            print(f"Generated answer:\n{answer}\n")

            # Step 2 — evaluate with LLM-as-a-judge
            scores = evaluate_response(client, question, answer)
            print("Evaluation scores:")
            for dimension, score in scores.items():
                print(f"  {dimension}: {score:.2f}")

            # Step 3 — push scores to Langfuse
            if tracer and trace and scores:
                for dimension, value in scores.items():
                    tracer.score(
                        trace_id=trace.id,
                        name=f"llm-judge/{dimension}",
                        value=float(value),
                        comment="LLM-as-a-judge evaluation",
                    )
                tracer.flush()
                print(f"\nScores posted to Langfuse trace: {trace.id}")

        except Exception as exc:
            print(f"[error] {exc}")


def main() -> None:
    print("Evaluation Example — LLM-as-a-judge with Langfuse scoring")
    print("=" * 60)
    run_evaluation()


if __name__ == "__main__":
    main()
