from datetime import date, timedelta

import pytest


@pytest.fixture
async def study_payload():
    return {
        "irb_pro_number": "PRO-2024-0001",
        "title": "Test Study Alpha",
        "description": "A test study for unit testing",
        "pi_name": "Dr. Smith",
        "requestor": "Jane Doe",
    }


class TestStudyCRUD:
    async def test_create_study(self, client, study_payload):
        resp = await client.post("/api/v1/studies", json=study_payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["irb_pro_number"] == study_payload["irb_pro_number"]
        assert data["status"] == "draft"
        assert "id" in data

    async def test_list_studies(self, client, study_payload):
        await client.post("/api/v1/studies", json={**study_payload, "irb_pro_number": "PRO-LIST-1"})
        resp = await client.get("/api/v1/studies")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1

    async def test_get_study(self, client, study_payload):
        create_resp = await client.post(
            "/api/v1/studies", json={**study_payload, "irb_pro_number": "PRO-GET-1"}
        )
        study_id = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/studies/{study_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == study_id

    async def test_get_study_not_found(self, client):
        resp = await client.get("/api/v1/studies/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_update_study(self, client, study_payload):
        create_resp = await client.post(
            "/api/v1/studies", json={**study_payload, "irb_pro_number": "PRO-UPD-1"}
        )
        study_id = create_resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/studies/{study_id}",
            json={"title": "Updated Title", "status": "active"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"
        assert resp.json()["status"] == "active"

    async def test_default_temporal_policy_is_removed(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies", json={**study_payload, "irb_pro_number": "PRO-TP-DEF"}
        )
        assert resp.status_code == 201
        assert resp.json()["temporal_policy"] == "removed"

    async def test_create_study_with_shifted(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-TP-SHIFT", "temporal_policy": "shifted"},
        )
        assert resp.status_code == 201
        assert resp.json()["temporal_policy"] == "shifted"

    async def test_update_temporal_policy(self, client, study_payload):
        create_resp = await client.post(
            "/api/v1/studies", json={**study_payload, "irb_pro_number": "PRO-TP-UPD"}
        )
        study_id = create_resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/studies/{study_id}",
            json={"temporal_policy": "unshifted"},
        )
        assert resp.status_code == 200
        assert resp.json()["temporal_policy"] == "unshifted"

    async def test_archive_study(self, client, study_payload):
        create_resp = await client.post(
            "/api/v1/studies", json={**study_payload, "irb_pro_number": "PRO-ARC-1"}
        )
        study_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/v1/studies/{study_id}")
        assert resp.status_code == 204

        # Verify it's archived
        get_resp = await client.get(f"/api/v1/studies/{study_id}")
        assert get_resp.json()["status"] == "archived"

    async def test_create_study_with_expiration_alert_date(self, client, study_payload):
        alert_date = (date.today() + timedelta(days=90)).isoformat()
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-EXP-1",
                  "expiration_alert_date": alert_date},
        )
        assert resp.status_code == 201
        assert resp.json()["expiration_alert_date"] == alert_date

    async def test_create_study_without_expiration_defaults_to_null(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-EXP-2"},
        )
        assert resp.status_code == 201
        assert resp.json()["expiration_alert_date"] is None

    async def test_update_expiration_alert_date(self, client, study_payload):
        create_resp = await client.post(
            "/api/v1/studies", json={**study_payload, "irb_pro_number": "PRO-EXP-3"}
        )
        study_id = create_resp.json()["id"]
        alert_date = (date.today() + timedelta(days=30)).isoformat()
        resp = await client.patch(
            f"/api/v1/studies/{study_id}",
            json={"expiration_alert_date": alert_date},
        )
        assert resp.status_code == 200
        assert resp.json()["expiration_alert_date"] == alert_date

    async def test_clear_expiration_alert_date(self, client, study_payload):
        alert_date = (date.today() + timedelta(days=60)).isoformat()
        create_resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-EXP-4",
                  "expiration_alert_date": alert_date},
        )
        study_id = create_resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/studies/{study_id}",
            json={"expiration_alert_date": None},
        )
        assert resp.status_code == 200
        assert resp.json()["expiration_alert_date"] is None

    async def test_list_expiring_studies(self, client, study_payload):
        past = (date.today() - timedelta(days=10)).isoformat()
        future = (date.today() + timedelta(days=90)).isoformat()
        # Past date — should appear
        await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-EXPLIST-1",
                  "expiration_alert_date": past},
        )
        # Future date — should not appear
        await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-EXPLIST-2",
                  "expiration_alert_date": future},
        )
        # No date — should not appear
        await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-EXPLIST-3"},
        )
        resp = await client.get("/api/v1/studies/expiring")
        assert resp.status_code == 200
        irbs = [s["irb_pro_number"] for s in resp.json()]
        assert "PRO-EXPLIST-1" in irbs
        assert "PRO-EXPLIST-2" not in irbs
        assert "PRO-EXPLIST-3" not in irbs

    async def test_expiring_excludes_archived(self, client, study_payload):
        past = (date.today() - timedelta(days=5)).isoformat()
        create_resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-EXPARC-1",
                  "expiration_alert_date": past},
        )
        study_id = create_resp.json()["id"]
        # Archive the study
        await client.delete(f"/api/v1/studies/{study_id}")
        resp = await client.get("/api/v1/studies/expiring")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()]
        assert study_id not in ids


