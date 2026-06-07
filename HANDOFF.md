# Handoff — Israel–Palestine reporting-asymmetry study

Read this first when resuming in a new (networked) environment. It captures
where the project stands, what's blocked, and the exact steps to run the real
pipeline once you have network access.

Origin chat session: https://claude.ai/code/session_014pQeRugA8UZn2rnBaAmwgY

## Where we are

A reproducible pipeline to **measure** (not assume) whether Israel–Palestine
conflict coverage is asymmetric, on three dimensions — coverage volume,
framing/language, selection/omission — against a both-sides ground-truth event
set. Scaffold, ingesters, analyses, an LLM-judge framing module, a sourced seed
baseline, and docs are all committed.

- **Branch:** `claude/israel-palestine-reporting-bias-8tmSW` (push here; never elsewhere without permission)
- **Everything is committed and pushed.** Nothing important lives only in the chat.
- Read `README.md` for the design and `docs/METHODOLOGY.md` for assumptions/caveats.

## What's blocked here, and why

This session runs under the default **Trusted** network level, which allowlists
only package registries + GitHub + cloud SDKs. So:

| Step | Status here | Needs |
|---|---|---|
| ACLED / GDELT ingestion | ❌ blocked (403 / not in allowlist) | Custom allowlist + ACLED key |
| `framing_llm.py` (SDK judge) | ✅ works under Trusted | `ANTHROPIC_API_KEY` env var |
| In-session subagent judge | ✅ works, no key/network | nothing |

## To run the real pipeline in the new environment

### 1. Enable network access (one-time, on the environment)
Cloud icon → edit environment → **Network access** → **Custom**, keep *"Also
include default list"* checked, add (see `docs/NETWORK.md`):
```
api.gdeltproject.org
api.acleddata.com
*.acleddata.com
data.humdata.org
```
(Or **Full** for an ad-hoc run.) Applies to **new** sessions — start a fresh one
after changing it. Running on a laptop avoids the allowlist entirely.

### 2. Set secrets as environment variables (env config, not committed)
- `ACLED_API_KEY` + `ACLED_EMAIL` — register free at https://acleddata.com/register/.
  ⚠️ ACLED moved to OAuth2 in 2024; if the classic key/email doesn't authenticate,
  set `ACLED_OAUTH_TOKEN` instead (the ingester sends it as a Bearer token). The
  auth block to adjust is `_request()` in `src/ingest/acled.py`.
- `ANTHROPIC_API_KEY` — for the SDK framing judge (https://console.anthropic.com/).

### 3. Run, in order
```bash
pip install -r requirements.txt

python -m src.ingest.acled --start 2023-10-01 --end 2024-06-01   # both-sides events
python -m src.baseline.rocket_baseline                            # rocket→Israel + outcomes
python -m src.ingest.gdelt --start 2023-10-01 --end 2024-06-01    # per-outlet coverage volume
python -m src.ingest.headlines --start 2023-10-01 --end 2024-06-01  # headlines for framing

python -m src.analysis.coverage_volume
python -m src.analysis.framing        # regex baseline
python -m src.analysis.framing_llm    # LLM judge (Sonnet 4.6; --model claude-haiku-4-5 to go cheaper)
python -m src.analysis.selection
```
Outputs land in `data/processed/`. The most revealing first cut is usually
`selection.py` (coverage rate by casualty band per side).

### Likely friction
- **Site-side bot blocks:** allowlisting lifts the *sandbox* block, but BBC blocks
  Anthropic's crawler and GDELT 403'd the proxy fetcher. GDELT's DOC API generally
  accepts a normal `curl`/requests client, so the sandbox's own calls will *likely*
  work once allowlisted — verify with a small `--limit`/short `timespan` first.
- **ACLED auth** is the most probable thing to need a tweak (OAuth, see above).
- **GDELT `domainis:`** domain spellings for each outlet are in `config.yaml`.

## Two ways to judge framing (decided: keep both)

- **`src/analysis/framing_llm.py`** — Anthropic SDK, Pydantic structured outputs,
  batched. The reproducible artifact; run it over the full harvest. Default model
  Sonnet 4.6 (`judge.model` in `config.yaml`), Haiku 4.5 to go cheaper.
- **In-session subagent** — dispatch headlines to a subagent inside a Claude Code
  session; no key, no external network. Great for exploring/iterating; labels live
  in the session, not a durable file. Use it to spot-check before a big SDK run.

Both resolve the subject/object problem the regex (`framing.py`) cannot
(e.g. "Israel kills 10" = named actor vs "10 Israelis killed" = agentless victim).

## Illustrative result so far (so it's not lost)

A Haiku subagent judged 14 sample headlines (n is tiny, **synthetic** — not real
data) and the agentless-framing gap came out **bidirectional** across outlets,
which is the point of a falsifiable measure:

| Outlet | Pal-victim agentless | Isr-victim agentless | Gap (Pal − Isr) |
|---|---|---|---|
| Reuters | 0.67 | 0.00 | +0.67 |
| BBC | 0.50 | 0.50 | 0.00 |
| Times of Israel | 0.00 | 0.00 | 0.00 |
| Al Jazeera | 0.00 | 1.00 | −1.00 |

## Open next steps (pick up here)

1. Run the **real** ACLED + GDELT pull (needs steps 1–3 above), then the analyses.
2. Optional worked-example fixture: judge ~100–150 representative headlines
   in-session and commit labels + gaps as an offline golden test for `framing_llm.py`.
3. Consider a spaCy fallback in `framing.py`, or retire it in favor of `framing_llm.py`.
4. Stricter coverage matching: harvest GDELT `artlist` and match articles to events
   by location+keyword, replacing the date-proxy in `coverage_volume.py`/`selection.py`.

## Caveats to keep visible
The seed baseline (`data/seed/`) leans on IDF/Israeli figures and is superseded by
ACLED. GDELT skews English (under-counts Arabic/Hebrew). Headline-only framing.
Don't frame the project as "prove bias" — it's built to measure asymmetry in
either direction. Full list in `docs/METHODOLOGY.md`.
