from datetime import date, timedelta

import pytest

RESEARCHER = {"X-User-Role": "researcher"}
BROKER = {}  # default role is broker


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
        resp = await client.post(
            "/api/v1/studies", json=study_payload, headers=RESEARCHER
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["irb_pro_number"] == study_payload["irb_pro_number"]
        assert data["status"] == "pending_researcher"
        assert data["requested_by"] == "dev_user"
        assert "id" in data

    async def test_broker_cannot_create_study(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-BRK-FAIL"},
        )
        assert resp.status_code == 403

    async def test_list_studies(self, client, study_payload):
        await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-LIST-1"},
            headers=RESEARCHER,
        )
        resp = await client.get("/api/v1/studies")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1

    async def test_get_study(self, client, study_payload):
        create_resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-GET-1"},
            headers=RESEARCHER,
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
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-UPD-1"},
            headers=RESEARCHER,
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
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-TP-DEF"},
            headers=RESEARCHER,
        )
        assert resp.status_code == 201
        assert resp.json()["temporal_policy"] == "removed"

    async def test_create_study_with_shifted(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={
                **study_payload,
                "irb_pro_number": "PRO-TP-SHIFT",
                "temporal_policy": "shifted",
            },
            headers=RESEARCHER,
        )
        assert resp.status_code == 201
        assert resp.json()["temporal_policy"] == "shifted"

    async def test_update_temporal_policy(self, client, study_payload):
        create_resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-TP-UPD"},
            headers=RESEARCHER,
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
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-ARC-1"},
            headers=RESEARCHER,
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
            json={
                **study_payload,
                "irb_pro_number": "PRO-EXP-1",
                "expiration_alert_date": alert_date,
            },
            headers=RESEARCHER,
        )
        assert resp.status_code == 201
        assert resp.json()["expiration_alert_date"] == alert_date

    async def test_create_study_without_expiration_defaults_to_null(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-EXP-2"},
            headers=RESEARCHER,
        )
        assert resp.status_code == 201
        assert resp.json()["expiration_alert_date"] is None

    async def test_update_expiration_alert_date(self, client, study_payload):
        create_resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-EXP-3"},
            headers=RESEARCHER,
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
            json={
                **study_payload,
                "irb_pro_number": "PRO-EXP-4",
                "expiration_alert_date": alert_date,
            },
            headers=RESEARCHER,
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
        await client.post(
            "/api/v1/studies",
            json={
                **study_payload,
                "irb_pro_number": "PRO-EXPLIST-1",
                "expiration_alert_date": past,
            },
            headers=RESEARCHER,
        )
        await client.post(
            "/api/v1/studies",
            json={
                **study_payload,
                "irb_pro_number": "PRO-EXPLIST-2",
                "expiration_alert_date": future,
            },
            headers=RESEARCHER,
        )
        await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-EXPLIST-3"},
            headers=RESEARCHER,
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
            json={
                **study_payload,
                "irb_pro_number": "PRO-EXPARC-1",
                "expiration_alert_date": past,
            },
            headers=RESEARCHER,
        )
        study_id = create_resp.json()["id"]
        await client.delete(f"/api/v1/studies/{study_id}")
        resp = await client.get("/api/v1/studies/expiring")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()]
        assert study_id not in ids


class TestResearcherIntake:
    async def test_researcher_creates_pending_study(self, client, study_payload):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-REQ-1"},
            headers=RESEARCHER,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending_researcher"
        assert data["requested_by"] == "dev_user"

    async def test_researcher_list_scoped(self, client, study_payload):
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

    async def test_researcher_update_own_pending(self, client, study_payload):
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
        assert resp.json()["status"] == "pending_researcher"

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
        assert resp.json()["status"] == "pending_researcher"

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


