import random

import numpy as np

from src.knockout import build_round_of_32_bracket, simulate_knockout
from src.models import Team


def _teams(count: int) -> list[Team]:
    return [Team(f"Team {index}", 1800 + index, 1.0, 1.0, "UEFA", False) for index in range(count)]


def test_round_of_32_bracket_pairs_outer_seeds() -> None:
    teams = _teams(32)

    bracket = build_round_of_32_bracket(teams)

    assert bracket[0] == (teams[0], teams[31])
    assert bracket[-1] == (teams[15], teams[16])


def test_knockout_returns_single_champion() -> None:
    result = simulate_knockout(_teams(32), np.random.default_rng(7), random.Random(7))

    assert result["champion"] in result["final"]
