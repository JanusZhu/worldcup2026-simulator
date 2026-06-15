from __future__ import annotations

import random

import numpy as np

from .match_model import simulate_match
from .models import Team


def build_round_of_32_bracket(qualified: list[Team]) -> list[tuple[Team, Team]]:
    if len(qualified) != 32:
        raise ValueError(f"Knockout bracket requires 32 teams, found {len(qualified)}")

    # TODO: Replace MVP pairing with the official FIFA 2026 bracket mapping.
    return [(qualified[index], qualified[-index - 1]) for index in range(16)]


def simulate_knockout_round(
    matches: list[tuple[Team, Team]],
    rng: np.random.Generator,
    penalty_rng: random.Random,
) -> list[Team]:
    winners: list[Team] = []
    for team_a, team_b in matches:
        result = simulate_match(team_a, team_b, rng, allow_draw=False, penalty_rng=penalty_rng)
        if result.winner is None:
            raise RuntimeError("Knockout match ended without a winner")
        winners.append(result.winner)
    return winners


def pair_adjacent(teams: list[Team]) -> list[tuple[Team, Team]]:
    if len(teams) % 2 != 0:
        raise ValueError("Cannot pair an odd number of teams")
    return [(teams[index], teams[index + 1]) for index in range(0, len(teams), 2)]


def simulate_knockout(
    qualified: list[Team],
    rng: np.random.Generator,
    penalty_rng: random.Random,
) -> dict[str, list[Team] | Team]:
    round_of_32_matches = build_round_of_32_bracket(qualified)
    round_of_16 = simulate_knockout_round(round_of_32_matches, rng, penalty_rng)
    quarterfinal = simulate_knockout_round(pair_adjacent(round_of_16), rng, penalty_rng)
    semifinal = simulate_knockout_round(pair_adjacent(quarterfinal), rng, penalty_rng)
    final = simulate_knockout_round(pair_adjacent(semifinal), rng, penalty_rng)
    champion = simulate_knockout_round(pair_adjacent(final), rng, penalty_rng)[0]

    return {
        "round_of_32": qualified,
        "round_of_16": round_of_16,
        "quarterfinal": quarterfinal,
        "semifinal": semifinal,
        "final": final,
        "champion": champion,
    }