class TestDatasetApprovalWorkflow:
    """Tests for the dataset-driven approval workflow."""

    @pytest.fixture
    async def researcher_study(self, client, study_payload):
        """Create a researcher-owned study with a global key."""
        await client.post("/api/v1/keys/global/rotate")
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": "PRO-WKFL-1"},
            headers=RESEARCHER,
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_upload_transitions_to_pending_broker(self, client, researcher_study):
        sid = researcher_study
        resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json={
                "records": [
                    {"mrn": "MRN001", "subject_id": "SUBJ-001", "accession_number": "ACC-001"},
                ]
            },
            headers=RESEARCHER,
        )
        assert resp.status_code == 201
        assert resp.json()["manifest"]["status"] == "pending"

        study = await client.get(f"/api/v1/studies/{sid}")
        assert study.json()["status"] == "pending_broker"

    async def test_dataset_approval_auto_activates_study(self, client, researcher_study):
        sid = researcher_study
        upload_resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json={
                "records": [
                    {"mrn": "MRN001", "subject_id": "SUBJ-001", "accession_number": "ACC-001"},
                ]
            },
            headers=RESEARCHER,
        )
        dataset_id = upload_resp.json()["manifest"]["id"]

        resp = await client.post(f"/api/v1/studies/{sid}/datasets/{dataset_id}/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"
        assert resp.json()["approved_by"] == "dev_user"
        assert resp.json()["approved_at"] is not None

        study = await client.get(f"/api/v1/studies/{sid}")
        assert study.json()["status"] == "active"

    async def test_additional_dataset_on_active_study(self, client, researcher_study):
        sid = researcher_study
        # First upload + approve
        r1 = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json={
                "records": [
                    {"mrn": "MRN001", "subject_id": "SUBJ-001", "accession_number": "ACC-001"},
                ]
            },
            headers=RESEARCHER,
        )
        d1_id = r1.json()["manifest"]["id"]
        await client.post(f"/api/v1/studies/{sid}/datasets/{d1_id}/approve")

        # Second upload on now-active study
        r2 = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json={
                "records": [
                    {"mrn": "MRN002", "subject_id": "SUBJ-002", "accession_number": "ACC-002"},
                ]
            },
            headers=RESEARCHER,
        )
        assert r2.status_code == 201
        assert r2.json()["manifest"]["status"] == "pending"

        # Study stays active
        study = await client.get(f"/api/v1/studies/{sid}")
        assert study.json()["status"] == "active"

        # Approve second dataset — study stays active
        d2_id = r2.json()["manifest"]["id"]
        resp = await client.post(f"/api/v1/studies/{sid}/datasets/{d2_id}/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

        study = await client.get(f"/api/v1/studies/{sid}")
        assert study.json()["status"] == "active"

    async def test_researcher_cannot_approve_dataset(self, client, researcher_study):
        sid = researcher_study
        upload_resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json={
                "records": [
                    {"mrn": "MRN001", "subject_id": "SUBJ-001", "accession_number": "ACC-001"},
                ]
            },
            headers=RESEARCHER,
        )
        dataset_id = upload_resp.json()["manifest"]["id"]

        resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/{dataset_id}/approve",
            headers=RESEARCHER,
        )
        assert resp.status_code == 403

    async def test_double_approve_dataset_409(self, client, researcher_study):
        sid = researcher_study
        upload_resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json={
                "records": [
                    {"mrn": "MRN001", "subject_id": "SUBJ-001", "accession_number": "ACC-001"},
                ]
            },
            headers=RESEARCHER,
        )
        dataset_id = upload_resp.json()["manifest"]["id"]
        await client.post(f"/api/v1/studies/{sid}/datasets/{dataset_id}/approve")

        resp = await client.post(f"/api/v1/studies/{sid}/datasets/{dataset_id}/approve")
        assert resp.status_code == 409

    async def test_cannot_upload_while_pending_broker(self, client, researcher_study):
        sid = researcher_study
        # First upload transitions to pending_broker
        await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json={
                "records": [
                    {"mrn": "MRN001", "subject_id": "SUBJ-001", "accession_number": "ACC-001"},
                ]
            },
            headers=RESEARCHER,
        )
        # Second upload should fail because study is now pending_broker
        resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json={
                "records": [
                    {"mrn": "MRN002", "subject_id": "SUBJ-002", "accession_number": "ACC-002"},
                ]
            },
            headers=RESEARCHER,
        )
        assert resp.status_code == 409


class TestReidentificationRequests:
    async def _create_study(self, client, study_payload, irb, headers=None):
        resp = await client.post(
            "/api/v1/studies",
            json={**study_payload, "irb_pro_number": irb},
            headers=headers or RESEARCHER,
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
