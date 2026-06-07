"""Selection / omission analysis: which real events get covered at all, by side.

For each ACLED event we check whether *any* article appeared in the coverage
window. We then compare coverage rates across sides, and — most tellingly —
across casualty bands. If low-casualty events toward Israel are covered while
equally-low-casualty events toward Palestine are not (or vice versa), that is a
selection effect that volume metrics alone would miss.

Uses GDELT daily volume as the coverage proxy (an event "is covered" if the
daily conflict-article count in its window exceeds a threshold). For a stricter
test, replace `covered()` with a per-event keyword/location match against an
artlist harvest.

Run:
    python -m src.analysis.selection
"""
from __future__ import annotations

import sys

import pandas as pd

from src.common import PROCESSED, RAW, load_config

# Daily article count above which we treat an event's window as "covered".
COVERAGE_THRESHOLD = 1
CASUALTY_BANDS = [(-1, 0), (0, 1), (1, 5), (5, 20), (20, 10**9)]
BAND_LABELS = ["0", "1", "2-5", "6-20", "21+"]


def main() -> int:
    cfg = load_config()
    ev_path, cov_path = RAW / "acled_events.csv", RAW / "gdelt_coverage.csv"
    if not ev_path.exists() or not cov_path.exists():
        print("Need acled_events.csv and gdelt_coverage.csv first.", file=sys.stderr)
        return 2

    events = pd.read_csv(ev_path)
    cov = pd.read_csv(cov_path)
    cov["date"] = pd.to_datetime(cov["date"], format="%Y%m%d", errors="coerce")
    events["event_date"] = pd.to_datetime(events["event_date"], errors="coerce")
    daily = cov.groupby("date")["articles"].sum().sort_index()
    window = pd.Timedelta(days=cfg["coverage"]["window_days"])

    def covered(d: pd.Timestamp) -> bool:
        if pd.isna(d):
            return False
        mask = (daily.index >= d) & (daily.index <= d + window)
        return float(daily[mask].sum()) > COVERAGE_THRESHOLD

    events["covered"] = events["event_date"].apply(covered)
    events["band"] = pd.cut(events["fatalities"], bins=[b[0] for b in CASUALTY_BANDS] + [10**9],
                            labels=BAND_LABELS, include_lowest=True, right=True)

    rate = events.groupby(["side", "band"], observed=True)["covered"].agg(["mean", "count"])
    rate = rate.rename(columns={"mean": "coverage_rate", "count": "events"})
    print(rate)
    print("\nCompare coverage_rate across sides within the same casualty band. "
          "Equal newsworthiness should yield equal coverage rates; a gap is the "
          "omission signal.")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    rate.to_csv(PROCESSED / "selection.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
