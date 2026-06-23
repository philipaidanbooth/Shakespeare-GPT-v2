#!/usr/bin/env python3
"""
Eval runner for Shakespeare GPT v2.

Metrics per question:
  1. format_ok     — all 4 required markdown sections present
  2. citation_ok   — (Act X, Scene Y) in blockquote matches at least one returned source act
  3. judge_score   — LLM-as-judge 1-5 vs SparkNotes reference answer (claude-haiku-4-5-20251001)

Usage:
  python evals/run_eval.py
  python evals/run_eval.py --url https://your-railway-url.railway.app
  python evals/run_eval.py --dataset evals/sparknotes_set.csv --output evals/my_results.csv
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

REQUIRED_SECTIONS = [
    "## Context",
    "## Specific Moment",
    "## Quote Specifically",
    "## Analyse the Moment",
]

ACT_CITATION_RE = re.compile(r'\(Act\s+([\w]+),\s+Scene\s+([\w]+)\)', re.IGNORECASE)
ACT_PREFIX_RE = re.compile(r'ACT\s+([\w]+)', re.IGNORECASE)
SCENE_PREFIX_RE = re.compile(r'SCENE\s+([\w]+)', re.IGNORECASE)

JUDGE_SYSTEM = (
    "You are a Shakespeare literature expert grading an AI assistant's response. "
    "Return ONLY valid JSON with no extra text."
)

JUDGE_PROMPT = """\
Question: {question}

Reference answer (SparkNotes — treat as a minimum bar, not a ceiling. A better answer should still score highly):
{reference}

AI answer to grade:
{answer}

Score the AI answer 1-5:
5 = Excellent: covers all key points accurately, may go beyond the reference
4 = Good: covers most key points, minor gaps only
3 = Adequate: addresses the core point but misses important detail
2 = Weak: partially addresses the question with notable errors or gaps
1 = Poor: wrong, fabricated, or fails to address the question

