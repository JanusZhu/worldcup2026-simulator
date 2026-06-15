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


def test_current_probabilities_api_locks_completed_matches() -> None:
    client = app.test_client()

    response = client.get("/api/current-probabilities")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["locked_matches"] == 1
    assert payload["last_updated"]
    assert payload["cache_ttl_seconds"] == 300
    assert len(payload["groups"]) == 12
    group_c = next(group for group in payload["groups"] if group["group"] == "C")
    brazil = next(standing for standing in group_c["standings"] if standing["team"]["name"] == "Brazil")
    morocco = next(standing for standing in group_c["standings"] if standing["team"]["name"] == "Morocco")
    assert brazil["played"] == 1
    assert morocco["played"] == 1
    assert brazil["points"] == 1
    assert morocco["points"] == 1
    assert 0 <= brazil["round_of_32_prob"] <= 1
    assert 0 <= brazil["group_eliminated_prob"] <= 1


def test_current_probabilities_api_supports_manual_refresh() -> None:
    client = app.test_client()

    response = client.get("/api/current-probabilities?refresh=1")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["locked_matches"] == 1
    assert payload["last_updated"]
    assert len(payload["groups"]) == 12
