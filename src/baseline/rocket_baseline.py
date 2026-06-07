"""Derive the rocket->Israel baseline from ACLED events.

This is the "list of rocket attacks on Israel" the project started from, built
from ground truth rather than one party's tally. Because per-rocket success is
never published, we classify each *event* into an outcome proxy:

    impact_with_casualties : event in Israel with >0 fatalities  (reached + harmed)
    impact_no_casualties   : event in Israel, 0 fatalities       (reached, no harm)
    fell_short             : notes indicate it landed in Gaza / fell short (failed)
    intercepted            : notes mention interception / Iron Dome (neutralized)
    unknown                : none of the above could be determined

If data/raw/acled_events.csv is absent, falls back to the sourced seed table so
you still get a baseline to look at.

Run:
    python -m src.baseline.rocket_baseline
"""
from __future__ import annotations

import sys

import pandas as pd

from src.common import DATA, PROCESSED, RAW, load_config

FELL_SHORT = ["fell short", "landed in gaza", "fell inside gaza", "misfire", "failed launch"]
INTERCEPTED = ["intercept", "iron dome", "shot down"]


def classify_outcome(row: pd.Series) -> str:
    notes = str(row.get("notes", "")).lower()
    if any(k in notes for k in FELL_SHORT):
        return "fell_short"
    if any(k in notes for k in INTERCEPTED):
        return "intercepted"
    if row.get("country") == "Israel":
        return "impact_with_casualties" if row.get("fatalities", 0) > 0 else "impact_no_casualties"
    return "unknown"


def from_acled(cfg: dict) -> pd.DataFrame | None:
    path = RAW / "acled_events.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    rockets = df[(df.get("side") == "toward_israel") & (df.get("is_projectile") == True)].copy()
    if rockets.empty:
        return rockets
    rockets["outcome"] = rockets.apply(classify_outcome, axis=1)
    cols = ["event_date", "location", "actor1", "fatalities", "outcome", "notes"]
    return rockets[[c for c in cols if c in rockets.columns]]


def main() -> int:
    cfg = load_config()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    derived = from_acled(cfg)

    if derived is not None and not derived.empty:
        out = PROCESSED / "rocket_baseline.csv"
        derived.to_csv(out, index=False)
        print(f"Derived {len(derived)} rocket->Israel events from ACLED -> {out}")
        print(derived["outcome"].value_counts())
        return 0

    print("No ACLED data found — showing sourced seed baseline instead.", file=sys.stderr)
    seed = pd.read_csv(DATA / "seed" / "rocket_episodes_seed.csv")
    print(seed.to_string(index=False))
    print("\nRun `python -m src.ingest.acled` first for an event-level baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
