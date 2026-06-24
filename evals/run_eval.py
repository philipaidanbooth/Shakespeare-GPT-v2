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
QUOTE_TEXT_RE = re.compile(r'"([^"]{20,})"')
ACT_PREFIX_RE = re.compile(r'ACT\s+([\w]+)', re.IGNORECASE)
SCENE_PREFIX_RE = re.compile(r'SCENE\s+([\w]+)', re.IGNORECASE)

BOLD_HEADER_RE = re.compile(r'^\*\*(.+?)\*\*:?\s*$')

# Checked in priority order — explicit word matches before ambiguous phrase matches
SECTION_MAP = [
    ("## Analyse the Moment", re.compile(r'analys', re.IGNORECASE)),
    ("## Context",            re.compile(r'\bcontext\b|\bbackground\b', re.IGNORECASE)),
    ("## Specific Moment",    re.compile(r'specific moment|specific scene|dramatic situation', re.IGNORECASE)),
    ("## Quote Specifically", re.compile(r'quote', re.IGNORECASE)),
    ("## Specific Moment",    re.compile(r'\bspecific\b|\bmoment\b|\bscene\b', re.IGNORECASE)),
    ("## Context",            re.compile(r'\bdramatic\b', re.IGNORECASE)),
]


def detect_header(line: str) -> Optional[str]:
    """Return canonical section name if line is a ## or **bold** header, else None."""
    stripped = line.strip()
    for canonical in REQUIRED_SECTIONS:
        if stripped.startswith(canonical):
            return canonical
    m = BOLD_HEADER_RE.match(stripped)
    if m:
        text = m.group(1)
        for canonical, pattern in SECTION_MAP:
            if pattern.search(text):
                return canonical
    return None

JUDGE_SYSTEM = (
    "You are a Shakespeare literature expert grading an AI assistant's response. "
    "You must respond with ONLY a JSON object — no markdown, no code blocks, no extra text."
)

JUDGE_EXAMPLE_Q = """\
Question: Why does Hamlet delay killing Claudius?

Reference answer: Hamlet delays because he is a deeply thoughtful and philosophical person who is paralyzed by doubt.

AI answer to grade:
Hamlet hesitates because he fears making a mistake and struggles with moral uncertainty.

Score the AI answer 1-5:
5 = Excellent: covers all key points accurately, may go beyond the reference
4 = Good: covers most key points, minor gaps only
3 = Adequate: addresses the core point but misses important detail
2 = Weak: partially addresses the question with notable errors or gaps
1 = Poor: wrong, fabricated, or fails to address the question"""

JUDGE_EXAMPLE_A = '{"score": 3, "reasoning": "Captures the hesitation but omits the philosophical depth and specific theological reasoning shown in the play."}'

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
1 = Poor: wrong, fabricated, or fails to address the question"""


def parse_sections(answer: str) -> dict:
    """Split markdown answer into its named sections, handling both ## and **bold** headers."""
    parts = {}
    current_header = None
    buf = []
    for line in answer.split('\n'):
        matched = detect_header(line)
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


def check_citation(answer: str, sources: list):
    """
    Verify the cited quote exists in a retrieved chunk. Returns True/False/None.
    None means chunk text wasn't available (old backend build) — not a failure.
    """
    # If no source has text content, we can't verify — report as unavailable
    if not any(s.get("text", "") for s in sources):
        return None

    m = QUOTE_TEXT_RE.search(answer)
    if m:
        words = re.sub(r'[^\w\s]', '', m.group(1).lower()).split()
        key_phrase = ' '.join(words[:6])
        for s in sources:
            chunk = re.sub(r'[^\w\s]', '', s.get("text", "").lower())
            if key_phrase in chunk:
                return True
        return False

    # Fallback: act/scene metadata match
    cited_act, cited_scene = extract_cited_act_scene(answer)
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
    text = ""
    try:
        msg = client.chat.completions.create(
            model="anthropic/claude-haiku-4-5",
            max_tokens=300,
            temperature=0,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": JUDGE_EXAMPLE_Q},
                {"role": "assistant", "content": JUDGE_EXAMPLE_A},
                {"role": "user", "content": prompt},
            ],
        )
        text = msg.choices[0].message.content.strip()
        # Strip markdown code fences if model wraps in ```json ... ```
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        data = json.loads(text)
        return int(data["score"]), str(data.get("reasoning", ""))
    except json.JSONDecodeError:
        m = re.search(r'"score"\s*:\s*(\d)', text)
        return (int(m.group(1)) if m else None), f"JSON parse error: {text[:80]}"
    except Exception as e:
        return None, f"Judge error: {e}"


