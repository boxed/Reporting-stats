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

ACLED and GDELT are **not reachable** from the restricted Claude-Code-on-the-web
environment this repo may have been created in (`Host not in allowlist`). Run the
ingestion steps where you have open network access — your laptop, or a web
environment created with a broader network policy. See
https://code.claude.com/docs/en/claude-code-on-the-web for network policies.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your ACLED key + email

# 1. Pull both-sides events (needs network + ACLED creds)
python -m src.ingest.acled --start 2023-10-01 --end 2024-06-01

# 2. Build the rocket-attack baseline (success/failure outcomes)
python -m src.baseline.rocket_baseline

# 3. Pull per-outlet coverage volume (needs network; GDELT, no key)
python -m src.ingest.gdelt --start 2023-10-01 --end 2024-06-01

# 4. Run the three analyses
python -m src.analysis.coverage_volume
python -m src.analysis.framing
python -m src.analysis.selection
```

## Layout

```
config.yaml                        outlets, query terms, date windows
data/seed/rocket_episodes_seed.csv sourced, usable-now rocket baseline
data/seed/SOURCES.md               provenance for every seed figure
src/ingest/acled.py                pull both-sides events from ACLED
src/ingest/gdelt.py                per-outlet coverage volume + tone
src/baseline/rocket_baseline.py    derive rocket→Israel events + outcomes
src/analysis/coverage_volume.py    articles per event / per fatality by side
src/analysis/framing.py            agent attribution & passive-voice metrics
src/analysis/selection.py          which events get zero coverage, by side
docs/METHODOLOGY.md                assumptions, threats to validity, caveats
```