RESEARCHER = {"X-User-Role": "researcher"}
BROKER = {}  # default role is broker


class TestResearcherIntake:
    async def test_researcher_creates_requested_study(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-REQ-1"},
            headers=RESEARCHER,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "requested"
        assert data["requested_by"] == "dev_user"

    async def test_broker_creates_draft_study(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-BRK-1"},
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "draft"
        assert resp.json()["requested_by"] is None

    async def test_researcher_list_scoped(self, client, study_payload):
        # Broker creates a study (not owned by researcher)
        await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-SCOPE-BRK"},
        )
        # Researcher creates a study
        await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-SCOPE-RES"},
            headers=RESEARCHER,
        )
        resp = await client.get("/api/v1/studies", headers=RESEARCHER)
        assert resp.status_code == 200
        irbs = [s["irb_pro_number"] for s in resp.json()]
        assert "PRO-SCOPE-RES" in irbs
        assert "PRO-SCOPE-BRK" not in irbs

    async def test_researcher_cannot_access_others_study(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-OWN-403"},
        )
        study_id = resp.json()["id"]
        resp = await client.get(f"/api/v1/studies/{study_id}", headers=RESEARCHER)
        assert resp.status_code == 403

    async def test_approve_study(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-APPROVE"},
            headers=RESEARCHER,
        )
        study_id = resp.json()["id"]
        resp = await client.post(f"/api/v1/studies/{study_id}/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    async def test_reject_study(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-REJECT"},
            headers=RESEARCHER,
        )
        study_id = resp.json()["id"]
        resp = await client.post(f"/api/v1/studies/{study_id}/reject")
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    async def test_approve_non_requested_409(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-APP-409"},
        )
        study_id = resp.json()["id"]
        resp = await client.post(f"/api/v1/studies/{study_id}/approve")
        assert resp.status_code == 409

    async def test_researcher_cannot_approve(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-SELF-APP"},
            headers=RESEARCHER,
        )
        study_id = resp.json()["id"]
        resp = await client.post(
            f"/api/v1/studies/{study_id}/approve", headers=RESEARCHER
        )
        assert resp.status_code == 403

    async def test_researcher_update_own_requested(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-RES-UPD"},
            headers=RESEARCHER,
        )
        study_id = resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/studies/{study_id}",
            json={"title": "Updated by Researcher"},
            headers=RESEARCHER,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated by Researcher"
        # status should remain requested (silently stripped)
        assert resp.json()["status"] == "requested"

    async def test_researcher_cannot_change_status(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-RES-STAT"},
            headers=RESEARCHER,
        )
        study_id = resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/studies/{study_id}",
            json={"status": "active"},
            headers=RESEARCHER,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "requested"

    async def test_researcher_archive_403(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-RES-ARC"},
            headers=RESEARCHER,
        )
        study_id = resp.json()["id"]
        resp = await client.delete(
            f"/api/v1/studies/{study_id}", headers=RESEARCHER
        )
        assert resp.status_code == 403


