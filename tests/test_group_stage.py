import random

import numpy as np

from src.group_stage import fixed_score_for_match, rank_standings, simulate_group
from src.models import FixedMatchResult, Team, TeamStanding


def test_group_ranking_uses_points_goal_difference_goals_scored() -> None:
    teams = [
        Team("A", 1800, 1.0, 1.0, "UEFA", False),
        Team("B", 1800, 1.0, 1.0, "UEFA", False),
        Team("C", 1800, 1.0, 1.0, "UEFA", False),
    ]
    standings = [
        TeamStanding(teams[0], points=4, goals_for=4, goals_against=2),
        TeamStanding(teams[1], points=6, goals_for=2, goals_against=1),
        TeamStanding(teams[2], points=4, goals_for=3, goals_against=1),
    ]

    ranked = rank_standings(standings, random.Random(42))

    assert [standing.team.name for standing in ranked] == ["B", "A", "C"]


def test_group_simulation_uses_fixed_result_in_requested_order() -> None:
    teams = [
        Team("A", 1800, 1.0, 1.0, "UEFA", False),
        Team("B", 1800, 1.0, 1.0, "UEFA", False),
        Team("C", 1800, 1.0, 1.0, "UEFA", False),
        Team("D", 1800, 1.0, 1.0, "UEFA", False),
    ]
    fixed_results = {
        frozenset(("A", "B")): FixedMatchResult("B", "A", 2, 0),
    }

    fixed_score = fixed_score_for_match(teams[0], teams[1], fixed_results)
    ranked, _top_two, _third = simulate_group(
        teams,
        np.random.default_rng(1),
        random.Random(1),
        fixed_results,
    )

    assert fixed_score == (0, 2)
    assert next(standing for standing in ranked if standing.team.name == "B").points >= 3
