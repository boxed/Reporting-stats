"""Per-outlet coverage volume and tone via the GDELT DOC 2.0 API (no key needed).

For each configured outlet we ask GDELT how many conflict articles it published
per day across the window. The output (data/raw/gdelt_coverage.csv) feeds the
coverage-volume and selection analyses.

GDELT DOC 2.0 caps queries at a 1-year span and ~250 artlist records, so we use
the daily volume timeline mode and page the window if needed.

Run:
    python -m src.ingest.gdelt --start 2023-10-01 --end 2024-06-01
"""
from __future__ import annotations

import argparse
import sys
import time

import pandas as pd
import requests

from src.common import RAW, load_config

DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def _fmt(d: str) -> str:
    """YYYY-MM-DD -> GDELT's YYYYMMDDHHMMSS."""
    return d.replace("-", "") + "000000"


def volume_for_domain(query: str, domains: list[str], start: str, end: str) -> pd.DataFrame:
    """Daily article volume for one outlet (its domains OR-ed together)."""
    domain_clause = " OR ".join(f"domainis:{d}" for d in domains)
    full = f"({query}) ({domain_clause})"
    params = {
        "query": full,
        "mode": "timelinevolraw",   # raw article counts per day
        "format": "json",
        "startdatetime": _fmt(start),
        "enddatetime": _fmt(end),
    }
    resp = requests.get(DOC_URL, params=params, timeout=60)
    resp.raise_for_status()
    series = resp.json().get("timeline", [])
    if not series:
        return pd.DataFrame(columns=["date", "articles"])
    points = series[0].get("data", [])
    return pd.DataFrame(
        {"date": [p["date"][:8] for p in points],
         "articles": [p.get("value", 0) for p in points]}
    )


def main() -> int:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=cfg["window"]["start"])
    ap.add_argument("--end", default=cfg["window"]["end"])
    args = ap.parse_args()

    query = cfg["coverage"]["base_query"]
    frames = []
    for tier, outlets in cfg["outlets"].items():
        for outlet in outlets:
            print(f"GDELT: {outlet['name']} ({tier})")
            try:
                df = volume_for_domain(query, outlet["gdelt_domains"], args.start, args.end)
            except requests.RequestException as exc:
                print(f"  failed: {exc}", file=sys.stderr)
                continue
            df["outlet"] = outlet["name"]
            df["tier"] = tier
            frames.append(df)
            time.sleep(1)  # GDELT rate-limits aggressively

    if not frames:
        print("No GDELT data fetched (network?).", file=sys.stderr)
        return 1
    out_df = pd.concat(frames, ignore_index=True)
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / "gdelt_coverage.csv"
    out_df.to_csv(out, index=False)
    print(f"Wrote {len(out_df)} rows -> {out}")
    print(out_df.groupby("outlet")["articles"].sum())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
