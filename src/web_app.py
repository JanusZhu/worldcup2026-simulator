from __future__ import annotations

import itertools
import os
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

from .data_loader import load_groups, load_teams
from .models import Team
from .schedule_loader import MatchSchedule, load_match_schedule
from .single_match import simulate_score_probabilities


SIMULATIONS_PER_MATCH = 10000
DEFAULT_SEED = 42
ROOT_DIR = Path(__file__).resolve().parents[1]

FLAG_CODES = {
    "Algeria": "dz",
    "Argentina": "ar",
    "Australia": "au",
    "Austria": "at",
    "Belgium": "be",
    "Bosnia and Herzegovina": "ba",
    "Brazil": "br",
    "Canada": "ca",
    "Cape Verde": "cv",
    "Colombia": "co",
    "Congo DR": "cd",
    "Croatia": "hr",
    "Curacao": "cw",
    "Czechia": "cz",
    "Ecuador": "ec",
    "Egypt": "eg",
    "England": "gb-eng",
    "France": "fr",
    "Germany": "de",
    "Ghana": "gh",
    "Haiti": "ht",
    "Iran": "ir",
    "Iraq": "iq",
    "Ivory Coast": "ci",
    "Japan": "jp",
    "Jordan": "jo",
    "Mexico": "mx",
    "Morocco": "ma",
    "Netherlands": "nl",
    "New Zealand": "nz",
    "Norway": "no",
    "Panama": "pa",
    "Paraguay": "py",
    "Portugal": "pt",
    "Qatar": "qa",
    "Saudi Arabia": "sa",
    "Scotland": "gb-sct",
    "Senegal": "sn",
    "South Africa": "za",
    "South Korea": "kr",
    "Spain": "es",
    "Sweden": "se",
    "Switzerland": "ch",
    "Tunisia": "tn",
    "Turkey": "tr",
    "United States": "us",
    "Uruguay": "uy",
    "Uzbekistan": "uz",
}


def flag_url(team_name: str) -> str:
    code = FLAG_CODES.get(team_name)
    return f"https://flagcdn.com/w80/{code}.png" if code else ""


def team_payload(team: Team) -> dict[str, Any]:
    return {
        "name": team.name,
        "elo": team.elo,
        "attack": team.attack,
        "defense": team.defense,
        "confederation": team.confederation,
        "is_host": team.is_host,
        "flag_url": flag_url(team.name),
    }


def schedule_payload(schedule: MatchSchedule | None) -> dict[str, Any] | None:
    if schedule is None:
        return None
    payload: dict[str, Any] = {
        "date": schedule.date,
        "time": schedule.time,
        "ground": schedule.ground,
        "round": schedule.round_name,
        "status": "played" if schedule.is_played else "scheduled",
        "is_played": schedule.is_played,
    }
    if schedule.is_played:
        payload["actual_score"] = f"{schedule.actual_goals_a}-{schedule.actual_goals_b}"
        payload["actual_goals_a"] = schedule.actual_goals_a
        payload["actual_goals_b"] = schedule.actual_goals_b
    return payload


def match_label(team_a: str, team_b: str, schedule: MatchSchedule | None) -> str:
    prefix = f"{schedule.date} " if schedule and schedule.date else ""
    suffix = " 已结束" if schedule and schedule.is_played else ""
    return f"{prefix}{team_a} vs {team_b}{suffix}"


def schedule_lookup(schedules: list[MatchSchedule]) -> dict[frozenset[str], MatchSchedule]:
    return {
        frozenset((schedule.team_a, schedule.team_b)): schedule
        for schedule in schedules
    }


def build_match_options(
    groups: dict[str, list[Team]],
    schedules: list[MatchSchedule],
) -> dict[str, list[dict[str, Any]]]:
    by_match = schedule_lookup(schedules)
    options: dict[str, list[dict[str, Any]]] = {}
    for group, teams in groups.items():
        group_options: list[dict[str, Any]] = []
        for team_a, team_b in itertools.combinations(teams, 2):
            schedule = by_match.get(frozenset((team_a.name, team_b.name)))
            scheduled_a = schedule.team_a if schedule else team_a.name
            scheduled_b = schedule.team_b if schedule else team_b.name
            group_options.append(
                {
                    "team_a": scheduled_a,
                    "team_b": scheduled_b,
                    "label": match_label(scheduled_a, scheduled_b, schedule),
                    "schedule": schedule_payload(schedule),
                }
            )
        group_options.sort(key=lambda match: ((match["schedule"] or {}).get("date", ""), (match["schedule"] or {}).get("time", "")))
        options[group] = group_options
    return options


