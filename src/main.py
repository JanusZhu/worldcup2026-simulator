from __future__ import annotations

import argparse
from pathlib import Path

from .data_loader import load_groups, load_teams
from .monte_carlo import run_simulations
from .schedule_loader import fixed_results_from_schedules, load_match_schedule
from .single_match import simulate_score_probabilities


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate the 2026 FIFA World Cup.")
    parser.add_argument("--teams", default="data/teams.csv", help="Path to teams CSV")
    parser.add_argument("--groups", default="data/groups.csv", help="Path to groups CSV")
    parser.add_argument("--simulations", type=int, default=10000, help="Number of tournament simulations")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", default="outputs/simulation_results.csv", help="Output CSV path")
    parser.add_argument("--match-team-a", help="Run single-match score simulation for this team")
    parser.add_argument("--match-team-b", help="Run single-match score simulation against this team")
    parser.add_argument("--top-scores", type=int, default=10, help="Number of likely scores to print")
    parser.add_argument(
        "--lock-played-results",
        action="store_true",
        help="Use real scores for completed group-stage matches and simulate only remaining matches",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    teams = load_teams(args.teams)

    if args.match_team_a or args.match_team_b:
        if not args.match_team_a or not args.match_team_b:
            raise ValueError("Both --match-team-a and --match-team-b are required for single-match simulation")
        if args.match_team_a not in teams:
            raise ValueError(f"Unknown team: {args.match_team_a}")
        if args.match_team_b not in teams:
            raise ValueError(f"Unknown team: {args.match_team_b}")

        results, summary = simulate_score_probabilities(
            teams[args.match_team_a],
            teams[args.match_team_b],
            args.simulations,
            seed=args.seed,
            allow_draw=True,
        )
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        results.to_csv(output_path, index=False)

        print(f"Saved score probabilities to {output_path}")
        print(
            f"\nExpected goals: {args.match_team_a} {summary['expected_goals_a']:.2f}, "
            f"{args.match_team_b} {summary['expected_goals_b']:.2f}"
        )
        print("\nResult probabilities:")
        print(f"{args.match_team_a} win: {summary['team_a_win_prob']:.2%}")
        print(f"Draw: {summary['draw_prob']:.2%}")
        print(f"{args.match_team_b} win: {summary['team_b_win_prob']:.2%}")
        print(f"\nTop {args.top_scores} likely scores:")
        print(results[["score", "probability"]].head(args.top_scores).to_string(index=False))
        return

    groups = load_groups(args.groups, teams)
    fixed_results = None
    if args.lock_played_results:
        schedules = load_match_schedule(
            cache_path=Path(".rating_sources") / "worldcup2026_schedule.json",
            allow_network=True,
        )
        fixed_results = fixed_results_from_schedules(schedules)
        print(f"Locked {len(fixed_results)} completed group-stage matches from schedule data.")

    results = run_simulations(args.simulations, teams, groups, seed=args.seed, fixed_results=fixed_results)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path, index=False)

    print(f"Saved results to {output_path}")
    print("\nTop 10 likely champions:")
    print(results[["team", "champion_prob"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