Return ONLY: {{"score": <int 1-5>, "reasoning": "<one sentence>"}}"""


def parse_sections(answer: str) -> dict:
    """Split markdown answer into its named sections."""
    parts = {}
    current_header = None
    buf = []
    for line in answer.split('\n'):
        matched = next((s for s in REQUIRED_SECTIONS if line.strip().startswith(s)), None)
        if matched:
            if current_header is not None:
                parts[current_header] = '\n'.join(buf).strip()
            current_header = matched
            buf = []
        elif current_header is not None:
            buf.append(line)
    if current_header is not None:
        parts[current_header] = '\n'.join(buf).strip()
    return parts


def extract_blockquote_text(section_text: str) -> str:
    """Collect all '> ' prefixed lines into a single string."""
    lines = [l[2:] for l in section_text.split('\n') if l.startswith('> ')]
    return ' '.join(lines)


def extract_cited_act_scene(blockquote: str) -> tuple:
    """Return (act, scene) from an (Act X, Scene Y) citation, or (None, None)."""
    m = ACT_CITATION_RE.search(blockquote)
    if m:
        return m.group(1).upper(), m.group(2).upper()
    return None, None


def normalise_act(act_str: str) -> str:
    """'ACT III' → 'III', 'ACT 3' → '3'."""
    m = ACT_PREFIX_RE.match(act_str.strip())
    return m.group(1).upper() if m else act_str.strip().upper()


def normalise_scene(scene_title: str) -> str:
    """'SCENE IV. Before the castle.' → 'IV'."""
    m = SCENE_PREFIX_RE.match(scene_title.strip())
    return m.group(1).upper() if m else scene_title.strip().upper()


def check_format(sections: dict) -> bool:
    return all(s in sections for s in REQUIRED_SECTIONS)


def check_citation(sections: dict, sources: list) -> bool:
    """
    Verify the (Act X, Scene Y) cited in ## Quote Specifically matches at least
    one returned source by both act and scene.
    """
    quote_text = sections.get("## Quote Specifically", "")
    cited_act, cited_scene = extract_cited_act_scene(quote_text)
    if not cited_act or not cited_scene or not sources:
        return False
    source_act_scenes = {
        (normalise_act(s.get("act", "")), normalise_scene(s.get("scene_title", "")))
        for s in sources
    }
    return (cited_act, cited_scene) in source_act_scenes


def llm_judge(
    client: OpenAI,
    question: str,
    reference: str,
    answer: str,
) -> tuple:
    """Ask Claude Haiku via OpenRouter to score answer vs reference. Returns (score, reasoning)."""
    prompt = JUDGE_PROMPT.format(question=question, reference=reference, answer=answer)
    try:
        msg = client.chat.completions.create(
            model="anthropic/claude-haiku-4-5",
            max_tokens=256,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        text = msg.choices[0].message.content.strip()
        data = json.loads(text)
        return int(data["score"]), str(data.get("reasoning", ""))
    except json.JSONDecodeError:
        m = re.search(r'"score"\s*:\s*(\d)', text if 'text' in dir() else "")
        return (int(m.group(1)) if m else 0), "JSON parse error"
    except Exception as e:
        return 0, f"Judge error: {e}"


def run_eval(base_url: str, dataset_path: Path, output_path: Path):
    df = pd.read_csv(dataset_path)
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    results = []

    total = len(df)
    print(f"Evaluating {total} questions against {base_url}/answer\n")

    for idx, row in df.iterrows():
        question = row["question"]
        reference = row["reference_answer"]
        play = row["play"]
        qtype = row["type"]

        print(f"[{int(idx)+1}/{total}] {question[:65]}...", end="  ", flush=True)

        try:
            resp = requests.post(
                f"{base_url}/answer",
                json={"question": question, "k": 5, "filters": {"play": play}},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"API ERROR: {e}")
            results.append({
                "question": question, "play": play, "type": qtype,
                "format_ok": False, "citation_ok": False,
                "judge_score": 0, "judge_reasoning": str(e), "api_error": True,
            })
            continue

        answer = data["answer"]
        sources = data["sources"]
        sections = parse_sections(answer)

        format_ok = check_format(sections)
        citation_ok = check_citation(sections, sources)
        judge_score, judge_reasoning = llm_judge(client, question, reference, answer)

        results.append({
            "question": question,
            "play": play,
            "type": qtype,
            "format_ok": format_ok,
            "citation_ok": citation_ok,
            "judge_score": judge_score,
            "judge_reasoning": judge_reasoning,
            "api_error": False,
        })

        print(
            f"format={'✓' if format_ok else '✗'}  "
            f"citation={'✓' if citation_ok else '✗'}  "
            f"judge={judge_score}/5"
        )

    results_df = pd.DataFrame(results)
    results_df.to_csv(output_path, index=False)

    valid = results_df[~results_df["api_error"]]
    errors = results_df["api_error"].sum()

    print(f"\n{'='*55}")
    print(f"Results → {output_path}")
    print(f"\nOverall  ({len(valid)}/{total} successful, {errors} errors)")
    print(f"  Format compliance:   {valid['format_ok'].mean():.0%}")
    print(f"  Citation accuracy:   {valid['citation_ok'].mean():.0%}")
    print(f"  Judge score (mean):  {valid['judge_score'].mean():.2f} / 5")

    if len(valid) > 0:
        print(f"\nBy play:")
        for play, g in valid.groupby("play"):
            print(
                f"  {play:<32} "
                f"judge={g['judge_score'].mean():.2f}  "
                f"citation={g['citation_ok'].mean():.0%}"
            )

        print(f"\nBy type:")
        for qtype, g in valid.groupby("type"):
            print(
                f"  {qtype:<12} "
                f"judge={g['judge_score'].mean():.2f}  "
                f"citation={g['citation_ok'].mean():.0%}"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Shakespeare GPT evals")
    parser.add_argument(
        "--url", default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--dataset", default="evals/sparknotes_set.csv",
        help="Path to eval CSV dataset",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output CSV path (default: evals/results_YYYYMMDD_HHMMSS.csv)",
    )
    args = parser.parse_args()

    output = args.output or f"evals/results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    run_eval(
        base_url=args.url.rstrip("/"),
        dataset_path=Path(args.dataset),
        output_path=Path(output),
    )
