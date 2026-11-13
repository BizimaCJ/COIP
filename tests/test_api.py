import pytest

NEW = {"protected_area_id": 1, "area_ha": 14.2, "created_by": 1}
PATH = ["prioritized", "assigned", "investigated", "intervened", "verifying", "closed"]


def move(client, case_id, to, reason="evidence reviewed", by=1):
    return client.post(f"/cases/{case_id}/transition",
                       json={"to_status": to, "changed_by": by, "reason": reason})


def make_case(client, **over):
    r = client.post("/cases", json={**NEW, **over})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.parametrize("ha,sev", [(0.5, "Low"), (1, "Medium"), (4.9, "Medium"),
                                    (5, "High"), (20, "High"), (20.1, "Critical")])
def test_severity_bands(client, ha, sev):
    assert make_case(client, area_ha=ha)["severity"] == sev


def test_new_case_starts_detected_with_a_log_entry(client):
    case = make_case(client)
    assert case["status"] == "detected"
    assert case["allowed_next"] == ["prioritized"]
    hist = client.get(f"/cases/{case['id']}/history").json()
    assert len(hist) == 1 and hist[0]["from_status"] is None


def test_geometry_round_trips_through_postgis(client):
    poly = {"type": "Polygon", "coordinates": [[[29.2, -2.5], [29.21, -2.5], [29.21, -2.51], [29.2, -2.5]]]}
    case = make_case(client, geometry=poly)
    assert client.get(f"/cases/{case['id']}").json()["geometry"]["type"] == "Polygon"


def test_illegal_jump_is_rejected_with_409_and_helpful_body(client):
    case = make_case(client)
    r = move(client, case["id"], "closed")
    assert r.status_code == 409
    d = r.json()["detail"]
    assert d["error"] == "invalid_transition"
    assert d["current_status"] == "detected"
    assert d["allowed_next"] == ["prioritized"]


def test_rejected_move_changes_nothing_and_logs_nothing(client):
    case = make_case(client)
    move(client, case["id"], "closed")
    assert client.get(f"/cases/{case['id']}").json()["status"] == "detected"
    assert len(client.get(f"/cases/{case['id']}/history").json()) == 1


def test_full_lifecycle_is_logged_with_who_when_why(client):
    cid = make_case(client)["id"]
    for step in PATH:
        assert move(client, cid, step, reason=f"going to {step}").status_code == 200
    case = client.get(f"/cases/{cid}").json()
    assert case["status"] == "closed" and case["closed_at"] is not None
    hist = client.get(f"/cases/{cid}/history").json()
    assert [h["to_status"] for h in hist] == ["detected"] + PATH
    assert all(h["changed_by"] and h["changed_at"] and h["reason"] for h in hist)


def test_verifying_can_loop_back_for_more_intervention(client):
    cid = make_case(client)["id"]
    for step in PATH[:5]:
        move(client, cid, step)
    r = move(client, cid, "intervened", reason="loss continued after 6 months")
    assert r.status_code == 200 and r.json()["status"] == "intervened"


def test_closed_case_reopens_and_clears_closed_at(client):
    cid = make_case(client)["id"]
    for step in PATH:
        move(client, cid, step)
    r = move(client, cid, "detected", reason="new alert inside the closed footprint")
    assert r.status_code == 200
    assert r.json()["status"] == "detected" and r.json()["closed_at"] is None


def test_reason_is_required(client):
    cid = make_case(client)["id"]
    assert move(client, cid, "prioritized", reason="").status_code == 422


def test_unknown_status_user_and_case(client):
    cid = make_case(client)["id"]
    assert move(client, cid, "teleported").status_code == 422
    assert move(client, cid, "prioritized", by=999).status_code == 404
    assert move(client, 9999, "prioritized").status_code == 404


def test_list_filters(client):
    a = make_case(client, area_ha=30)["id"]
    make_case(client, area_ha=0.5)
    move(client, a, "prioritized")
    assert len(client.get("/cases").json()) == 2
    assert [c["id"] for c in client.get("/cases?status=prioritized").json()] == [a]
    assert [c["id"] for c in client.get("/cases?severity=Critical").json()] == [a]


def test_transitions_endpoint_lists_all_arrows(client):
    assert len(client.get("/transitions").json()) == 8
