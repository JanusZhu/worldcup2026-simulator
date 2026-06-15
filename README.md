# worldcup2026-simulator

A typed, modular Python simulator for the 2026 FIFA World Cup format:

- 48 teams
- 12 groups of 4
- group round-robin
- top 2 from each group qualify
- 8 best third-place teams qualify
- 32-team knockout bracket
- knockout matches cannot end in draws

The included `data/teams.csv` and `data/groups.csv` are sample inputs for development. Replace them with official groups and updated ratings when available.

## Rating Sources

The current `data/teams.csv` is generated from public data:

- `elo`: current World Football Elo Ratings from `https://www.eloratings.net/World.tsv`.
- `attack`: recent goals scored per match from `2024-01-01` up to, but not including, the 2026 World Cup start date `2026-06-11`, normalized to the 48-team tournament average.
- `defense`: recent goals allowed per match from `2024-01-01` up to, but not including, `2026-06-11`, normalized to the 48-team tournament average. Lower is better.
- Recent match scores: `https://raw.githubusercontent.com/martj42/international_results/master/results.csv`.
- `host bonus`: model-defined in `src/match_model.py` and applied mainly to Mexico, United States, and Canada through `is_host=true`.

Attack and defense are sample-size smoothed toward `1.0` for teams with fewer than 12 recent matches, then clamped between `0.65` and `1.35` to avoid one small results window overwhelming the simulator.

To refresh the rating file from the public sources:

```powershell
python scripts\generate_real_ratings.py
```

The simulator is intentionally data-driven: updating `data/teams.csv` changes the model inputs without changing the tournament code.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python -m src.main --teams data/teams.csv --groups data/groups.csv --simulations 10000 --seed 42
```

Results are saved to:

```text
outputs/simulation_results.csv
```

The CLI also prints the top 10 most likely champions.

For a quick smoke run:

```powershell
python -m src.main --simulations 100 --seed 42
```

## Single-Match Score Simulation

To estimate group-stage score probabilities for one match:

```powershell
python -m src.main --match-team-a Argentina --match-team-b Jordan --simulations 10000 --seed 42 --output outputs/argentina_jordan_scores.csv
```

This simulates the match once per Monte Carlo sample, allows draws, and saves score probabilities:

```text
score,goals_a,goals_b,count,probability
2-0,2,0,1180,0.118
1-0,1,0,1045,0.1045
```

The CLI also prints expected goals, win/draw/loss probabilities, and the most likely scorelines.

## Web App

To open the local group-stage match predictor:

```powershell
python -m src.web_app
```

Then open:

```text
http://127.0.0.1:5000
```

The page lets you choose a group-stage match, runs `10,000` single-match simulations, and shows flags, team ratings, expected goals, win/draw/loss probabilities, likely scores, schedule details, actual results for completed matches, and a Chinese explanation.

When the web app starts, it tries to load group-stage schedule and result data from:

```text
https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json
```

If the schedule source is unavailable, the app still works with the local group data, but schedule/result fields may be blank.

## Test

```powershell
pytest
```

## Input Files

`teams.csv`

```text
team,elo,attack,defense,confederation,is_host
```

`groups.csv`

```text
group,team
```

Each team in `groups.csv` must exist in `teams.csv`. The loader expects exactly 48 teams, 12 groups, and 4 teams per group.

## Model Notes

Each game is simulated once inside each tournament run. The simulator does not simulate the same fixture many times and then choose the most common result.

### How Each Match Works

1. Start with team ratings:

```text
Elo rating
attack rating
defense rating
host advantage
```

The current sample ratings are inputs in `data/teams.csv`, not live ratings pulled from an external service:

- `elo`: overall team strength. Higher is better.
- `attack`: attacking multiplier. Higher means a stronger attack.
- `defense`: opponent-goals multiplier. Lower means a stronger defense; higher means a weaker defense.
- `is_host`: marks the 2026 host teams: Mexico, United States, and Canada.

The host multiplier is defined in `src/match_model.py`. Host teams get a meaningful expected-goals multiplier, while all non-host teams get only a tiny neutral tournament bump:

```python
HOST_EXPECTED_GOALS_MULTIPLIER = 1.10
NON_HOST_EXPECTED_GOALS_MULTIPLIER = 1.01
```

2. Convert ratings into expected goals.

Expected goals are calculated with:

```python
base_goals = 1.35
elo_diff = team_a.elo - team_b.elo
lambda_a = base_goals * exp(elo_diff / 600) * team_a.attack * team_b.defense * host_bonus_a
lambda_b = base_goals * exp(-elo_diff / 600) * team_b.attack * team_a.defense * host_bonus_b
```

The pieces mean:

- `base_goals`: neutral scoring level before team strength is applied.
- `exp(elo_diff / 600)`: increases expected goals for the stronger Elo team and decreases them for the weaker Elo team.
- `team_a.attack`: boosts team A if it has a stronger attack.
- `team_b.defense`: boosts team A if team B has a weaker defense, because higher defense values mean more goals allowed.
- `host_bonus_a`: gives a large boost only to Mexico, United States, and Canada; other teams receive only the tiny non-host multiplier.

Expected goals are clamped between `0.2` and `4.0`.

3. Generate actual goals with a Poisson distribution.

```python
goals_a = poisson(lambda_a)
goals_b = poisson(lambda_b)
```

This keeps real match randomness alive: favorites usually do better, but underdogs can still win.

4. Decide the match result.

In the group stage, tied scores remain draws. In the knockout stage, tied scores go to reduced-goal extra time. If still tied, the winner is decided by Elo-weighted penalties.

5. Record the result.

Group matches update points, goal difference, and goals scored. Knockout matches advance exactly one winner and eliminate the loser.

Monte Carlo probabilities come from repeating the entire tournament many times and counting how often each team reaches each stage.

## Upgrade Paths

- Replace sample groups with the official FIFA group draw.
- Replace the MVP deterministic knockout pairing in `src/knockout.py` with official bracket mapping.
- Calibrate attack and defense ratings from goals, xG, betting lines, or player-level models.
- Add uncertainty bands by running multiple parameter sets.
