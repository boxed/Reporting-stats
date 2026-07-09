# Red Alert weekly series — results snapshot

Produced by `python -m src.ingest.redalert` from the Home Front Command (Pikud
HaOref) siren feed, via the community mirror
[`dleshem/israel-alerts-data`](https://github.com/dleshem/israel-alerts-data)
(reachable over `raw.githubusercontent.com` even under the Trusted network level).
Snapshot pulled **2026-07-09**; the mirror updates continuously, so re-running
will extend the series. The `data/processed/redalert_weekly.csv` output is
git-ignored (reproducible), so this table preserves the findings.

**Interactive chart:** https://claude.ai/code/artifact/f854b48c-6c97-4c51-b786-118c4a7816e9

## Scope
- Category **1** only ("ירי רקטות וטילים" — rocket & missile fire); UAV (cat 2),
  drills, early-warnings and all-clears excluded.
- **165,293** siren activations → **12,594** distinct alert-minutes, **624** weeks,
  2014-07-21 → 2026-06-29.

## Two measures (why both)
One incoming round sirens every threatened locality in the same minute, so raw
activations **overcount attacks**. `distinct_alert_minutes` (unique alert minutes)
is the honest "how often / barrages" proxy; `alerts` is the "how wide / reach"
measure. They diverge sharply: May 2021 (Gaza) had the most *barrages* (736) but
~5,600 activations; early-2026 ballistic weeks had fewer barrages yet 13,000–22,000
activations (nationwide simultaneous sirens).

## By year
| Year | Barrages (distinct-min) | Activations (raw) | Active weeks | Peak week (barrages) |
|---|--:|--:|--:|--:|
| 2014 | 998 | 1,897 | 14 | 390 |
| 2015 | 30 | 46 | 17 | 5 |
| 2016 | 29 | 246 | 19 | 6 |
| 2017 | 65 | 160 | 26 | 12 |
| 2018 | 475 | 1,207 | 27 | 125 |
| 2019 | 576 | 1,917 | 30 | 248 |
| 2020 | 88 | 272 | 27 | 29 |
| 2021 | 1,119 | 7,188 | 15 | 736 |
| 2022 | 274 | 815 | 9 | 259 |
| 2023 | 2,380 | 11,031 | 24 | 494 |
| 2024 | 3,608 | 21,204 | 53 | 291 |
| 2025 | 336 | 25,398 | 41 | 71 |
| 2026 (partial) | 2,616 | 93,912 | 18 | 398 |

## Caveats
- **Alerts ≠ rockets.** A siren marks a threat to an area, not a confirmed impact;
  open-ground rockets may raise no public alert.
- **Coverage grows over time** — digital records start 2014-07 and system density
  increased; earlier years undercount relative to later ones.
- **Not Gaza-only** from late 2023 — includes Hezbollah, Houthi and Iranian fire.
- The minute-dedup can merge a rolling multi-minute salvo or split one; it is a
  proxy, not a barrage ground truth.
