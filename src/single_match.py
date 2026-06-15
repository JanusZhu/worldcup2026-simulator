from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd

from .match_model import expected_goals, simulate_match
from .models import Team


def simulate_score_probabilities(
    team_a: Team,
    team_b: Team,
    simulations: int,
    seed: int = 42,
    allow_draw: bool = True,
) -> tuple[pd.DataFrame, dict[str, float]]:
    if simulations <= 0:
        raise ValueError("Number of simulations must be positive")

    rng = np.random.default_rng(seed)
    score_counts: Counter[tuple[int, int]] = Counter()
    wins_a = 0
    wins_b = 0
    draws = 0

    for _ in range(simulations):
        result = simulate_match(team_a, team_b, rng, allow_draw=allow_draw)
        score_counts[(result.goals_a, result.goals_b)] += 1
        if result.goals_a > result.goals_b:
            wins_a += 1
        elif result.goals_b > result.goals_a:
            wins_b += 1
        else:
            draws += 1

    rows = [
        {
            "score": f"{goals_a}-{goals_b}",
            "goals_a": goals_a,
            "goals_b": goals_b,
            "count": count,
            "probability": count / simulations,
        }
        for (goals_a, goals_b), count in score_counts.items()
    ]

    score_frame = (
        pd.DataFrame(rows)
        .sort_values(["probability", "goals_a", "goals_b"], ascending=[False, True, True])
        .reset_index(drop=True)
    )
    lambda_a, lambda_b = expected_goals(team_a, team_b)
    summary = {
        "expected_goals_a": lambda_a,
        "expected_goals_b": lambda_b,
        "team_a_win_prob": wins_a / simulations,
        "draw_prob": draws / simulations,
        "team_b_win_prob": wins_b / simulations,
    }
    return score_frame, summary
