"""Framing & language analysis on article headlines.

Reads a CSV of headlines (data/raw/headlines.csv with columns: outlet, title,
side) and scores two well-studied framing markers:

  1. Agent attribution: is an actor *named* as doing the killing
     ("Israel kills 10") vs. agentless/passive ("10 killed in Gaza",
     "Palestinians die in strike")? Agentless death framing is the classic
     way responsibility is softened.
  2. Lexical choice: "killed/slain" (violent agency) vs "died/dead" (no agent).

Output reports, per outlet and per side, the share of death-headlines that are
agentless. A neutral outlet should apply agentless framing at similar rates
regardless of who the victims are; a gap is the bias signal.

Headlines come from `src/ingest/headlines.py` (GDELT artlist) — or any CSV with
`outlet,title,side` columns, so you can hand-curate or swap the source.

Limitation: agent detection is a regex heuristic. It keys on active verb forms
adjacent to a named actor and cannot fully resolve subject vs. object in every
construction. For a publishable result, replace `is_agentless` with a spaCy
dependency parse that checks the grammatical subject of the kill verb.

Run:
    python -m src.analysis.framing
"""
from __future__ import annotations

import re
import sys

import pandas as pd

from src.common import PROCESSED, RAW

# Any death/violence headline, active or passive (so "Israel kills" is counted
# AND classified as agentful, not silently dropped like a past-tense-only regex).
DEATH = re.compile(r"\b(kill(s|ed|ing)?|dead|die[sd]?|slain|perish\w*|massacre\w*)\b", re.I)
# A named actor performing the act, e.g. "Israel kills", "Hamas fires rockets".
# Only ACTIVE verb forms count (kills/strikes), never the passive past participle
# "killed" — "Israelis killed" is victim framing, not the Israelis acting.
ACTIVE_AGENT = re.compile(
    r"\b(israel\w*|idf|hamas|hezbollah|militants?|gunmen|forces|troops|soldiers)\b"
    r"\s+\w*\s*(kills?|fires?|strikes?|launch(?:es)?|hits?|bombs?|shells?|raids?)\b",
    re.I)


def is_death_headline(title: str) -> bool:
    return bool(DEATH.search(title or ""))


def is_agentless(title: str) -> bool:
    """A death headline with no named actor performing the act."""
    return is_death_headline(title) and not ACTIVE_AGENT.search(title or "")


def main() -> int:
    path = RAW / "headlines.csv"
    if not path.exists():
        print("Need data/raw/headlines.csv (outlet,title,side). See module "
              "docstring / METHODOLOGY.md for how to harvest from GDELT.",
              file=sys.stderr)
        return 2

    df = pd.read_csv(path)
    df["is_death"] = df["title"].apply(is_death_headline)
    deaths = df[df["is_death"]].copy()
    if deaths.empty:
        print("No death-headlines matched.", file=sys.stderr)
        return 1
    deaths["agentless"] = deaths["title"].apply(is_agentless)

    by = deaths.groupby(["outlet", "side"]).agg(
        death_headlines=("title", "count"),
        agentless=("agentless", "sum"),
    )
    by["agentless_share"] = by["agentless"] / by["death_headlines"]
    print(by)

    # The headline harvester tags `side` as the victim group. Compute, per
    # outlet, the gap in agentless framing between Palestinian and Israeli deaths.
    share = by["agentless_share"].unstack("side")
    if {"palestinian", "israeli"}.issubset(share.columns):
        gap = (share["palestinian"] - share["israeli"]).rename("pal_minus_isr_gap")
        print("\nAgentless-framing gap per outlet (Palestinian - Israeli victims):")
        print(gap.sort_values(ascending=False).to_string())
        print("\nPositive => the outlet strips the named actor more often when "
              "Palestinians die than when Israelis die. Negative => the reverse. "
              "Near zero => symmetric framing.")
    else:
        print("\nNeed both 'palestinian' and 'israeli' victim sides present to "
              "compute the gap; harvest more headlines or check side tagging.")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    by.to_csv(PROCESSED / "framing.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
