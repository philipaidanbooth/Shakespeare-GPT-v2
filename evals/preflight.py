#!/usr/bin/env python3
"""
Preflight checks for Shakespeare GPT v2 evals.
Run this before a full eval to confirm everything is wired up correctly.

Usage:
  python evals/preflight.py
  python evals/preflight.py --url https://your-railway-url.railway.app
"""

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

BACKEND_URL = "https://shakespeare-gpt-v2-production-3c45.up.railway.app"
DATASET = Path(__file__).parent / "sparknotes_set.csv"

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
WARN = "\033[93m!\033[0m"

failures = []


def check(name: str, ok: bool, detail: str = ""):
    symbol = PASS if ok else FAIL
    print(f"  {symbol}  {name}" + (f": {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def section(title: str):
    print(f"\n{title}")
    print("-" * len(title))


# --- 1. Health ---
def check_health(url: str):
    section("1. Backend health")
    try:
        r = requests.get(f"{url}/health", timeout=15)
        data = r.json()
        check("HTTP 200", r.status_code == 200, f"got {r.status_code}")
        check('Returns {"status": "ok"}', data.get("status") == "ok", str(data))
    except Exception as e:
        check("Reachable", False, str(e))


# --- 2. Play names ---
def check_plays(url: str):
    section("2. Play names in ChromaDB")
    df = pd.read_csv(DATASET)
    csv_plays = set(df["play"].unique())
    try:
        r = requests.get(f"{url}/plays", timeout=15)
        if r.status_code == 404:
            check("GET /plays endpoint exists", False, "deploy latest code first")
            return set()
        data = r.json()
        db_plays = set(data.get("plays", []))
        check(f"Total docs loaded", data.get("total_docs", 0) > 0, f"{data.get('total_docs', 0)} docs")
        missing = csv_plays - db_plays
        check(
            "All eval plays found in ChromaDB",
            len(missing) == 0,
            f"missing: {missing}" if missing else "",
        )
        extra = db_plays - csv_plays
        if extra:
            print(f"  {WARN}  Extra plays in DB (not in eval set): {extra}")
        return db_plays
    except Exception as e:
        check("GET /plays reachable", False, str(e))
        return set()


# --- 3. Answer endpoint ---
def check_answer(url: str):
    section("3. /answer endpoint")
    try:
        r = requests.post(
            f"{url}/answer",
            json={"question": "Why does Iago hate Othello?", "k": 5, "filters": {"play": "Othello"}},
            timeout=60,
        )
        check("HTTP 200", r.status_code == 200, f"got {r.status_code} — {r.text[:120]}")
        if r.status_code != 200:
            return None
        data = r.json()
        check("Has 'answer' field", "answer" in data)
        check("Has 'sources' field", "sources" in data)
        sources = data.get("sources", [])
        check("At least 3 sources returned", len(sources) >= 3, f"got {len(sources)}")
        has_text = all(s.get("text") for s in sources)
        check(
            "All sources have text field",
            has_text,
            "text field missing — redeploy backend" if not has_text else "",
        )
        answer = data.get("answer", "")
        has_sections = any(h in answer for h in ["## Context", "## Specific Moment", "**Context", "**Analyse"])
        check("Answer contains section headers", has_sections, answer[:80] if not has_sections else "")
        return data
    except Exception as e:
        check("/answer reachable", False, str(e))
        return None


# --- 4. Judge ---
def check_judge(answer_data: dict | None):
    section("4. LLM judge (OpenRouter)")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    check("OPENROUTER_API_KEY set", bool(api_key))
    if not api_key:
        return

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    try:
        msg = client.chat.completions.create(
            model="anthropic/claude-haiku-4-5",
            max_tokens=150,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON with keys: score (int 1-5) and reasoning (string)."},
                {"role": "user", "content": 'Score this answer 1-5: "Iago hates Othello because of jealousy." vs reference "Iago hates Othello due to jealousy and suspected affair."'},
            ],
        )
        text = msg.choices[0].message.content.strip()
        data = json.loads(text)
        check("Judge returns valid JSON", True)
        check("JSON has 'score' field", "score" in data, str(data))
        check("Score is int 1-5", isinstance(data.get("score"), int) and 1 <= data["score"] <= 5, str(data.get("score")))
        check("JSON has 'reasoning' field", "reasoning" in data)
    except json.JSONDecodeError as e:
        check("Judge returns valid JSON", False, f"parse error: {text[:80]}")
    except Exception as e:
        check("Judge reachable", False, str(e))


# --- 5. Dataset ---
def check_dataset():
    section("5. Eval dataset")
    check("sparknotes_set.csv exists", DATASET.exists())
    if not DATASET.exists():
        return
    df = pd.read_csv(DATASET)
    check("Has required columns", all(c in df.columns for c in ["question", "reference_answer", "play", "type"]))
    check(f"Row count", len(df) > 0, f"{len(df)} questions")
    missing_refs = df["reference_answer"].isna().sum()
    check("No missing reference answers", missing_refs == 0, f"{missing_refs} missing" if missing_refs else "")


# --- Summary ---
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=BACKEND_URL)
    args = parser.parse_args()
    url = args.url.rstrip("/")

    print(f"\nShakespeare GPT v2 — Preflight Check")
    print(f"Backend: {url}")
    print("=" * 45)

    check_health(url)
    check_plays(url)
    answer_data = check_answer(url)
    check_judge(answer_data)
    check_dataset()

    print(f"\n{'=' * 45}")
    if failures:
        print(f"\033[91mFAILED\033[0m — {len(failures)} check(s) failed:")
        for f in failures:
            print(f"  • {f}")
        print("\nFix the above before running full evals.")
        sys.exit(1)
    else:
        print(f"\033[92mALL CHECKS PASSED\033[0m — ready to run full evals:")
        print(f"  python evals/run_eval.py --url {url} --save-to-db")


if __name__ == "__main__":
    main()
