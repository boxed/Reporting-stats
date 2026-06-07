# Network & execution modes

The pipeline has two halves with very different network needs.

## 1. Data ingestion — needs an allowlist

`src/ingest/acled.py`, `src/ingest/gdelt.py`, and `src/ingest/headlines.py` make
outbound calls to external data hosts. On Claude Code on the web the default
**Trusted** network level blocks these (you'll see `Host not in allowlist` or
HTTP 403).

To enable them, edit the environment (cloud icon → edit environment → **Network
access**), choose **Custom**, keep *"Also include default list of common package
managers"* checked, and add:

```
api.gdeltproject.org
api.acleddata.com
*.acleddata.com
data.humdata.org
```

Or choose **Full** for an ad-hoc research run. The change applies to **new**
sessions. Docs: https://code.claude.com/docs/en/claude-code-on-the-web#network-access

> Caveat: allowlisting lifts the *sandbox* block, but some sites also block
> datacenter IPs / non-browser user-agents at their end (observed: BBC blocks the
> crawler; GDELT 403s the proxy fetcher). GDELT's open DOC API generally accepts a
> normal client; ACLED's authenticated API is the reliable path (needs an ACLED key).

Running locally (your laptop) sidesteps all of this — there's no allowlist there.

## 2. Framing judgment — two ways, neither needs an allowlist change

**a) SDK judge — `src/analysis/framing_llm.py`.** Calls `api.anthropic.com`,
which is **already in the Trusted defaults**, so no network change is needed —
just set `ANTHROPIC_API_KEY` in the environment's env vars. This is the
reproducible, version-controlled path; run it over the full headline harvest.

**b) In-session subagent.** Inside a Claude Code session, the same classification
can be done by dispatching headlines to a subagent — no API key, no external
network, works even under **Trusted**. Best for exploring/iterating now and for
validating the judge before committing to a run. Labels live in the session, not
a durable artifact, so it complements (b) rather than replacing the script.

| Step | Trusted (default) | What it needs |
|---|---|---|
| ACLED / GDELT ingestion | ❌ blocked | Custom allowlist (above) + ACLED key |
| `framing_llm.py` judge | ✅ works | `ANTHROPIC_API_KEY` env var |
| In-session subagent judge | ✅ works | nothing |