def make_explanation(
    team_a: Team,
    team_b: Team,
    summary: dict[str, float],
    top_scores: list[dict[str, Any]],
    schedule: MatchSchedule | None = None,
    actual_probability: float | None = None,
) -> str:
    result_probs = {
        team_a.name: summary["team_a_win_prob"],
        "平局": summary["draw_prob"],
        team_b.name: summary["team_b_win_prob"],
    }
    most_likely_result = max(result_probs, key=result_probs.get)
    xg_a = summary["expected_goals_a"]
    xg_b = summary["expected_goals_b"]
    xg_gap = abs(xg_a - xg_b)
    top_three_total_goals = [
        score["goals_a"] + score["goals_b"]
        for score in top_scores[:3]
    ]
    average_top_goals = sum(top_three_total_goals) / len(top_three_total_goals) if top_three_total_goals else 0

    if most_likely_result == "平局" or max(result_probs.values()) - sorted(result_probs.values())[-2] < 0.05:
        opening = "这场比赛的分布比较接近，模型没有给出非常明确的一边倒倾向。"
    elif most_likely_result == team_a.name:
        opening = f"模型更偏向 {team_a.name}，它在 10,000 次模拟中的胜率最高。"
    else:
        opening = f"模型更偏向 {team_b.name}，它在 10,000 次模拟中的胜率最高。"

    if xg_gap < 0.25:
        xg_text = f"从 expected goals 看，双方差距很小：{team_a.name} 为 {xg_a:.2f}，{team_b.name} 为 {xg_b:.2f}。"
    elif xg_a > xg_b:
        xg_text = f"从 expected goals 看，{team_a.name} 的进球期望更高：{xg_a:.2f} 对 {xg_b:.2f}。"
    else:
        xg_text = f"从 expected goals 看，{team_b.name} 的进球期望更高：{xg_b:.2f} 对 {xg_a:.2f}。"

    scoring_text = (
        "最可能比分集中在低比分区间，说明这场比赛在模型里更像是细节决定结果。"
        if average_top_goals <= 2.25
        else "最可能比分包含较多进球，说明模型认为这场比赛有一定开放性。"
    )
    host_text = ""
    if team_a.is_host or team_b.is_host:
        hosts = "、".join(team.name for team in (team_a, team_b) if team.is_host)
        host_text = f" {hosts} 是东道主，模型会给它一个额外的主办国进球期望加成。"
    actual_text = ""
    if schedule and schedule.is_played:
        if actual_probability is not None:
            actual_text = (
                f" 实际赛果是 {team_a.name} {schedule.actual_goals_a}-{schedule.actual_goals_b} {team_b.name}，"
                f"这个比分在赛前模型模拟中的概率约为 {actual_probability:.1%}。"
            )

    return (
        f"{opening} {xg_text} 这些数值由 Elo、进攻 rating、对手防守 rating 和东道主加成共同计算。"
        f"{host_text}{actual_text} {scoring_text} 这不是确定预测，而是 10,000 次蒙特卡洛模拟下的概率分布。"
    )


def create_app(
    schedules: list[MatchSchedule] | None = None,
    allow_schedule_network: bool = False,
) -> Flask:
    app = Flask(__name__)
    teams = load_teams(ROOT_DIR / "data" / "teams.csv")
    groups = load_groups(ROOT_DIR / "data" / "groups.csv", teams)
    if schedules is None:
        schedules = load_match_schedule(
            cache_path=ROOT_DIR / ".rating_sources" / "worldcup2026_schedule.json",
            allow_network=allow_schedule_network,
        )
    match_options = build_match_options(groups, schedules)
    schedules_by_match = schedule_lookup(schedules)
    valid_group_matches = {
        frozenset((match["team_a"], match["team_b"]))
        for matches in match_options.values()
        for match in matches
    }

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/api/groups")
    def api_groups() -> Any:
        return jsonify(
            {
                "groups": [
                    {
                        "group": group,
                        "teams": [team_payload(team) for team in group_teams],
                        "matches": match_options[group],
                    }
                    for group, group_teams in groups.items()
                ]
            }
        )

    @app.post("/api/simulate-match")
    def api_simulate_match() -> Any:
        payload = request.get_json(silent=True) or {}
        team_a_name = payload.get("team_a")
        team_b_name = payload.get("team_b")
        if team_a_name not in teams or team_b_name not in teams:
            return jsonify({"error": "Unknown team"}), 400
        if frozenset((team_a_name, team_b_name)) not in valid_group_matches:
            return jsonify({"error": "Match must be one of the configured group-stage matches"}), 400

        team_a = teams[team_a_name]
        team_b = teams[team_b_name]
        scores, summary = simulate_score_probabilities(
            team_a,
            team_b,
            SIMULATIONS_PER_MATCH,
            seed=DEFAULT_SEED,
            allow_draw=True,
        )
        top_scores = scores.head(10).to_dict(orient="records")
        schedule = schedules_by_match.get(frozenset((team_a_name, team_b_name)))
        actual_probability = None
        if schedule and schedule.is_played:
            match_score = scores[
                (scores["goals_a"] == schedule.actual_goals_a)
                & (scores["goals_b"] == schedule.actual_goals_b)
            ]
            if not match_score.empty:
                actual_probability = float(match_score.iloc[0]["probability"])
        return jsonify(
            {
                "team_a": team_payload(team_a),
                "team_b": team_payload(team_b),
                "simulations": SIMULATIONS_PER_MATCH,
                "schedule": schedule_payload(schedule),
                "expected_goals_a": summary["expected_goals_a"],
                "expected_goals_b": summary["expected_goals_b"],
                "team_a_win_prob": summary["team_a_win_prob"],
                "draw_prob": summary["draw_prob"],
                "team_b_win_prob": summary["team_b_win_prob"],
                "top_scores": top_scores,
                "actual_score_probability": actual_probability,
                "explanation": make_explanation(
                    team_a,
                    team_b,
                    summary,
                    top_scores,
                    schedule,
                    actual_probability,
                ),
            }
        )

    return app


app = create_app(allow_schedule_network=os.environ.get("ENABLE_SCHEDULE_NETWORK", "0") == "1")


def main() -> None:
    port = int(os.environ.get("PORT", "5000"))
    create_app(allow_schedule_network=True).run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
