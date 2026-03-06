# Evaluation with Langfuse

Langfuse provides a flexible evaluation framework that supports human feedback,
rule-based scoring, and LLM-as-a-judge patterns.

## Evaluation Concepts

| Concept      | Description                                                          |
|--------------|----------------------------------------------------------------------|
| **Score**    | A numeric or categorical rating attached to a trace or observation   |
| **Evaluator**| The entity that creates a score (human, rule, LLM)                  |
| **Dataset**  | A curated collection of input/output pairs for batch evaluation      |
| **Run**      | A batch execution of an LLM over a dataset                           |

---

## Manual Scoring via SDK

Attach a score to an existing trace:

```python
from langfuse import Langfuse

lf = Langfuse()

lf.score(
    trace_id="trace-abc123",
    name="helpfulness",
    value=0.9,              # float 0.0–1.0
    comment="Clear and concise answer",
)
lf.flush()
```

---

## LLM-as-a-Judge

Use a second LLM call to evaluate the quality of the first:

```python
from app.utils.llm_client import create_llm_client
from app.utils.tracing import TracingClient

client = create_llm_client()
tracer = TracingClient()

JUDGE_PROMPT = """Rate the following answer on accuracy (0.0-1.0).
Return JSON: {"accuracy": <score>, "reason": "<brief reason>"}"""

def evaluate(question: str, answer: str, trace_id: str) -> None:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": JUDGE_PROMPT},
            {"role": "user", "content": f"Q: {question}\nA: {answer}"},
        ],
    )
    import json
    result = json.loads(response.choices[0].message.content)
    tracer.score(
        trace_id=trace_id,
        name="accuracy",
        value=result["accuracy"],
        comment=result["reason"],
    )
    tracer.flush()
```

---

## Batch Evaluation with Datasets

### 1. Create a dataset

```python
from langfuse import Langfuse

lf = Langfuse()

dataset = lf.create_dataset(name="qa-benchmark-v1")

items = [
    {"input": "What is RAG?", "expected_output": "Retrieval-Augmented Generation ..."},
    {"input": "What is LiteLLM?", "expected_output": "A unified LLM API proxy ..."},
]

for item in items:
    lf.create_dataset_item(
        dataset_name="qa-benchmark-v1",
        input=item["input"],
        expected_output=item["expected_output"],
    )
```

### 2. Run the model over the dataset

```python
from langfuse import Langfuse
from app.utils.llm_client import create_llm_client

lf = Langfuse()
client = create_llm_client()

dataset = lf.get_dataset("qa-benchmark-v1")
run_name = "gpt-4o-mini-run-1"

for item in dataset.items:
    with item.observe(run_name=run_name) as trace:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": item.input}],
        )
        answer = response.choices[0].message.content
        trace.update(output=answer)

lf.flush()
```

### 3. Score the run

After running, attach scores (manually or via LLM judge):

```python
for item in dataset.items:
    run_item = item.get_run(run_name)
    score = evaluate_answer(item.input, run_item.output, item.expected_output)
    lf.score(
        trace_id=run_item.trace_id,
        name="correctness",
        value=score,
    )
lf.flush()
```

---

## Score Types

| Type            | Value format          | Example use case                   |
|-----------------|-----------------------|------------------------------------|
| Numeric (0–1)   | `float`               | Quality, accuracy, relevance       |
| Numeric (1–5)   | `float`               | RLHF star rating                   |
| Boolean         | `0.0` or `1.0`        | Pass/fail, contains PII            |
| Categorical     | `string`              | Thumbs up/down                     |

---

## Viewing Evaluation Results in the UI

1. Open <http://localhost:3000>
2. Navigate to **Scores** to see aggregate score statistics
3. Navigate to **Datasets → [dataset name] → Runs** to compare runs side-by-side

---

## Automated Evaluation Pipeline

For CI/CD integration, run evaluations automatically on every deployment:

```bash
# In CI
python -m app.examples.evaluation
# Check Langfuse scores via API
curl "http://localhost:3000/api/public/scores?runName=my-run&name=accuracy" \
  -H "Authorization: Basic $(echo -n $PK:$SK | base64)"
```
