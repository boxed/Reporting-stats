"""Build a *weekly* projectile-toward-Israel time series (last few decades).

The question this answers: "how many rockets/missiles per week were fired at
Israel?" over a multi-decade span. There are two precision levels, and this
module prefers the better one when it exists:

1. **Event-level (preferred).** If the ACLED-derived baseline
   (`data/processed/rocket_baseline.csv`, produced by `rocket_baseline.py`)
   is present, count discrete *attack events* per ISO week and sum fatalities.
   This is a genuine per-week count of attacks, the most honest answer.

2. **Episode-level fallback (usable now, no network).** Absent ACLED, fall
   back to the sourced episode seed (`data/seed/rocket_episodes_seed.csv`) and
   spread each episode's approximate projectile total **evenly** across the ISO
   weeks it spans. Overlapping episodes sum. This yields an average *weekly
   intensity during active episodes* — NOT a real week-by-week count.

⚠️ Caveat that matters: real rocket fire is **bursty** (hundreds in a day,
then quiet for months). The fallback's even-spread deliberately flattens that,
and the two cumulative seed rows (Sderot-era 2001-2008, 2018-2019) smear
thousands of projectiles across years, so their weekly rate is an artifact of
averaging, not a measured rate. Weeks with no active episode are 0 by
construction (the seed only records escalations). Prefer the ACLED path for any
published claim. See `data/seed/SOURCES.md`.

Run:
    python -m src.baseline.weekly_rate
"""
from __future__ import annotations

import sys

import pandas as pd

from src.common import DATA, PROCESSED, load_config  # noqa: F401  (cfg kept for parity)


def weekly_from_events() -> pd.DataFrame | None:
    """Per-ISO-week count of discrete attack events from the ACLED baseline."""
    path = PROCESSED / "rocket_baseline.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if df.empty or "event_date" not in df.columns:
        return None
    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    df = df.dropna(subset=["event_date"])
    fatalities = df["fatalities"] if "fatalities" in df.columns else 0
    df = df.assign(fatalities=pd.to_numeric(fatalities, errors="coerce").fillna(0))

    weekly = (
        df.set_index("event_date")
        .resample("W-MON", label="left", closed="left")
        .agg(attacks=("outcome", "size"), fatalities=("fatalities", "sum"))
        .reset_index()
        .rename(columns={"event_date": "week_start"})
    )
    weekly["source"] = "acled_events"
    return weekly


def weekly_from_seed() -> pd.DataFrame:
    """Spread each episode's projectile total evenly over the weeks it spans."""
    seed = pd.read_csv(DATA / "seed" / "rocket_episodes_seed.csv")
    seed["start_date"] = pd.to_datetime(seed["start_date"])
    seed["end_date"] = pd.to_datetime(seed["end_date"])

    rows: list[dict] = []
    for _, ep in seed.iterrows():
        # ISO weeks (Monday-anchored) touched by this episode, inclusive.
        weeks = pd.date_range(
            ep["start_date"].normalize() - pd.Timedelta(days=ep["start_date"].weekday()),
            ep["end_date"],
            freq="W-MON",
        )
        if len(weeks) == 0:
            weeks = pd.DatetimeIndex([ep["start_date"].normalize()])
        total = float(ep.get("projectiles_fired_approx") or 0)
        deaths = float(ep.get("israeli_deaths_from_projectiles_approx") or 0)
        per_week = total / len(weeks)
        deaths_per_week = deaths / len(weeks)
        for wk in weeks:
            rows.append(
                {
                    "week_start": wk,
                    "projectiles_per_week": per_week,
                    "israeli_deaths_per_week": deaths_per_week,
                    "episode": ep["name"],
                    "confidence": ep["confidence"],
                }
            )

    df = pd.DataFrame(rows)
    # Sum overlapping episodes onto a single continuous weekly grid; gaps -> 0.
    grid = pd.date_range(df["week_start"].min(), df["week_start"].max(), freq="W-MON")
    agg = (
        df.groupby("week_start")
        .agg(
            projectiles_per_week=("projectiles_per_week", "sum"),
            israeli_deaths_per_week=("israeli_deaths_per_week", "sum"),
            episodes=("episode", lambda s: "; ".join(sorted(set(s)))),
        )
        .reindex(grid)
        .rename_axis("week_start")
        .reset_index()
    )
    # Gaps between escalations -> 0 fire, no episode label.
    agg["projectiles_per_week"] = agg["projectiles_per_week"].fillna(0.0)
    agg["israeli_deaths_per_week"] = agg["israeli_deaths_per_week"].fillna(0.0)
    agg["episodes"] = agg["episodes"].fillna("")
    agg["source"] = "seed_episode_spread"
    return agg


def main() -> int:
    load_config()
    PROCESSED.mkdir(parents=True, exist_ok=True)

    weekly = weekly_from_events()
    if weekly is not None and not weekly.empty:
        out = PROCESSED / "weekly_rocket_rate.csv"
        weekly.to_csv(out, index=False)
        print(f"Weekly attack counts from ACLED events -> {out} ({len(weekly)} weeks)")
        print(weekly.tail(12).to_string(index=False))
        return 0

    print(
        "No ACLED baseline found — building the weekly series from the episode "
        "seed (even-spread approximation; see module docstring).",
        file=sys.stderr,
    )
    weekly = weekly_from_seed()
    out = PROCESSED / "weekly_rocket_rate.csv"
    weekly.to_csv(out, index=False)
    print(f"Weekly projectile rate from seed (spread) -> {out} ({len(weekly)} weeks)")

    # A by-year digest is far more readable than 1,200 weekly rows.
    by_year = (
        weekly.assign(year=weekly["week_start"].dt.year)
        .groupby("year")
        .agg(
            active_weeks=("projectiles_per_week", lambda s: int((s > 0).sum())),
            avg_proj_per_active_week=(
                "projectiles_per_week",
                lambda s: round(s[s > 0].mean(), 1) if (s > 0).any() else 0.0,
            ),
            peak_week_proj=("projectiles_per_week", lambda s: round(s.max(), 1)),
            total_projectiles=("projectiles_per_week", lambda s: round(s.sum())),
        )
    )
    print("\nBy year (active weeks = weeks inside a recorded escalation):")
    print(by_year.to_string())
    print(
        "\n⚠️ Even-spread approximation: real fire is bursty. Cumulative seed rows "
        "(2001-08, 2018-19) smear totals across years. Wire up ACLED "
        "(`python -m src.ingest.acled`) for true per-week event counts."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
