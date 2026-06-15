from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import FixedMatchResult


OPENFOOTBALL_2026_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
SOURCE_TEAM_ALIASES = {
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Curaçao": "Curacao",
    "Czech Republic": "Czechia",
    "DR Congo": "Congo DR",
    "USA": "United States",
}


@dataclass(frozen=True)
class MatchSchedule:
    group: str
    team_a: str
    team_b: str
    date: str
    time: str
    ground: str
    round_name: str
    actual_goals_a: int | None = None
    actual_goals_b: int | None = None

    @property
    def is_played(self) -> bool:
        return self.actual_goals_a is not None and self.actual_goals_b is not None


def normalize_team_name(team_name: str) -> str:
    return SOURCE_TEAM_ALIASES.get(team_name, team_name)


def load_match_schedule(
    url: str = OPENFOOTBALL_2026_URL,
    cache_path: Path | None = None,
    allow_network: bool = True,
) -> list[MatchSchedule]:
    if allow_network:
        try:
            with urllib.request.urlopen(url, timeout=8) as response:
                raw_data = response.read()
            if cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(raw_data)
            return parse_openfootball_schedule(json.loads(raw_data))
        except OSError:
            pass

    if cache_path and cache_path.exists():
        return parse_openfootball_schedule(json.loads(cache_path.read_text(encoding="utf-8")))
    return []


def parse_openfootball_schedule(payload: dict[str, Any]) -> list[MatchSchedule]:
    schedules: list[MatchSchedule] = []
    for match in payload.get("matches", []):
        if "group" not in match:
            continue
        score = match.get("score", {})
        full_time = score.get("ft") if isinstance(score, dict) else None
        actual_goals_a = int(full_time[0]) if full_time else None
        actual_goals_b = int(full_time[1]) if full_time else None
        schedules.append(
            MatchSchedule(
                group=str(match["group"]).replace("Group ", ""),
                team_a=normalize_team_name(str(match["team1"])),
                team_b=normalize_team_name(str(match["team2"])),
                date=str(match.get("date", "")),
                time=str(match.get("time", "")),
                ground=str(match.get("ground", "")),
                round_name=str(match.get("round", "")),
                actual_goals_a=actual_goals_a,
                actual_goals_b=actual_goals_b,
            )
        )
    return schedules


def fixed_results_from_schedules(schedules: list[MatchSchedule]) -> dict[frozenset[str], FixedMatchResult]:
    return {
        frozenset((schedule.team_a, schedule.team_b)): FixedMatchResult(
            team_a=schedule.team_a,
            team_b=schedule.team_b,
            goals_a=schedule.actual_goals_a,
            goals_b=schedule.actual_goals_b,
        )
        for schedule in schedules
        if schedule.is_played
    }
