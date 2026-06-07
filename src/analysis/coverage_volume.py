"""Coverage-volume asymmetry: articles per event and per fatality, by side.

Method
------
For each ACLED event we count outlet articles published within
`coverage.window_days` of the event date (GDELT daily volume as a proxy for
"attention around that date"). We then aggregate by side and compute:

    articles_per_event    = total articles / number of events
    articles_per_fatality = total articles / total fatalities

An *asymmetry ratio* compares the two sides. A ratio far from 1.0 is the signal
to investigate — but note the GDELT volume here is date-level, not event-matched
at the article level, so treat this as a screening metric, not a verdict. The
selection analysis does the stricter per-event match.

Run:
    python -m src.analysis.coverage_volume
"""
from __future__ import annotations

import sys

import pandas as pd

from src.common import PROCESSED, RAW, load_config


def main() -> int:
    cfg = load_config()
    ev_path, cov_path = RAW / "acled_events.csv", RAW / "gdelt_coverage.csv"
    if not ev_path.exists() or not cov_path.exists():
        print("Need data/raw/acled_events.csv and gdelt_coverage.csv first "
              "(run src.ingest.acled and src.ingest.gdelt).", file=sys.stderr)
        return 2

    events = pd.read_csv(ev_path)
    cov = pd.read_csv(cov_path)
    cov["date"] = pd.to_datetime(cov["date"], format="%Y%m%d", errors="coerce")
    events["event_date"] = pd.to_datetime(events["event_date"], errors="coerce")
    window = pd.Timedelta(days=cfg["coverage"]["window_days"])

    # Total daily article volume across all outlets (sum the tiers).
    daily = cov.groupby("date")["articles"].sum().sort_index()

    def articles_near(d: pd.Timestamp) -> float:
        if pd.isna(d):
            return 0.0
        mask = (daily.index >= d) & (daily.index <= d + window)
        return float(daily[mask].sum())

    events["coverage_proxy"] = events["event_date"].apply(articles_near)

    summary = events.groupby("side").agg(
        events=("event_date", "count"),
        fatalities=("fatalities", "sum"),
        coverage=("coverage_proxy", "sum"),
    )
    summary["articles_per_event"] = summary["coverage"] / summary["events"]
    summary["articles_per_fatality"] = summary["coverage"] / summary["fatalities"].replace(0, pd.NA)

    print(summary)
    if {"toward_israel", "toward_palestine"}.issubset(summary.index):
        ti, tp = summary.loc["toward_israel"], summary.loc["toward_palestine"]
        print("\nAsymmetry ratios (toward_israel : toward_palestine)")
        print(f"  per event    : {ti.articles_per_event / tp.articles_per_event:.2f}")
        if pd.notna(ti.articles_per_fatality) and pd.notna(tp.articles_per_fatality):
            print(f"  per fatality : {ti.articles_per_fatality / tp.articles_per_fatality:.2f}")
        print("\nA ratio >1 means events toward Israel drew more coverage per "
              "event/fatality; <1 the reverse. Investigate, don't conclude.")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    summary.to_csv(PROCESSED / "coverage_volume.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
