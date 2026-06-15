from __future__ import annotations

import itertools
import random

import numpy as np

from .match_model import simulate_match
from .models import Team, TeamStanding


def simulate_group(
    teams: list[Team],
    rng: np.random.Generator,
    tie_rng: random.Random,
) -> tuple[list[TeamStanding], list[Team], TeamStanding]:
    standings = {team.name: TeamStanding(team=team) for team in teams}

    for team_a, team_b in itertools.combinations(teams, 2):
        result = simulate_match(team_a, team_b, rng, allow_draw=True)
        standing_a = standings[team_a.name]
        standing_b = standings[team_b.name]
        _apply_result(standing_a, standing_b, result.goals_a, result.goals_b)

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
) -> tuple[list[Team], list[TeamStanding]]:
    qualified: list[Team] = []
    third_place_standings: list[TeamStanding] = []

    for group_name in sorted(groups):
        _ranked, top_two, third_place = simulate_group(groups[group_name], rng, tie_rng)
        qualified.extend(top_two)
        third_place_standings.append(third_place)

    best_thirds = rank_third_place_teams(third_place_standings, tie_rng)[:8]
    qualified.extend(standing.team for standing in best_thirds)
    return qualified, best_thirds


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
