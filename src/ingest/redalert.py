"""Red Alert (Tzeva Adom / Pikud HaOref) siren archive -> weekly incoming-fire counts.

This is the most *granular* freely-available signal of fire toward Israel: every
incoming-threat siren the Home Front Command issues, timestamped and geolocated.
It is automated civil-defense data, not a party's political tally — a useful,
less one-sided complement to the IDF/ISA counts in the seed baselines.

Why not "Iron Dome interceptions"? There is **no public per-interception
dataset.** The IDF publishes only aggregate intercept *rates* per operation
(~75% 2012, ~80% 2014, ~90% 2021) and has declined to publish interception
counts during the 2023– war. Alerts are the granular proxy that actually exists.

DEFAULT SOURCE — reachable with no network change. The canonical archive lives
on tzevaadom.co.il / oref.org.il, both blocked under Claude-Code-on-the-web
"Trusted". But the community mirror `dleshem/israel-alerts-data` commits the full
Home Front Command history as a CSV, and `raw.githubusercontent.com` IS reachable
even under Trusted — so by default we pull that. Set `redalert.source_format:
json` + the tzevaadom URL to use the original instead (needs an allowlist/local run).

⚠️ What an alert is (and isn't):
- One event triggers a siren in every threatened locality, so **raw alert count
  wildly overcounts attacks** — a single ballistic missile can set off sirens in
  hundreds of towns in the same minute. We therefore emit BOTH `alerts` (raw
  siren activations = reach/intensity) and `distinct_alert_minutes` (unique
  alert minutes ≈ distinct barrages), and the latter is the honest "attacks" proxy.
- Category 1 is rocket/missile fire; category 2 is hostile-aircraft/UAV; others
  are drills, early-warnings, and "all clear". Filter via `redalert.rocket_categories`.
- Rockets aimed at open ground may not trigger a public alert; digital coverage
  begins 2014-07 and is far denser from 2021/2023 on.

Run:
    python -m src.ingest.redalert                 # full archive (2014-07 → today)
    python -m src.ingest.redalert --start 2023-10-01 --end 2024-01-01
"""
from __future__ import annotations

import argparse
import io
import sys

import pandas as pd
import requests

from src.common import PROCESSED, RAW, load_config


def _coerce_datetime(series: pd.Series) -> pd.Series:
    """Timestamps arrive as ISO strings (CSV mirror) or epoch s/ms (tzevaadom)."""
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().mean() > 0.5:
        unit = "ms" if numeric.dropna().median() > 1e12 else "s"
        return pd.to_datetime(numeric, unit=unit, errors="coerce")
    return pd.to_datetime(series, errors="coerce")


def _extract_records(payload) -> list[dict]:
    """Find the list of alert records inside a JSON payload (tzevaadom path)."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("alerts", "data", "items", "results"):
            if isinstance(payload.get(key), list):
                return payload[key]
        flattened: list[dict] = []
        for val in payload.values():
            if isinstance(val, list):
                flattened.extend(v for v in val if isinstance(v, dict))
        if flattened:
            return flattened
    return []


def _keep_category(value, wanted: list[str]) -> bool:
    if not wanted:
        return True
    v = str(value).strip().lower()
    for w in wanted:
        w = str(w).strip().lower()
        if w.isdigit():
            if v == w:            # numeric code -> exact match
                return True
        elif w in v:              # text label -> substring
            return True
    return False


def fetch(cfg: dict) -> pd.DataFrame:
    rc = cfg.get("redalert", {})
    url = rc.get(
        "source_url",
        "https://raw.githubusercontent.com/dleshem/israel-alerts-data/main/israel-alerts.csv",
    )
    fmt = rc.get("source_format", "csv")
    date_f = rc.get("date_field", "alertDate")
    cat_f = rc.get("category_field", "category")

    resp = requests.get(url, timeout=180, headers={"User-Agent": "reporting-stats/1.0"})
    resp.raise_for_status()

    if fmt == "csv":
        df = pd.read_csv(io.BytesIO(resp.content))
    else:
        records = _extract_records(resp.json())
        if not records:
            raise ValueError("Could not locate alert records in the JSON payload.")
        df = pd.DataFrame(records)
    print(f"Fetched {len(df):,} raw alert rows ({fmt}). Columns: {list(df.columns)}")

    if date_f not in df.columns:
        raise KeyError(f"date_field '{date_f}' not in columns {list(df.columns)}")
    df["ts"] = _coerce_datetime(df[date_f])
    df = df.dropna(subset=["ts"])
    if cat_f in df.columns:
        before = len(df)
        df = df[df[cat_f].apply(lambda v: _keep_category(v, rc.get("rocket_categories", [])))]
        print(f"Kept {len(df):,}/{before:,} rows after category filter "
              f"{rc.get('rocket_categories', [])}.")
    else:
        print(f"  note: category_field '{cat_f}' absent — keeping all threat types.",
              file=sys.stderr)
    return df


def to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.set_index("ts").sort_index()
    raw = idx.resample("W-MON", label="left", closed="left").size().rename("alerts")
    # Minute-dedup across localities ≈ distinct barrages (the "attacks" proxy).
    minute = pd.Series(idx.index.floor("min"), index=idx.index).drop_duplicates()
    distinct = (
        minute.to_frame("m").set_index("m")
        .resample("W-MON", label="left", closed="left").size()
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
        print("Default source is raw.githubusercontent.com (reachable under Trusted). "
              "If you switched to the tzevaadom JSON, that host is blocked — run "
              "locally or allowlist it (see docs/NETWORK.md).", file=sys.stderr)
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
    print("Totals: "
          f"{int(weekly['alerts'].sum()):,} raw alerts, "
          f"{int(weekly['distinct_alert_minutes'].sum()):,} distinct alert-minutes "
          "(≈ barrages).")
    print(weekly.tail(8).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
