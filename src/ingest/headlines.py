"""Harvest real article headlines per outlet from GDELT DOC 2.0 (artlist mode).

Produces data/raw/headlines.csv with the columns src/analysis/framing.py needs:
`outlet`, `title`, `side` — where `side` is the *victim group* the headline
concerns (israeli / palestinian / both / unclear), inferred heuristically from
place and nationality words in the title.

GDELT artlist caps each response at ~250 records, so we slice the window into
chunks (default weekly) and page through time, then de-duplicate by URL.

Run:
    python -m src.ingest.headlines --start 2023-10-01 --end 2024-06-01
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
import requests

from src.common import RAW, load_config

DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

PALESTINIAN = re.compile(
    r"\b(gaza|gazan|palestin\w*|west bank|rafah|khan younis|jabalia|jenin|nablus)\b", re.I)
ISRAELI = re.compile(
    r"\b(israel\w*|tel aviv|sderot|ashkelon|ashdod|kibbutz|jerusalem|be'eri|netivot)\b", re.I)


def victim_side(title: str) -> str:
    t = title or ""
    p, i = bool(PALESTINIAN.search(t)), bool(ISRAELI.search(t))
    if p and i:
        return "both"
    if p:
        return "palestinian"
    if i:
        return "israeli"
    return "unclear"


def _fmt(d: datetime) -> str:
    return d.strftime("%Y%m%d%H%M%S")


def _slices(start: str, end: str, days: int):
    cur = datetime.strptime(start, "%Y-%m-%d")
    stop = datetime.strptime(end, "%Y-%m-%d")
    while cur < stop:
        nxt = min(cur + timedelta(days=days), stop)
        yield cur, nxt
        cur = nxt


def fetch_outlet(query: str, domains: list[str], start: str, end: str,
                 slice_days: int) -> list[dict]:
    domain_clause = " OR ".join(f"domainis:{d}" for d in domains)
    full = f"({query}) ({domain_clause})"
    out: list[dict] = []
    for a, b in _slices(start, end, slice_days):
        params = {
            "query": full, "mode": "artlist", "format": "json",
            "maxrecords": 250, "sort": "datedesc",
            "startdatetime": _fmt(a), "enddatetime": _fmt(b),
        }
        try:
            resp = requests.get(DOC_URL, params=params, timeout=60)
            resp.raise_for_status()
            arts = resp.json().get("articles", [])
        except (requests.RequestException, ValueError) as exc:
            print(f"    slice {a:%Y-%m-%d} failed: {exc}", file=sys.stderr)
            arts = []
        out.extend(arts)
        time.sleep(1)  # GDELT rate-limits aggressively
    return out


def main() -> int:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=cfg["window"]["start"])
    ap.add_argument("--end", default=cfg["window"]["end"])
    ap.add_argument("--slice-days", type=int, default=7)
    args = ap.parse_args()

    query = cfg["coverage"]["base_query"]
    rows: list[dict] = []
    for tier, outlets in cfg["outlets"].items():
        for outlet in outlets:
            print(f"GDELT artlist: {outlet['name']} ({tier})")
            arts = fetch_outlet(query, outlet["gdelt_domains"],
                                args.start, args.end, args.slice_days)
            for art in arts:
                title = art.get("title", "")
                rows.append({
                    "outlet": outlet["name"], "tier": tier,
                    "title": title, "url": art.get("url", ""),
                    "seendate": art.get("seendate", ""),
                    "language": art.get("language", ""),
                    "side": victim_side(title),
                })

    if not rows:
        print("No headlines harvested (network policy may block GDELT here).",
              file=sys.stderr)
        return 1

    df = pd.DataFrame(rows).drop_duplicates(subset=["url"]).reset_index(drop=True)
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / "headlines.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {len(df)} unique headlines -> {out}")
    print(df.groupby(["tier", "side"]).size())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
