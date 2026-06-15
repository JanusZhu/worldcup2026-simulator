from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Iterable

import numpy as np
import pandas as pd
from tqdm import tqdm

from .models import FixedMatchResult, Team
from .tournament import simulate_tournament


STAGE_COLUMNS = [
    "champion",
    "final",
    "semifinal",
    "quarterfinal",
    "round_of_16",
    "round_of_32",
]


def run_simulations(
    n: int,
    teams: dict[str, Team],
    groups: dict[str, list[Team]],
    seed: int = 42,
    fixed_results: dict[frozenset[str], FixedMatchResult] | None = None,
    show_progress: bool = True,
) -> pd.DataFrame:
    if n <= 0:
        raise ValueError("Number of simulations must be positive")

    rng = np.random.default_rng(seed)
    tie_rng = random.Random(seed)
    counts: dict[str, dict[str, int]] = {
        team_name: defaultdict(int) for team_name in sorted(teams)
    }

    simulation_range: Iterable[int] = tqdm(range(n), desc="Simulating tournaments") if show_progress else range(n)
    for _ in simulation_range:
        result = simulate_tournament(teams, groups, rng, tie_rng, fixed_results)
        for stage in STAGE_COLUMNS:
            value = result[stage]
            if isinstance(value, list):
                for team in value:
                    counts[team.name][stage] += 1
            else:
                counts[value.name][stage] += 1

    rows = []
    for team_name in sorted(teams):
        team_counts = counts[team_name]
        round_of_32 = team_counts["round_of_32"]
        rows.append(
            {
                "team": team_name,
                "champion_prob": team_counts["champion"] / n,
                "final_prob": team_counts["final"] / n,
                "semifinal_prob": team_counts["semifinal"] / n,
                "quarterfinal_prob": team_counts["quarterfinal"] / n,
                "round_of_16_prob": team_counts["round_of_16"] / n,
                "round_of_32_prob": round_of_32 / n,
                "group_eliminated_prob": 1 - (round_of_32 / n),
            }
        )

    return pd.DataFrame(rows).sort_values("champion_prob", ascending=False).reset_index(drop=True)
