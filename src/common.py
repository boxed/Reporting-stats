"""Shared helpers: config loading, paths, and side classification."""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"

load_dotenv(ROOT / ".env")


def load_config() -> dict:
    with open(ROOT / "config.yaml", "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def classify_side(actor1: str, country: str, cfg: dict) -> str | None:
    """Infer direction of an event from its perpetrator and location.

    Returns 'toward_israel', 'toward_palestine', or None if undetermined.
    """
    actor1 = actor1 or ""
    sides = cfg["sides"]

    def matches(patterns: list[str]) -> bool:
        return any(re.search(re.escape(p), actor1, re.IGNORECASE) for p in patterns)

    ti, tp = sides["toward_israel"], sides["toward_palestine"]
    if matches(ti["actor_patterns"]) or country in ti["location_in"]:
        # A Palestinian/allied actor, or an event located in Israel.
        if matches(ti["actor_patterns"]):
            return "toward_israel"
    if matches(tp["actor_patterns"]):
        return "toward_palestine"
    # Fall back to location when the actor is ambiguous.
    if country in ti["location_in"]:
        return "toward_israel"
    if country in tp["location_in"]:
        return "toward_palestine"
    return None
