from __future__ import annotations

import random

import numpy as np

from .group_stage import simulate_group_stage
from .knockout import simulate_knockout
from .models import Team


TournamentResult = dict[str, list[Team] | Team]


def simulate_tournament(
    teams: dict[str, Team],
    groups: dict[str, list[Team]],
    rng: np.random.Generator,
    tie_rng: random.Random,
) -> TournamentResult:
    qualified, _best_thirds = simulate_group_stage(groups, rng, tie_rng)
    if len(qualified) != 32:
        raise RuntimeError(f"Expected 32 qualified teams, found {len(qualified)}")
    return simulate_knockout(qualified, rng, tie_rng)
