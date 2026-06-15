from src.data_loader import load_groups, load_teams
from src.monte_carlo import run_simulations


def test_full_tournament_simulation_returns_probabilities() -> None:
    teams = load_teams("data/teams.csv")
    groups = load_groups("data/groups.csv", teams)

    results = run_simulations(3, teams, groups, seed=123)

    assert len(results) == 48
    assert set(results.columns) == {
        "team",
        "champion_prob",
        "final_prob",
        "semifinal_prob",
        "quarterfinal_prob",
        "round_of_16_prob",
        "round_of_32_prob",
        "group_eliminated_prob",
    }
    assert results["champion_prob"].sum() == 1
