from __future__ import annotations

import itertools
import random

import numpy as np

from .match_model import simulate_match
from .models import FixedMatchResult, Team, TeamStanding


FixedResults = dict[frozenset[str], FixedMatchResult]


def simulate_group(
    teams: list[Team],
    rng: np.random.Generator,
    tie_rng: random.Random,
    fixed_results: FixedResults | None = None,
) -> tuple[list[TeamStanding], list[Team], TeamStanding]:
    standings = {team.name: TeamStanding(team=team) for team in teams}

    for team_a, team_b in itertools.combinations(teams, 2):
        fixed_score = fixed_score_for_match(team_a, team_b, fixed_results)
        if fixed_score is None:
            result = simulate_match(team_a, team_b, rng, allow_draw=True)
            goals_a, goals_b = result.goals_a, result.goals_b
        else:
            goals_a, goals_b = fixed_score
        standing_a = standings[team_a.name]
        standing_b = standings[team_b.name]
        _apply_result(standing_a, standing_b, goals_a, goals_b)

    ranked = rank_standings(list(standings.values()), tie_rng)
    return ranked, [ranked[0].team, ranked[1].team], ranked[2]


def rank_standings(standings: list[TeamStanding], tie_rng: random.Random) -> list[TeamStanding]:
    random_fallback = {standing.team.name: tie_rng.random() for standing in standings}
    return sorted(
        standings,
        key=lambda standing: (
            standing.points,
            standing.goal_difference,
            standing.goals_for,
            random_fallback[standing.team.name],
        ),
        reverse=True,
    )


def rank_third_place_teams(
    third_place_standings: list[TeamStanding],
    tie_rng: random.Random,
) -> list[TeamStanding]:
    random_fallback = {standing.team.name: tie_rng.random() for standing in third_place_standings}
    return sorted(
        third_place_standings,
        key=lambda standing: (
            standing.points,
            standing.goal_difference,
            standing.goals_for,
            random_fallback[standing.team.name],
        ),
        reverse=True,
    )


def simulate_group_stage(
    groups: dict[str, list[Team]],
    rng: np.random.Generator,
    tie_rng: random.Random,
    fixed_results: FixedResults | None = None,
) -> tuple[list[Team], list[TeamStanding]]:
    qualified: list[Team] = []
    third_place_standings: list[TeamStanding] = []

    for group_name in sorted(groups):
        _ranked, top_two, third_place = simulate_group(groups[group_name], rng, tie_rng, fixed_results)
        qualified.extend(top_two)
        third_place_standings.append(third_place)

    best_thirds = rank_third_place_teams(third_place_standings, tie_rng)[:8]
    qualified.extend(standing.team for standing in best_thirds)
    return qualified, best_thirds


def current_group_standings(
    groups: dict[str, list[Team]],
    fixed_results: FixedResults,
    tie_rng: random.Random,
) -> dict[str, list[TeamStanding]]:
    standings_by_group: dict[str, list[TeamStanding]] = {}
    for group_name in sorted(groups):
        standings = {team.name: TeamStanding(team=team) for team in groups[group_name]}
        for team_a, team_b in itertools.combinations(groups[group_name], 2):
            fixed_score = fixed_score_for_match(team_a, team_b, fixed_results)
            if fixed_score is None:
                continue
            _apply_result(standings[team_a.name], standings[team_b.name], fixed_score[0], fixed_score[1])
        standings_by_group[group_name] = rank_standings(list(standings.values()), tie_rng)
    return standings_by_group


def fixed_score_for_match(
    team_a: Team,
    team_b: Team,
    fixed_results: FixedResults | None,
) -> tuple[int, int] | None:
    if not fixed_results:
        return None
    fixed = fixed_results.get(frozenset((team_a.name, team_b.name)))
    if fixed is None:
        return None
    if fixed.team_a == team_a.name and fixed.team_b == team_b.name:
        return fixed.goals_a, fixed.goals_b
    if fixed.team_a == team_b.name and fixed.team_b == team_a.name:
        return fixed.goals_b, fixed.goals_a
    raise ValueError(f"Fixed result teams do not match requested match: {team_a.name} vs {team_b.name}")


def _apply_result(standing_a: TeamStanding, standing_b: TeamStanding, goals_a: int, goals_b: int) -> None:
    standing_a.played += 1
    standing_b.played += 1
    standing_a.goals_for += goals_a
    standing_a.goals_against += goals_b
    standing_b.goals_for += goals_b
    standing_b.goals_against += goals_a

    if goals_a > goals_b:
        standing_a.wins += 1
        standing_b.losses += 1
        standing_a.points += 3
    elif goals_b > goals_a:
        standing_b.wins += 1
        standing_a.losses += 1
        standing_b.points += 3
    else:
        standing_a.draws += 1
        standing_b.draws += 1
        standing_a.points += 1
        standing_b.points += 1