class TestReidentificationRequests:
    async def _create_study(self, client, study_payload, irb, headers=None):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": irb},
            headers=headers or {},
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_researcher_creates_request(self, client, study_payload):
        study_id = await self._create_study(
            client, study_payload, "PRO-REID-1", RESEARCHER
        )
        resp = await client.post(
            f"/api/v1/studies/{study_id}/reidentification-requests",
            json={"message": "Need to reidentify patient SUBJ-001"},
            headers=RESEARCHER,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["requested_by"] == "dev_user"
        assert data["message"] == "Need to reidentify patient SUBJ-001"

    async def test_researcher_cannot_request_on_others_study(self, client, study_payload):
        # Broker creates a study (not owned by researcher)
        study_id = await self._create_study(
            client, study_payload, "PRO-REID-2"
        )
        resp = await client.post(
            f"/api/v1/studies/{study_id}/reidentification-requests",
            json={"message": "Trying to access other's study"},
            headers=RESEARCHER,
        )
        assert resp.status_code == 403

    async def test_broker_lists_requests(self, client, study_payload):
        study_id = await self._create_study(
            client, study_payload, "PRO-REID-3", RESEARCHER
        )
        await client.post(
            f"/api/v1/studies/{study_id}/reidentification-requests",
            json={"message": "Request 1"},
            headers=RESEARCHER,
        )
        await client.post(
            f"/api/v1/studies/{study_id}/reidentification-requests",
            json={"message": "Request 2"},
            headers=RESEARCHER,
        )
        resp = await client.get(
            f"/api/v1/studies/{study_id}/reidentification-requests"
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_broker_resolves_request(self, client, study_payload):
        study_id = await self._create_study(
            client, study_payload, "PRO-REID-4", RESEARCHER
        )
        create_resp = await client.post(
            f"/api/v1/studies/{study_id}/reidentification-requests",
            json={"message": "Please reidentify"},
            headers=RESEARCHER,
        )
        request_id = create_resp.json()["id"]
        resp = await client.post(
            f"/api/v1/studies/{study_id}/reidentification-requests/{request_id}/resolve",
            json={"status": "completed"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["resolved_by"] == "dev_user"
        assert data["resolved_at"] is not None

    async def test_double_resolve_409(self, client, study_payload):
        study_id = await self._create_study(
            client, study_payload, "PRO-REID-5", RESEARCHER
        )
        create_resp = await client.post(
            f"/api/v1/studies/{study_id}/reidentification-requests",
            json={"message": "Please reidentify"},
            headers=RESEARCHER,
        )
        request_id = create_resp.json()["id"]
        await client.post(
            f"/api/v1/studies/{study_id}/reidentification-requests/{request_id}/resolve",
            json={"status": "completed"},
        )
        resp = await client.post(
            f"/api/v1/studies/{study_id}/reidentification-requests/{request_id}/resolve",
            json={"status": "denied"},
        )
        assert resp.status_code == 409

    async def test_researcher_cannot_resolve(self, client, study_payload):
        study_id = await self._create_study(
            client, study_payload, "PRO-REID-6", RESEARCHER
        )
        create_resp = await client.post(
            f"/api/v1/studies/{study_id}/reidentification-requests",
            json={"message": "Please reidentify"},
            headers=RESEARCHER,
        )
        request_id = create_resp.json()["id"]
        resp = await client.post(
            f"/api/v1/studies/{study_id}/reidentification-requests/{request_id}/resolve",
            json={"status": "completed"},
            headers=RESEARCHER,
        )
        assert resp.status_code == 403
