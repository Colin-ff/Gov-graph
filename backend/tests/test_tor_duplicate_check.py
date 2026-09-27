"""Tests for embedding-based duplicate detection.

conftest.py's autouse ``_stub_embeddings`` fixture replaces the real
all-mpnet-base-v2 model with a deterministic bag-of-words embedding for the
whole test suite, so these run fast with no network access or torch. Gemini
verification is untouched by that fixture; it only activates when
``GEMINI_API_KEY`` is set, which none of these tests do except the ones in
the "Gemini verification" section below, so the rest exercise the
cosine-only fallback path.
"""

import json

from app.services import duplicate_verification_service


def _tor_payload(**overrides):
    payload = {
        "group_name": "Research Data Governance Committee",
        "entity_type": "Committee",
        "purpose": "oversee research data management access retention and governance",
        "responsibilities": "monitor research data strategy; review data retention policy",
        "members": [
            {
                "first_name": "Ashley",
                "last_name": "Clay",
                "gender": "female",
                "email": "a.clay@unsw.edu.au",
                "zID": "z5298471",
                "roles": ["Chair"],
                "is_student": False,
                "is_faculty": True,
                "is_external": False,
            },
            {
                "first_name": "Alex",
                "last_name": "Li",
                "gender": "male",
                "email": "a.li@unsw.edu.au",
                "zID": "z5347016",
                "roles": ["Secretariat"],
                "is_student": True,
                "is_faculty": False,
                "is_external": False,
            },
        ],
        "relations": [],
        "reference_links": [],
        "start_date": "2024-06-01",
        "review_date": "2026-06-01",
    }
    payload.update(overrides)
    return payload


def test_submit_tor_form_returns_no_duplicates_when_none_exist(client, admin_headers):
    resp = client.post("/api/tor", json=_tor_payload(), headers=admin_headers)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["possible_duplicates"] == []


def test_check_duplicates_flags_near_duplicate_group(client, admin_headers):
    client.post("/api/tor", json=_tor_payload(), headers=admin_headers)

    near_duplicate = _tor_payload(
        group_name="Research Information Governance Committee",
        purpose="oversee research information management access retention and governance",
    )
    resp = client.post("/api/tor/check-duplicates", json=near_duplicate, headers=admin_headers)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    candidates = resp.get_json()["possible_duplicates"]
    assert candidates
    assert candidates[0]["group_name"] == "Research Data Governance Committee"
    assert candidates[0]["score"] >= 0.55


def test_check_duplicates_excludes_own_group_uuid(client, admin_headers):
    create_resp = client.post("/api/tor", json=_tor_payload(), headers=admin_headers)
    group_uuid = create_resp.get_json()["uuid"]

    own_text = _tor_payload()
    resp = client.post(
        "/api/tor/check-duplicates",
        json={**own_text, "group_uuid": group_uuid},
        headers=admin_headers,
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["possible_duplicates"] == []


def test_check_duplicates_ignores_unrelated_group(client, admin_headers):
    client.post("/api/tor", json=_tor_payload(), headers=admin_headers)

    unrelated = _tor_payload(
        group_name="Campus Sustainability Advisory Group",
        purpose="advise on environmental sustainability initiatives across campus facilities",
        responsibilities="review energy usage; recommend waste reduction measures",
    )
    resp = client.post("/api/tor/check-duplicates", json=unrelated, headers=admin_headers)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["possible_duplicates"] == []


def test_check_duplicates_requires_authentication(client):
    resp = client.post("/api/tor/check-duplicates", json=_tor_payload())

    assert resp.status_code == 401


def test_check_duplicates_validates_required_fields(client, admin_headers):
    resp = client.post("/api/tor/check-duplicates", json={}, headers=admin_headers)

    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"] == "Validation failed"
    assert "purpose" in body["details"]
    assert "responsibilities" in body["details"]
    assert "entity_type" in body["details"]


# ----- Gemini verification ---------------------------------------------------


class _FakeGeminiResponse:
    def __init__(self, payload: dict):
        self.text = json.dumps(payload)


class _FakeGeminiModels:
    def __init__(self, payload: dict):
        self._payload = payload

    def generate_content(self, **kwargs):
        return _FakeGeminiResponse(self._payload)


class _FakeGeminiClient:
    def __init__(self, payload: dict, **kwargs):
        self.models = _FakeGeminiModels(payload)


def _patch_gemini(monkeypatch, payload: dict):
    monkeypatch.setattr(
        duplicate_verification_service.genai,
        "Client",
        lambda **kwargs: _FakeGeminiClient(payload),
    )


def test_check_duplicates_drops_candidate_gemini_rejects(app, client, admin_headers, monkeypatch):
    create_resp = client.post("/api/tor", json=_tor_payload(), headers=admin_headers)
    existing_uuid = create_resp.get_json()["uuid"]

    app.config["GEMINI_API_KEY"] = "test-key"
    _patch_gemini(monkeypatch, {"duplicate_uuids": []})

    near_duplicate = _tor_payload(
        group_name="Research Information Governance Committee",
        purpose="oversee research information management access retention and governance",
    )
    resp = client.post("/api/tor/check-duplicates", json=near_duplicate, headers=admin_headers)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["possible_duplicates"] == []
    assert existing_uuid  # the cosine search did find a candidate to reject


def test_check_duplicates_keeps_candidate_gemini_confirms(app, client, admin_headers, monkeypatch):
    create_resp = client.post("/api/tor", json=_tor_payload(), headers=admin_headers)
    existing_uuid = create_resp.get_json()["uuid"]

    app.config["GEMINI_API_KEY"] = "test-key"
    _patch_gemini(monkeypatch, {"duplicate_uuids": [existing_uuid]})

    near_duplicate = _tor_payload(
        group_name="Research Information Governance Committee",
        purpose="oversee research information management access retention and governance",
    )
    resp = client.post("/api/tor/check-duplicates", json=near_duplicate, headers=admin_headers)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    candidates = resp.get_json()["possible_duplicates"]
    assert [c["uuid"] for c in candidates] == [existing_uuid]


def test_check_duplicates_falls_back_to_cosine_results_when_gemini_fails(
    app, client, admin_headers, monkeypatch
):
    client.post("/api/tor", json=_tor_payload(), headers=admin_headers)

    app.config["GEMINI_API_KEY"] = "test-key"

    class _FailingModels:
        def generate_content(self, **kwargs):
            from google.genai import errors

            raise errors.APIError(500, {"error": {"message": "boom"}})

    class _FailingClient:
        def __init__(self, **kwargs):
            self.models = _FailingModels()

    monkeypatch.setattr(
        duplicate_verification_service.genai, "Client", lambda **kwargs: _FailingClient()
    )

    near_duplicate = _tor_payload(
        group_name="Research Information Governance Committee",
        purpose="oversee research information management access retention and governance",
    )
    resp = client.post("/api/tor/check-duplicates", json=near_duplicate, headers=admin_headers)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    candidates = resp.get_json()["possible_duplicates"]
    assert candidates
    assert candidates[0]["group_name"] == "Research Data Governance Committee"
