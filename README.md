# Reporting-stats — measuring asymmetry in Israel–Palestine conflict reporting

This project measures whether news coverage of the Israel–Palestine conflict is
**asymmetric** relative to a ground-truth record of events, and if so, in which
direction and on which dimension. It is deliberately built to be **falsifiable**:
it can return "bias toward Israel", "bias toward Palestine", or "no measurable
asymmetry" depending on what the data shows.

> ⚠️ **Framing note.** A study designed to *prove* bias is not credible. A study
> designed to *measure* asymmetry — with a pre-registered metric that could come
> out either way — is. Everything here is structured around the second goal.
> Read [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) before drawing conclusions.

## Why a baseline alone is not enough

A list of rocket attacks on Israel, by itself, **cannot demonstrate reporting
bias.** Bias is a *relative* measurement. If you only have events on one side you
cannot separate "coverage is skewed" from "that side had more newsworthy events."

So the baseline (rockets → Israel) is built as **one arm of a two-sided event
dataset**. The other arm (Israeli strikes/operations → Gaza & West Bank) is
pulled the same way, from the same source, so the two are comparable.

## The three things we measure

| Dimension | Question | Data needed |
|---|---|---|
| **Coverage volume** | Articles / words *per event* and *per fatality* on each side | events + per-outlet article counts |
| **Framing & language** | Active vs. passive voice; who is named as the actor; word choice (`killed` vs. `died`) | article headlines/bodies |
| **Selection / omission** | Which real events get covered *at all* vs. ignored | events + coverage match |

## Ground truth: ACLED

Events come from [ACLED](https://acleddata.com) (Armed Conflict Location & Event
Data). ACLED codes each event from a deliberate mix of pro-Israeli and
pro-Palestinian sources and documents uncertainty — the most defensible "truth"
layer available, and it covers **both directions of fire**.

A **sourced seed dataset** (`data/seed/rocket_episodes_seed.csv`) is included so
you can explore the rocket baseline immediately, before wiring up ACLED. It is
coarse (episode-level, approximate) and is **superseded** by the ACLED pull.

## Outlets analyzed

Configured in [`config.yaml`](config.yaml):
- **Western legacy:** BBC, New York Times, Reuters, AP
- **Regional anchors:** Al Jazeera, Times of Israel, Haaretz
- **Broad aggregate:** all GDELT-indexed outlets (for volume/tone at scale)

## ⚠️ Network policy constraint

ACLED and GDELT are **not reachable** from the default **Trusted** Claude-Code-on-the-web
network level (`Host not in allowlist` / HTTP 403). Set the environment's Network
access to **Custom** and allowlist the data hosts — full instructions and the exact
domain list are in [`docs/NETWORK.md`](docs/NETWORK.md). The **framing judge needs
no network change**: the Anthropic SDK host is already allowlisted, and the
in-session subagent path needs neither a key nor network. Running locally sidesteps
the allowlist entirely.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your ACLED key + email

# 1. Pull both-sides events (needs network + ACLED creds)
python -m src.ingest.acled --start 2023-10-01 --end 2024-06-01

# 2. Build the rocket-attack baseline (success/failure outcomes)
python -m src.baseline.rocket_baseline

# 2b. Build the weekly projectiles-toward-Israel time series (2001–2024)
#     Uses ACLED events if present; else spreads the seed episodes (approx).
python -m src.baseline.weekly_rate

# 2c. Print the year-by-year compiled counts (2001–2024), no network needed.
python -m src.baseline.annual_counts

# 2d. Pull the Red Alert (Tzeva Adom) siren archive -> weekly incoming-fire
#     counts. Granular, timestamped, no key. Needs network (or run locally).
python -m src.ingest.redalert

# 3. Pull per-outlet coverage volume (needs network; GDELT, no key)
python -m src.ingest.gdelt --start 2023-10-01 --end 2024-06-01

# 4. Harvest real headlines for the framing analysis (needs network; GDELT)
python -m src.ingest.headlines --start 2023-10-01 --end 2024-06-01

# 5. Run the three analyses
python -m src.analysis.coverage_volume
python -m src.analysis.framing
python -m src.analysis.selection
```

## Layout

```
config.yaml                        outlets, query terms, date windows
data/seed/rocket_episodes_seed.csv sourced, usable-now rocket baseline (episode-level)
data/seed/annual_rocket_counts_seed.csv  year-by-year counts 2001–2024 (compiled)
data/seed/SOURCES.md               provenance for every episode-seed figure
data/seed/SOURCES_annual.md        provenance + caveats for the annual counts
src/ingest/acled.py                pull both-sides events from ACLED
src/ingest/redalert.py             Red Alert (Tzeva Adom) sirens -> weekly incoming-fire counts
src/ingest/gdelt.py                per-outlet coverage volume + tone
src/ingest/headlines.py            harvest per-outlet headlines (GDELT artlist)
src/baseline/rocket_baseline.py    derive rocket→Israel events + outcomes
src/baseline/weekly_rate.py        weekly projectiles-toward-Israel series (2001–2024)
src/baseline/annual_counts.py      year-by-year compiled counts (2001–2024)
src/analysis/coverage_volume.py    articles per event / per fatality by side
src/analysis/framing.py            agent attribution & passive-voice metrics
src/analysis/selection.py          which events get zero coverage, by side
docs/METHODOLOGY.md                assumptions, threats to validity, caveats
```
