import numpy as np

from src.match_model import expected_goals, host_multiplier, simulate_match
from src.models import Team


def test_expected_goals_respect_strength_and_clamp() -> None:
    strong = Team("Strong", 2100, 1.2, 0.85, "UEFA", False)
    weak = Team("Weak", 1500, 0.8, 1.2, "AFC", False)

    strong_lambda, weak_lambda = expected_goals(strong, weak)

    assert 0.2 <= strong_lambda <= 4.0
    assert 0.2 <= weak_lambda <= 4.0
    assert strong_lambda > weak_lambda


def test_knockout_match_always_has_winner() -> None:
    team_a = Team("A", 1800, 1.0, 1.0, "UEFA", False)
    team_b = Team("B", 1800, 1.0, 1.0, "UEFA", False)

    result = simulate_match(team_a, team_b, np.random.default_rng(1), allow_draw=False)

    assert result.winner in {team_a, team_b}


def test_same_fixture_keeps_match_level_randomness() -> None:
    favorite = Team("Favorite", 2000, 1.1, 0.9, "UEFA", False)
    underdog = Team("Underdog", 1750, 0.95, 1.05, "AFC", False)
    rng = np.random.default_rng(99)

    results = [simulate_match(favorite, underdog, rng, allow_draw=True) for _ in range(50)]
    scores = {(result.goals_a, result.goals_b) for result in results}

    assert len(scores) > 1


def test_host_multiplier_is_meaningful_only_for_hosts() -> None:
    host = Team("United States", 1845, 1.0, 1.0, "CONCACAF", True)
    non_host = Team("France", 2110, 1.0, 1.0, "UEFA", False)

    assert host_multiplier(host) > host_multiplier(non_host)
    assert host_multiplier(non_host) < 1.02
