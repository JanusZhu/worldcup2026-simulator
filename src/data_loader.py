from __future__ import annotations

from pathlib import Path

import pandas as pd

from .models import Team


TEAM_COLUMNS = {"team", "elo", "attack", "defense", "confederation", "is_host"}
GROUP_COLUMNS = {"group", "team"}


def _validate_columns(frame: pd.DataFrame, required: set[str], path: Path) -> None:
    missing = required - set(frame.columns)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"{path} is missing required columns: {missing_list}")


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"Cannot parse boolean value: {value!r}")


def load_teams(path: str | Path) -> dict[str, Team]:
    csv_path = Path(path)
    frame = pd.read_csv(csv_path)
    _validate_columns(frame, TEAM_COLUMNS, csv_path)

    teams: dict[str, Team] = {}
    for row in frame.itertuples(index=False):
        team = Team(
            name=str(row.team),
            elo=float(row.elo),
            attack=float(row.attack),
            defense=float(row.defense),
            confederation=str(row.confederation),
            is_host=_parse_bool(row.is_host),
        )
        if team.name in teams:
            raise ValueError(f"Duplicate team in {csv_path}: {team.name}")
        teams[team.name] = team

    if len(teams) != 48:
        raise ValueError(f"Expected 48 teams in {csv_path}, found {len(teams)}")
    return teams


def load_groups(path: str | Path, teams: dict[str, Team]) -> dict[str, list[Team]]:
    csv_path = Path(path)
    frame = pd.read_csv(csv_path)
    _validate_columns(frame, GROUP_COLUMNS, csv_path)

    groups: dict[str, list[Team]] = {}
    for row in frame.itertuples(index=False):
        team_name = str(row.team)
        if team_name not in teams:
            raise ValueError(f"Team in {csv_path} not found in teams file: {team_name}")
        groups.setdefault(str(row.group), []).append(teams[team_name])

    if len(groups) != 12:
        raise ValueError(f"Expected 12 groups in {csv_path}, found {len(groups)}")
    bad_groups = {group: len(members) for group, members in groups.items() if len(members) != 4}
    if bad_groups:
        details = ", ".join(f"{group}={size}" for group, size in sorted(bad_groups.items()))
        raise ValueError(f"Each group must have 4 teams. Invalid groups: {details}")
    return dict(sorted(groups.items()))
