import random

from src.group_stage import rank_standings
from src.models import Team, TeamStanding


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
