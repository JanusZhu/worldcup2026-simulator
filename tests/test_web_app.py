from src.schedule_loader import MatchSchedule
from src.web_app import create_app


app = create_app(
    schedules=[
        MatchSchedule(
            group="C",
            team_a="Brazil",
            team_b="Morocco",
            date="2026-06-13",
            time="18:00 UTC-4",
            ground="New York/New Jersey (East Rutherford)",
            round_name="Matchday 3",
            actual_goals_a=1,
            actual_goals_b=1,
        )
    ]
)


def test_groups_api_returns_groups_and_matches() -> None:
    client = app.test_client()

    response = client.get("/api/groups")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["groups"]) == 12
    assert all(len(group["teams"]) == 4 for group in payload["groups"])
    assert all(len(group["matches"]) == 6 for group in payload["groups"])
    group_c = next(group for group in payload["groups"] if group["group"] == "C")
    brazil_morocco = next(
        match
        for match in group_c["matches"]
        if match["team_a"] == "Brazil" and match["team_b"] == "Morocco"
    )
    assert brazil_morocco["schedule"]["actual_score"] == "1-1"


def test_simulate_match_api_returns_prediction_payload() -> None:
    client = app.test_client()

    response = client.post(
        "/api/simulate-match",
        json={"team_a": "Brazil", "team_b": "Morocco"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    probability_sum = payload["team_a_win_prob"] + payload["draw_prob"] + payload["team_b_win_prob"]
    assert abs(probability_sum - 1.0) < 0.000001
    assert payload["team_a"]["flag_url"].endswith("/br.png")
    assert payload["team_b"]["flag_url"].endswith("/ma.png")
    assert payload["expected_goals_a"] > 0
    assert payload["expected_goals_b"] > 0
    assert payload["schedule"]["status"] == "played"
    assert payload["schedule"]["actual_score"] == "1-1"
    assert payload["actual_score_probability"] is not None
    assert len(payload["top_scores"]) == 10
    assert "实际赛果" in payload["explanation"]
