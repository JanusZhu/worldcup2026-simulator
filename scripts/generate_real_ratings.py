from __future__ import annotations

import csv
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd


ELO_WORLD_URL = "https://www.eloratings.net/World.tsv"
ELO_TEAMS_URL = "https://www.eloratings.net/en.teams.tsv"
RESULTS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
RECENT_RESULTS_START = "2024-01-01"
WORLD_CUP_START_DATE = "2026-06-11"
MIN_MATCHES_FOR_FULL_WEIGHT = 12

ELO_NAME_ALIASES = {
    "Congo DR": "DR Congo",
    "Curacao": "Curaçao",
}

RESULTS_NAME_ALIASES = {
    "Czechia": "Czech Republic",
    "Congo DR": "DR Congo",
    "Curacao": "Curaçao",
}

CONFEDERATIONS = {
    "Algeria": "CAF",
    "Argentina": "CONMEBOL",
    "Australia": "AFC",
    "Austria": "UEFA",
    "Belgium": "UEFA",
    "Bosnia and Herzegovina": "UEFA",
    "Brazil": "CONMEBOL",
    "Canada": "CONCACAF",
    "Cape Verde": "CAF",
    "Colombia": "CONMEBOL",
    "Congo DR": "CAF",
    "Croatia": "UEFA",
    "Curacao": "CONCACAF",
    "Czechia": "UEFA",
    "Ecuador": "CONMEBOL",
    "Egypt": "CAF",
    "England": "UEFA",
    "France": "UEFA",
    "Germany": "UEFA",
    "Ghana": "CAF",
    "Haiti": "CONCACAF",
    "Iran": "AFC",
    "Iraq": "AFC",
    "Ivory Coast": "CAF",
    "Japan": "AFC",
    "Jordan": "AFC",
    "Mexico": "CONCACAF",
    "Morocco": "CAF",
    "Netherlands": "UEFA",
    "New Zealand": "OFC",
    "Norway": "UEFA",
    "Panama": "CONCACAF",
    "Paraguay": "CONMEBOL",
    "Portugal": "UEFA",
    "Qatar": "AFC",
    "Saudi Arabia": "AFC",
    "Scotland": "UEFA",
    "Senegal": "CAF",
    "South Africa": "CAF",
    "South Korea": "AFC",
    "Spain": "UEFA",
    "Sweden": "UEFA",
    "Switzerland": "UEFA",
    "Tunisia": "CAF",
    "Turkey": "UEFA",
    "United States": "CONCACAF",
    "Uruguay": "CONMEBOL",
    "Uzbekistan": "AFC",
}

HOSTS = {"Canada", "Mexico", "United States"}


@dataclass(frozen=True)
class RatingRow:
    team: str
    elo: int
    attack: float
    defense: float
    confederation: str
    is_host: bool


def elo_source_name(team: str) -> str:
    return ELO_NAME_ALIASES.get(team, team)


def results_source_name(team: str) -> str:
    return RESULTS_NAME_ALIASES.get(team, team)



def load_group_teams(groups_path: Path) -> list[str]:
    groups = pd.read_csv(groups_path)
    return groups["team"].tolist()


def load_elo_ratings(world_path: Path, teams_path: Path) -> dict[str, int]:
    code_to_name: dict[str, str] = {}
    with teams_path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            parts = raw_line.rstrip("\n").split("\t")
            if len(parts) >= 2 and not parts[0].endswith("_loc"):
                code_to_name[parts[0]] = parts[1]

    ratings: dict[str, int] = {}
    with world_path.open(encoding="utf-8") as handle:
        reader = csv.reader(handle, delimiter="\t")
        for row in reader:
            if len(row) < 4:
                continue
            code = row[2]
            name = code_to_name.get(code)
            if name:
                ratings[name] = int(row[3])
    return ratings


