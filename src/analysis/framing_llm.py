"""Framing analysis via an LLM judge — more accurate than the regex in framing.py.

The regex in framing.py can't reliably tell "Israel kills 10" (Israel = actor)
from "10 Israelis killed" (Israelis = victims). An LLM resolves who-acted-on-whom
and whether a named agent is present, which is exactly the judgment the
agentless-framing metric depends on.

For each headline the judge returns:
  victim_side  : israeli | palestinian | both | neither   (replaces keyword guess)
  is_harm      : does the headline describe people being killed/harmed?
  agency       : named_actor | agentless | not_applicable
  actor        : the named actor, if any (free text, for spot-checking)

We then compute the same per-outlet Palestinian-vs-Israeli agentless gap as
framing.py, but on judged labels. Headlines are classified in batches via
structured outputs (Pydantic), so the result is schema-valid by construction.

Input : data/raw/headlines.csv  (outlet, title[, side])   — from src.ingest.headlines
Output: data/processed/framing_llm.csv + the gap, printed.

Run:
    python -m src.analysis.framing_llm                  # uses config judge.model
    python -m src.analysis.framing_llm --model claude-haiku-4-5
"""
from __future__ import annotations

import argparse
import sys
from typing import Literal, Optional

import pandas as pd
from pydantic import BaseModel

from src.common import PROCESSED, RAW, load_config

SYSTEM = """You classify news headlines about the Israel–Palestine conflict for a \
study of reporting framing. Judge ONLY the text given — do not use outside knowledge \
of the event, and do not infer who "really" was at fault. Be literal about grammar.

For each headline return:
- victim_side: who is harmed/killed in THIS headline — "israeli", "palestinian", \
"both", or "neither" (neither = no one is described as harmed, or victims' side is \
genuinely unstated).
- is_harm: true if the headline states that people were killed, wounded, or died; \
false otherwise.
- agency: for a harm headline, is a specific actor grammatically named as causing \
the harm? "named_actor" = an agent is the subject doing the killing/striking \
(e.g. "Israel kills 10", "Hamas rockets hit Tel Aviv"). "agentless" = the harm is \
stated with no actor as subject (e.g. "10 Palestinians killed", "Children die in \
Gaza blast", passive or intransitive). "not_applicable" = is_harm is false. \
A nationality next to a passive verb ("Israelis killed") is the VICTIM, so that is \
agentless, not named_actor.
- actor: the named actor causing harm, verbatim from the headline, or null.

Classify each numbered headline independently. Return one judgment per headline, \
preserving the given index."""


class Judgment(BaseModel):
    index: int
    victim_side: Literal["israeli", "palestinian", "both", "neither"]
    is_harm: bool
    agency: Literal["named_actor", "agentless", "not_applicable"]
    actor: Optional[str] = None


class Batch(BaseModel):
    judgments: list[Judgment]


def classify_batch(client, model: str, rows: list[tuple[int, str]]) -> list[Judgment]:
    listing = "\n".join(f"{i}. {title}" for i, title in rows)
    resp = client.messages.parse(
        model=model,
        max_tokens=8000,
        thinking={"type": "disabled"},  # literal classification — no thinking needed
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"Headlines:\n{listing}"}],
        output_format=Batch,
    )
    return resp.parsed_output.judgments


def main() -> int:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=cfg["judge"]["model"])
    ap.add_argument("--batch-size", type=int, default=cfg["judge"]["batch_size"])
    ap.add_argument("--limit", type=int, default=None, help="cap headlines (for a cheap trial run)")
    args = ap.parse_args()

    path = RAW / "headlines.csv"
    if not path.exists():
        print("Need data/raw/headlines.csv — run src.ingest.headlines first.", file=sys.stderr)
        return 2

    df = pd.read_csv(path)
    if args.limit:
        df = df.head(args.limit)
    if "title" not in df.columns:
        print("headlines.csv must have a 'title' column.", file=sys.stderr)
        return 2

    try:
        import anthropic
    except ImportError:
        print("pip install anthropic", file=sys.stderr)
        return 2
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

    rows = list(enumerate(df["title"].fillna("").tolist()))
    judged: dict[int, Judgment] = {}
    for start in range(0, len(rows), args.batch_size):
        chunk = rows[start:start + args.batch_size]
        print(f"  judging headlines {start}–{start + len(chunk) - 1} ({args.model})")
        try:
            for j in classify_batch(client, args.model, chunk):
                judged[j.index] = j
        except anthropic.APIError as exc:
            print(f"    batch failed, leaving unknown: {exc}", file=sys.stderr)

    df["victim_side"] = [judged[i].victim_side if i in judged else "neither" for i in range(len(df))]
    df["is_harm"] = [judged[i].is_harm if i in judged else False for i in range(len(df))]
    df["agency"] = [judged[i].agency if i in judged else "not_applicable" for i in range(len(df))]
    df["actor"] = [judged[i].actor if i in judged else None for i in range(len(df))]

    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED / "framing_llm.csv", index=False)

    harm = df[df["is_harm"]].copy()
    if harm.empty:
        print("No harm headlines judged.", file=sys.stderr)
        return 1
    harm["agentless"] = harm["agency"] == "agentless"
    by = harm.groupby(["outlet", "victim_side"]).agg(
        harm_headlines=("title", "count"),
        agentless=("agentless", "sum"),
    )
    by["agentless_share"] = by["agentless"] / by["harm_headlines"]
    print(by)

    share = by["agentless_share"].unstack("victim_side")
    if {"palestinian", "israeli"}.issubset(share.columns):
        gap = (share["palestinian"] - share["israeli"]).rename("pal_minus_isr_gap")
        print("\nAgentless-framing gap per outlet (Palestinian - Israeli victims), LLM-judged:")
        print(gap.sort_values(ascending=False).to_string())
        print("\nPositive => the outlet omits the named actor more often when "
              "Palestinians die than when Israelis die. Near zero => symmetric.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
