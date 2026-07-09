"""Red Alert (Tzeva Adom / Pikud HaOref) siren archive -> weekly incoming-fire counts.

This is the most *granular* freely-available signal of fire toward Israel: every
incoming-threat siren the Home Front Command issues, timestamped and geolocated.
It is automated civil-defense data, not a party's political tally — a useful,
less one-sided complement to the IDF/ISA counts in the seed baselines.

Why not "Iron Dome interceptions"? There is **no public per-interception
dataset.** The IDF publishes only aggregate intercept *rates* per operation
(~75% 2012, ~80% 2014, ~90% 2021) and has declined to publish interception
counts during the 2023– war. Alerts are the granular proxy that actually exists.

⚠️ What an alert is (and isn't):
- One barrage triggers a siren in every threatened locality, so **raw alert
  count overcounts attacks**. We therefore also emit a minute-deduplicated count
  (distinct alert minutes) as a rough "distinct barrage" proxy.
- The category also covers hostile-aircraft/UAV intrusions; filter with
  `redalert.rocket_categories` in config.yaml.
- Rockets aimed at open ground may not trigger a public alert; digital coverage
  is dense only from ~2014 on (and far denser from 2021/2023).

Network: the source host (tzevaadom.co.il) is blocked under Claude-Code-on-the-web
"Trusted"; run locally, or allowlist it (see docs/NETWORK.md). The parser is
tolerant of schema drift and prints a sample record so you can adjust the
`redalert.*` field names in config.yaml on first run.

Run:
    python -m src.ingest.redalert                 # full archive
    python -m src.ingest.redalert --start 2021-01-01 --end 2024-01-01
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd
import requests

from src.common import PROCESSED, RAW, load_config


def _coerce_datetime(series: pd.Series) -> pd.Series:
    """Alerts store the timestamp as epoch seconds or an ISO string; handle both."""
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().mean() > 0.5:
        # Epoch — seconds if ~1e9, milliseconds if ~1e12.
        unit = "ms" if numeric.dropna().median() > 1e12 else "s"
        return pd.to_datetime(numeric, unit=unit, errors="coerce")
    return pd.to_datetime(series, errors="coerce", utc=True).dt.tz_localize(None)


def _extract_records(payload) -> list[dict]:
    """Find the list of alert records inside whatever the endpoint returned."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("alerts", "data", "items", "results"):
            if isinstance(payload.get(key), list):
                return payload[key]
        # Daily-keyed object: {"2023-10-07": [...], ...} -> flatten.
        flattened: list[dict] = []
        for val in payload.values():
            if isinstance(val, list):
                flattened.extend(v for v in val if isinstance(v, dict))
        if flattened:
            return flattened
    return []


def _keep_category(value: str, wanted: list[str]) -> bool:
    if not wanted:
        return True
    v = str(value).strip().lower()
    for w in wanted:
        w = str(w).strip().lower()
        if w.isdigit():           # numeric category code -> exact match
            if v == w:
                return True
        elif w in v:              # text label -> substring match
            return True
    return False


def fetch(cfg: dict) -> pd.DataFrame:
    rc = cfg.get("redalert", {})
    url = rc.get("source_url", "https://www.tzevaadom.co.il/static/historical/all.json")
    resp = requests.get(url, timeout=120, headers={"User-Agent": "reporting-stats/1.0"})
    resp.raise_for_status()
    records = _extract_records(resp.json())
    if not records:
        raise ValueError("Could not locate alert records in the payload.")
    print(f"Fetched {len(records):,} raw alert records.")
    print(f"Sample record (adjust redalert.* field names if needed):\n  {records[0]}")

    df = pd.DataFrame(records)
    date_f = rc.get("date_field", "date")
    cat_f = rc.get("category_field", "category")
    if date_f not in df.columns:
        raise KeyError(f"date_field '{date_f}' not in record keys {list(df.columns)}")

    df["ts"] = _coerce_datetime(df[date_f])
    df = df.dropna(subset=["ts"])
    if cat_f in df.columns:
        df = df[df[cat_f].apply(lambda v: _keep_category(v, rc.get("rocket_categories", [])))]
    else:
        print(f"  note: category_field '{cat_f}' absent — keeping all threat types.",
              file=sys.stderr)
    return df


def to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.set_index("ts").sort_index()
    raw = idx.resample("W-MON", label="left", closed="left").size().rename("alerts")
    # Minute-dedup across localities ≈ distinct barrages.
    minute = idx.index.floor("min")
    distinct = (
        pd.Series(minute, index=idx.index)
        .drop_duplicates()
        .to_frame("m")
        .set_index("m")
        .resample("W-MON", label="left", closed="left")
        .size()
        .rename("distinct_alert_minutes")
    )
    out = pd.concat([raw, distinct], axis=1).fillna(0).astype(int)
    out.index.name = "week_start"
    return out.reset_index()


def main() -> int:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=None, help="YYYY-MM-DD (optional filter)")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD (optional filter)")
    args = ap.parse_args()

    try:
        df = fetch(cfg)
    except (requests.RequestException, ValueError, KeyError) as exc:
        print(f"Red Alert fetch failed: {exc}", file=sys.stderr)
        print("Host is blocked under 'Trusted'; run locally or allowlist "
              "tzevaadom.co.il (see docs/NETWORK.md).", file=sys.stderr)
        return 1

    if args.start:
        df = df[df["ts"] >= pd.Timestamp(args.start)]
    if args.end:
        df = df[df["ts"] < pd.Timestamp(args.end)]

    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW / "redalert_alerts.csv", index=False)

    weekly = to_weekly(df)
    out = PROCESSED / "redalert_weekly.csv"
    weekly.to_csv(out, index=False)
    print(f"\nWrote {len(weekly)} weeks -> {out} "
          f"(span {weekly['week_start'].min().date()} → {weekly['week_start'].max().date()})")
    print(weekly.tail(10).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
