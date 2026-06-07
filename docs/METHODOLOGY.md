# Methodology, assumptions, and threats to validity

## Design principle: measure, don't confirm
The project is built so the result can come back as bias in *either* direction,
or none. Every metric reports an **asymmetry ratio / gap** against a both-sides
baseline rather than a one-sided count. If you find yourself only able to produce
a number for one side, the design has failed and the result is not interpretable.

## Pipeline
1. **Ground truth (`src/ingest/acled.py`)** — ACLED events for Israel and
   Palestine, both directions of fire, with `side`, `fatalities`, and a
   `is_projectile` flag. ACLED sources from a deliberate pro-Israeli/
   pro-Palestinian mix and codes uncertainty, which is why it is the truth layer
   rather than any single outlet or military.
2. **Baseline (`src/baseline/rocket_baseline.py`)** — the rocket→Israel subset,
   with a per-event outcome proxy (impact-with-casualties / impact / fell-short /
   intercepted / unknown). Per-rocket success is never published; these are the
   honest proxies available.
3. **Coverage (`src/ingest/gdelt.py`)** — per-outlet daily article volume.
4. **Analyses** — coverage volume, framing, selection (see README table).

## Key assumptions (and why they're shaky)
- **GDELT daily volume ≈ attention around an event.** It is date-level, not
  article-to-event matched, so coverage-volume is a *screening* metric. The
  selection analysis is the stricter test; for a publishable result, harvest
  GDELT `artlist` and match articles to events by location + keyword.
- **`classify_side` infers direction from actor + location.** Cross-border and
  multi-actor events (e.g. Hezbollah, Houthi, internal Palestinian violence) are
  edge cases. Audit the `side == None` rows before trusting aggregates.
- **Casualty bands assume comparable newsworthiness within a band.** A 5-fatality
  event is not always as newsworthy as another 5-fatality event (children,
  notable victims, location). Bands reduce but do not remove this.
- **Seed dataset leans on IDF/Israeli figures.** Flagged in `data/seed/SOURCES.md`;
  superseded by ACLED.

## Threats to validity
- **Source-language asymmetry.** GDELT skews English. Arabic and Hebrew coverage
  is under-counted, which can masquerade as a coverage gap. Consider GDELT's
  translingual stream or per-language stratification.
- **Paywalls.** NYT/Haaretz bodies are often inaccessible; framing analysis runs
  on headlines, which are themselves an editorial choice (defensible) but not the
  whole article.
- **Survivorship in events.** ACLED itself draws on media; events ignored by all
  media may be absent from "ground truth" too. This *understates* omission.
- **Multiple comparisons.** Three dimensions × several outlets × casualty bands =
  many tests. Pre-register the handful you care about, or correct for it.

## Reproducibility
Pin the ACLED pull date and the GDELT window; both backfill and revise. Commit
the `data/processed/*.csv` outputs alongside the window used so results are
auditable.
