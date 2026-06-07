"""Pull both-sides conflict events from ACLED into data/raw/acled_events.csv.

ACLED is the ground-truth layer. We pull BOTH directions of fire (Palestinian
projectiles toward Israel, and Israeli strikes toward Gaza/West Bank) so the two
are directly comparable — that comparability is what makes a bias claim valid.

Auth note: ACLED migrated to OAuth2 in 2024. This module supports either the
classic key+email query params or a Bearer OAuth token (ACLED_OAUTH_TOKEN). If
ACLED has changed again, only `_request` below should need editing.

Run:
    python -m src.ingest.acled --start 2023-10-01 --end 2024-06-01
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import pandas as pd
import requests

from src.common import RAW, classify_side, load_config

ACLED_READ_URL = "https://api.acleddata.com/acled/read"


def _request(params: dict) -> dict:
    """One paginated ACLED request, with whichever auth is configured."""
    headers = {}
    token = os.getenv("ACLED_OAUTH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        params = {**params, "key": os.getenv("ACLED_API_KEY", ""),
                  "email": os.getenv("ACLED_EMAIL", "")}
    resp = requests.get(ACLED_READ_URL, params=params, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()


def fetch(start: str, end: str, cfg: dict) -> pd.DataFrame:
    rows: list[dict] = []
    for country in cfg["acled"]["countries"]:
        page = 1
        while True:
            params = {
                "country": country,
                "event_date": f"{start}|{end}",
                "event_date_where": "BETWEEN",
                "limit": 1000,
                "page": page,
            }
            data = _request(params)
            batch = data.get("data", [])
            if not batch:
                break
            rows.extend(batch)
            print(f"  {country}: page {page} -> {len(batch)} events")
            page += 1
            time.sleep(0.5)  # be polite to the API
    return pd.DataFrame(rows)


def enrich(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["side"] = df.apply(
        lambda r: classify_side(r.get("actor1", ""), r.get("country", ""), cfg),
        axis=1,
    )
    df["fatalities"] = pd.to_numeric(df.get("fatalities"), errors="coerce").fillna(0)
    kws = cfg["acled"]["rocket_keywords"]
    notes = df.get("notes", pd.Series([""] * len(df))).fillna("")
    sub = df.get("sub_event_type", pd.Series([""] * len(df))).fillna("")
    df["is_projectile"] = (
        notes.str.contains("|".join(kws), case=False, regex=True)
        | sub.str.contains("Shelling|missile|artillery", case=False, regex=True)
    )
    return df


def main() -> int:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=cfg["window"]["start"])
    ap.add_argument("--end", default=cfg["window"]["end"])
    args = ap.parse_args()

    if not (os.getenv("ACLED_OAUTH_TOKEN") or os.getenv("ACLED_API_KEY")):
        print("No ACLED credentials in .env — see .env.example.", file=sys.stderr)
        return 2

    print(f"Fetching ACLED events {args.start}..{args.end}")
    df = enrich(fetch(args.start, args.end, cfg), cfg)
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / "acled_events.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {len(df)} events -> {out}")
    if not df.empty:
        print(df.groupby("side")["fatalities"].agg(["count", "sum"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
