"""Evaluate the knowledge assistant on a labeled question set.

Metrics
  route accuracy        agent chose the expected route (retrieve / web_search / clarify)
  retrieval hit rate    expected document was among the retrieved sources
  citation validity     every [n] in the answer refers to a source that exists
  citation correctness  at least one citation points to the expected document
  answer accuracy       answer contains all expected facts (keywords)
  faithfulness (opt.)   LLM-as-judge score 1-5: is every claim supported by the sources?

Usage (from backend/):
  python -m eval.run_eval --ingest            # index ../samples, then evaluate
  python -m eval.run_eval --judge             # also run the LLM-as-judge (needs API key)
"""
import argparse
import json
import re
import time
import uuid
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from app import ingest
from app.agent.graph import run_agent
from app.providers import get_llm, is_fake

HERE = Path(__file__).parent
SAMPLES = HERE.parents[1] / "samples"


class Judgement(BaseModel):
    score: int = Field(ge=1, le=5, description="5 = every claim supported by the sources")
    explanation: str


JUDGE_PROMPT = """You are grading a RAG system. Score 1-5 how faithful the ANSWER is to the SOURCES.
5 = every claim is supported; 3 = some unsupported details; 1 = mostly unsupported or wrong.

SOURCES:
{sources}

QUESTION: {question}
ANSWER: {answer}"""


def judge(case: dict, result: dict) -> int | None:
    if is_fake() or not result["sources"]:
        return None
    sources = "\n\n".join(f"[{s['id']}] {s['snippet']}" for s in result["sources"])
    verdict = get_llm().with_structured_output(Judgement).invoke(
        JUDGE_PROMPT.format(sources=sources, question=case["question"], answer=result["answer"])
    )
    return verdict.score


def score_case(case: dict, result: dict) -> dict:
    ids = {s["id"]: s for s in result["sources"]}
    cited = [int(n) for n in re.findall(r"\[(\d+)\]", result["answer"])]
    expected = case["expected_source"]
    row = {
        "question": case["question"],
        "route": result["route"],
        "route_ok": result["route"] == case["expected_route"],
    }
    if expected:
        row["retrieval_hit"] = any(s["source"] == expected for s in result["sources"])
        row["citations_valid"] = bool(cited) and all(n in ids for n in cited)
        row["citation_correct"] = any(n in ids and ids[n]["source"] == expected for n in cited)
        answer = result["answer"].lower()
        row["answer_ok"] = all(k.lower() in answer for k in case["expected_keywords"])
    return row


def rate(rows: list[dict], key: str) -> str:
    vals = [r[key] for r in rows if r.get(key) is not None]
    return f"{sum(vals) / len(vals):.0%}" if vals else "n/a"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ingest", action="store_true", help="index the sample documents first")
    ap.add_argument("--judge", action="store_true", help="add LLM-as-judge faithfulness scores")
    args = ap.parse_args()

    if args.ingest:
        for f in sorted(SAMPLES.iterdir()):
            print("Indexed", ingest.ingest(f.read_bytes(), f.name))

    cases = json.loads((HERE / "dataset.json").read_text())
    rows = []
    for case in cases:
        start = time.perf_counter()
        result = run_agent(case["question"], thread_id=f"eval-{uuid.uuid4()}")
        row = score_case(case, result)
        row["seconds"] = round(time.perf_counter() - start, 2)
        if args.judge:
            row["faithfulness"] = judge(case, result)
        rows.append(row)
        flag = lambda k: {True: "yes", False: "no", None: "-"}[row.get(k)]
        print(f"{case['question'][:52]:<54} route={row['route']:<10} hit={flag('retrieval_hit'):<4}"
              f"cite={flag('citation_correct'):<4} answer={flag('answer_ok')}")

    summary = {
        "route_accuracy": rate(rows, "route_ok"),
        "retrieval_hit_rate": rate(rows, "retrieval_hit"),
        "citation_validity": rate(rows, "citations_valid"),
        "citation_correctness": rate(rows, "citation_correct"),
        "answer_accuracy": rate(rows, "answer_ok"),
    }
    scores = [r["faithfulness"] for r in rows if r.get("faithfulness")]
    if scores:
        summary["avg_faithfulness"] = f"{sum(scores) / len(scores):.2f} / 5"

    print("\n" + "\n".join(f"{k.replace('_', ' '):<22} {v}" for k, v in summary.items()))
    out = HERE / "results" / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "cases": rows}, indent=2))
    print(f"\nSaved {out.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