def run_eval(base_url: str, dataset_path: Path, output_path: Path, limit: Optional[int] = None) -> tuple:
    df = pd.read_csv(dataset_path)
    if limit:
        df = df.head(limit)
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
        citation_ok = check_citation(answer, sources)
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

        cite_str = "N/A" if citation_ok is None else ("✓" if citation_ok else "✗")
        judge_str = f"{judge_score}/5" if judge_score is not None else "err"
        print(
            f"format={'✓' if format_ok else '✗'}  "
            f"citation={cite_str}  "
            f"judge={judge_str}"
        )

    results_df = pd.DataFrame(results)
    results_df.to_csv(output_path, index=False)

    valid = results_df[~results_df["api_error"]]
    errors = results_df["api_error"].sum()

    scored = valid[valid["judge_score"].notna()]
    cited  = valid[valid["citation_ok"].notna()]
    parse_errors = valid["judge_score"].isna().sum()

    print(f"\n{'='*55}")
    print(f"Results → {output_path}")
    print(f"\nOverall  ({len(valid)}/{total} answered, {errors} API errors)")
    print(f"  Format compliance:   {valid['format_ok'].mean():.0%}")
    if len(cited) > 0:
        print(f"  Citation accuracy:   {cited['citation_ok'].mean():.0%}  ({len(valid)-len(cited)} N/A)")
    else:
        print(f"  Citation accuracy:   N/A (no chunk text returned — redeploy backend)")
    if len(scored) > 0:
        print(f"  Judge score (mean):  {scored['judge_score'].mean():.2f} / 5  ({parse_errors} parse errors excluded)")
    else:
        print(f"  Judge score (mean):  N/A ({parse_errors} parse errors)")

    if len(valid) > 0:
        print(f"\nBy play:")
        for play, g in valid.groupby("play"):
            g_scored = g[g["judge_score"].notna()]
            g_cited  = g[g["citation_ok"].notna()]
            judge_s  = f"{g_scored['judge_score'].mean():.2f}" if len(g_scored) else "N/A"
            cite_s   = f"{g_cited['citation_ok'].mean():.0%}" if len(g_cited) else "N/A"
            print(f"  {play:<32} judge={judge_s}  citation={cite_s}")

        print(f"\nBy type:")
        for qtype, g in valid.groupby("type"):
            g_scored = g[g["judge_score"].notna()]
            g_cited  = g[g["citation_ok"].notna()]
            judge_s  = f"{g_scored['judge_score'].mean():.2f}" if len(g_scored) else "N/A"
            cite_s   = f"{g_cited['citation_ok'].mean():.0%}" if len(g_cited) else "N/A"
            print(f"  {qtype:<12} judge={judge_s}  citation={cite_s}")

    return results_df, valid, int(errors)


def save_to_db(results_df: pd.DataFrame, valid: pd.DataFrame, errors: int):
    import psycopg2
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set — skipping DB save")
        return
    if "sslmode" not in db_url:
        db_url += "?sslmode=require"
    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            scored = valid[valid["judge_score"].notna()]
            cited  = valid[valid["citation_ok"].notna()]
            cur.execute(
                "INSERT INTO eval_runs (total, errors, format_pct, citation_pct, judge_avg) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (
                    len(results_df),
                    errors,
                    float(valid["format_ok"].mean()) if len(valid) > 0 else 0.0,
                    float(cited["citation_ok"].mean()) if len(cited) > 0 else None,
                    float(scored["judge_score"].mean()) if len(scored) > 0 else None,
                ),
            )
            run_id = cur.fetchone()[0]
            for _, row in results_df.iterrows():
                cur.execute(
                    "INSERT INTO eval_results "
                    "(run_id, question, play, type, format_ok, citation_ok, judge_score, judge_reasoning, api_error) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        run_id, row["question"], row["play"], row["type"],
                        bool(row["format_ok"]), bool(row["citation_ok"]),
                        int(row["judge_score"]), str(row["judge_reasoning"]),
                        bool(row["api_error"]),
                    ),
                )
    print(f"Saved to DB (run_id={run_id})")


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
    parser.add_argument(
        "--save-to-db", action="store_true",
        help="Save results to Railway Postgres DB for display on the evals page",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Only evaluate the first N questions (useful for smoke tests)",
    )
    args = parser.parse_args()

    output = args.output or f"evals/results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    results_df, valid, errors = run_eval(
        base_url=args.url.rstrip("/"),
        dataset_path=Path(args.dataset),
        output_path=Path(output),
        limit=args.limit,
    )
    if args.save_to_db:
        save_to_db(results_df, valid, errors)
