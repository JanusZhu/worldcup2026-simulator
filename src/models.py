from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Team:
    name: str
    elo: float
    attack: float
    defense: float
    confederation: str
    is_host: bool


@dataclass(frozen=True)
class MatchResult:
    team_a: Team
    team_b: Team
    goals_a: int
    goals_b: int
    winner: Team | None
    went_to_penalties: bool = False


@dataclass(frozen=True)
class FixedMatchResult:
    team_a: str
    team_b: str
    goals_a: int
    goals_b: int


@dataclass
class TeamStanding:
    team: Team
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against
