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

Headlines can come from GDELT artlist mode (mode=artlist&format=json) — see
docs/METHODOLOGY.md for the harvesting query. This module deliberately works on
a CSV so you can hand-curate or swap the source.

Run:
    python -m src.analysis.framing
"""
from __future__ import annotations

import re
import sys

import pandas as pd

from src.common import PROCESSED, RAW

PASSIVE_DEATH = re.compile(r"\b(killed|dead|die[sd]?|slain|perish)\b", re.I)
# An active actor immediately before a kill verb, e.g. "Israel kills", "Hamas fired".
ACTIVE_AGENT = re.compile(
    r"\b(israel|idf|israeli\s+\w+|hamas|militants?|gunmen|forces)\b\s+\w*\s*"
    r"(kill|fire|strike|launch|hit|bomb)", re.I)


def is_death_headline(title: str) -> bool:
    return bool(PASSIVE_DEATH.search(title or ""))


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

    print("\nGap = (agentless share when victims are Palestinian) - "
          "(when victims are Israeli). A large positive gap means an outlet "
          "strips the agent more often when Palestinians die.")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    by.to_csv(PROCESSED / "framing.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
