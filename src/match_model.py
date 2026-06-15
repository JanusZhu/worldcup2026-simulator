from __future__ import annotations

import math
import random

import numpy as np

from .models import MatchResult, Team


BASE_GOALS = 1.35
HOST_EXPECTED_GOALS_MULTIPLIER = 1.10
NON_HOST_EXPECTED_GOALS_MULTIPLIER = 1.01
MIN_EXPECTED_GOALS = 0.2
MAX_EXPECTED_GOALS = 4.0
EXTRA_TIME_FACTOR = 30 / 90


def clamp_expected_goals(value: float) -> float:
    return max(MIN_EXPECTED_GOALS, min(MAX_EXPECTED_GOALS, value))


def host_multiplier(team: Team) -> float:
    return HOST_EXPECTED_GOALS_MULTIPLIER if team.is_host else NON_HOST_EXPECTED_GOALS_MULTIPLIER


def expected_goals(team_a: Team, team_b: Team, extra_time: bool = False) -> tuple[float, float]:
    elo_diff = team_a.elo - team_b.elo
    host_bonus_a = host_multiplier(team_a)
    host_bonus_b = host_multiplier(team_b)

    lambda_a = BASE_GOALS * math.exp(elo_diff / 600) * team_a.attack * team_b.defense * host_bonus_a
    lambda_b = BASE_GOALS * math.exp(-elo_diff / 600) * team_b.attack * team_a.defense * host_bonus_b
    if extra_time:
        lambda_a *= EXTRA_TIME_FACTOR
        lambda_b *= EXTRA_TIME_FACTOR

    return clamp_expected_goals(lambda_a), clamp_expected_goals(lambda_b)


def simulate_match(
    team_a: Team,
    team_b: Team,
    rng: np.random.Generator,
    allow_draw: bool = True,
    penalty_rng: random.Random | None = None,
) -> MatchResult:
    lambda_a, lambda_b = expected_goals(team_a, team_b)
    goals_a = int(rng.poisson(lambda_a))
    goals_b = int(rng.poisson(lambda_b))

    if goals_a > goals_b:
        return MatchResult(team_a, team_b, goals_a, goals_b, team_a)
    if goals_b > goals_a:
        return MatchResult(team_a, team_b, goals_a, goals_b, team_b)
    if allow_draw:
        return MatchResult(team_a, team_b, goals_a, goals_b, None)

    extra_a, extra_b = expected_goals(team_a, team_b, extra_time=True)
    goals_a += int(rng.poisson(extra_a))
    goals_b += int(rng.poisson(extra_b))

    if goals_a > goals_b:
        return MatchResult(team_a, team_b, goals_a, goals_b, team_a)
    if goals_b > goals_a:
        return MatchResult(team_a, team_b, goals_a, goals_b, team_b)

    winner = simulate_penalties(team_a, team_b, penalty_rng or random.Random())
    return MatchResult(team_a, team_b, goals_a, goals_b, winner, went_to_penalties=True)


def simulate_penalties(team_a: Team, team_b: Team, rng: random.Random) -> Team:
    elo_diff = team_a.elo - team_b.elo
    probability_a = 1 / (1 + math.exp(-elo_diff / 400))
    probability_a = max(0.35, min(0.65, probability_a))
    return team_a if rng.random() < probability_a else team_b