def load_recent_goal_rates(results_path: Path, teams: list[str]) -> dict[str, tuple[float, float]]:
    results = pd.read_csv(results_path, na_values=["NA"])
    results["date"] = pd.to_datetime(results["date"])
    recent = results[
        (results["date"] >= RECENT_RESULTS_START)
        & (results["date"] < WORLD_CUP_START_DATE)
        & results["home_score"].notna()
        & results["away_score"].notna()
    ]

    tracked = {results_source_name(team) for team in teams}
    stats: dict[str, dict[str, float]] = defaultdict(lambda: {"matches": 0, "gf": 0, "ga": 0})
    for row in recent.itertuples(index=False):
        home = row.home_team
        away = row.away_team
        if home in tracked:
            stats[home]["matches"] += 1
            stats[home]["gf"] += float(row.home_score)
            stats[home]["ga"] += float(row.away_score)
        if away in tracked:
            stats[away]["matches"] += 1
            stats[away]["gf"] += float(row.away_score)
            stats[away]["ga"] += float(row.home_score)

    total_goals_for = sum(stats[results_source_name(team)]["gf"] for team in teams)
    total_goals_against = sum(stats[results_source_name(team)]["ga"] for team in teams)
    total_matches = sum(stats[results_source_name(team)]["matches"] for team in teams)
    average_for = total_goals_for / total_matches
    average_against = total_goals_against / total_matches

    rates: dict[str, tuple[float, float]] = {}
    for team in teams:
        data = stats[results_source_name(team)]
        matches = data["matches"]
        if matches:
            raw_attack = (data["gf"] / matches) / average_for
            raw_defense = (data["ga"] / matches) / average_against
        else:
            raw_attack = 1.0
            raw_defense = 1.0

        sample_weight = min(1.0, matches / MIN_MATCHES_FOR_FULL_WEIGHT)
        attack = 1.0 + (raw_attack - 1.0) * sample_weight
        defense = 1.0 + (raw_defense - 1.0) * sample_weight
        rates[team] = (max(0.65, min(1.35, attack)), max(0.65, min(1.35, defense)))
    return rates


def build_rows(groups_path: Path, world_path: Path, elo_teams_path: Path, results_path: Path) -> list[RatingRow]:
    teams = load_group_teams(groups_path)
    elo_ratings = load_elo_ratings(world_path, elo_teams_path)
    goal_rates = load_recent_goal_rates(results_path, teams)

    rows: list[RatingRow] = []
    missing_elo: list[str] = []
    for team in teams:
        elo = elo_ratings.get(elo_source_name(team))
        if elo is None:
            missing_elo.append(team)
            continue
        attack, defense = goal_rates[team]
        rows.append(
            RatingRow(
                team=team,
                elo=elo,
                attack=round(attack, 3),
                defense=round(defense, 3),
                confederation=CONFEDERATIONS[team],
                is_host=team in HOSTS,
            )
        )

    if missing_elo:
        raise ValueError(f"Missing Elo ratings for: {', '.join(missing_elo)}")
    return rows


def write_teams_csv(rows: list[RatingRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["team", "elo", "attack", "defense", "confederation", "is_host"])
        for row in rows:
            writer.writerow(
                [
                    row.team,
                    row.elo,
                    f"{row.attack:.3f}",
                    f"{row.defense:.3f}",
                    row.confederation,
                    str(row.is_host).lower(),
                ]
            )


def download_text(url: str, output_path: Path) -> None:
    with urllib.request.urlopen(url) as response:
        output_path.write_bytes(response.read())


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    tmp_dir = root / ".rating_sources"
    tmp_dir.mkdir(exist_ok=True)

    world_path = tmp_dir / "World.tsv"
    elo_teams_path = tmp_dir / "en.teams.tsv"
    results_path = tmp_dir / "international_results.csv"
    download_text(ELO_WORLD_URL, world_path)
    download_text(ELO_TEAMS_URL, elo_teams_path)
    download_text(RESULTS_URL, results_path)

    rows = build_rows(root / "data" / "groups.csv", world_path, elo_teams_path, results_path)
    write_teams_csv(rows, root / "data" / "teams.csv")
    print(f"Wrote {len(rows)} real-data team ratings to data/teams.csv")
    print(f"Elo source: {ELO_WORLD_URL}")
    print(f"Results source: {RESULTS_URL}")
    print(f"Recent results window starts: {RECENT_RESULTS_START}")
    print(f"Recent results window ends before: {WORLD_CUP_START_DATE}")
    print(f"Generated on: {date.today().isoformat()}")


if __name__ == "__main__":
    main()
