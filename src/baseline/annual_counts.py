"""Annual rockets/mortars-toward-Israel counts (2001–2024), compiled baseline.

The finest granularity that freely-available sources actually publish for "how
much fire toward Israel" is **annual** — so this is an annual table, not a fake
weekly one. It complements the two other baselines:

    rocket_episodes_seed.csv  -> operation-level, with date spans (weekly_rate.py)
    annual_rocket_counts_seed -> year-level totals, full 2001–2024 coverage (here)
    ACLED / UCDP (when wired)  -> true event-level, both-sides ground truth

⚠️ These are Israeli-sourced *launch* tallies (ISA / IDF / ITIC / JVL) with
definitions that shift between rockets-only and rockets+mortars; "launches"
are not impacts or casualties; 2024 is multi-front and left blank. See
`data/seed/SOURCES_annual.md` for the per-year provenance and caveats.

This module prints the table and writes `data/processed/annual_rocket_counts.csv`
with a derived (and clearly-labelled) naive weekly-average column. It does NOT
claim weekly precision — for that, wire up the event-level pipeline.

Run:
    python -m src.baseline.annual_counts
"""
from __future__ import annotations

import pandas as pd

from src.common import DATA, PROCESSED


def load_annual() -> pd.DataFrame:
    df = pd.read_csv(DATA / "seed" / "annual_rocket_counts_seed.csv")
    df["year"] = df["year"].astype(int)
    return df


def main() -> int:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df = load_annual()

    counted = df[df["combined_approx"].notna()].copy()
    counted["combined_approx"] = counted["combined_approx"].astype(int)
    # Naive weekly average — combined / 52. A flat smear, NOT a measured rate;
    # the by-year column is the honest unit. Labelled as such in the output.
    counted["naive_avg_per_week"] = (counted["combined_approx"] / 52).round(1)

    out = PROCESSED / "annual_rocket_counts.csv"
    counted.to_csv(out, index=False)

    span_total = int(counted["combined_approx"].sum())
    print(f"Annual rockets/mortars toward Israel -> {out}")
    print(
        counted[["year", "combined_approx", "naive_avg_per_week", "confidence", "source_tag"]]
        .to_string(index=False)
    )
    print(f"\nCumulative 2001–2023 (excl. blank 2024): ~{span_total:,} projectiles.")
    print(
        "naive_avg_per_week = combined / 52 — a flat smear for scale only. Real fire "
        "is bursty (see weekly_rate.py) and these are one-party launch tallies "
        "(see data/seed/SOURCES_annual.md). 2024 is multi-front and omitted."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
