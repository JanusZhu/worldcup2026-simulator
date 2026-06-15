from src.models import Team
from src.single_match import simulate_score_probabilities


def test_single_match_score_probabilities_sum_to_one() -> None:
    team_a = Team("A", 1900, 1.05, 0.95, "UEFA", False)
    team_b = Team("B", 1750, 0.95, 1.05, "AFC", False)

    scores, summary = simulate_score_probabilities(team_a, team_b, 200, seed=42)

    assert abs(scores["probability"].sum() - 1.0) < 0.000001
    result_prob_sum = summary["team_a_win_prob"] + summary["draw_prob"] + summary["team_b_win_prob"]
    assert abs(result_prob_sum - 1.0) < 0.000001
    assert {"score", "goals_a", "goals_b", "count", "probability"} <= set(scores.columns)
