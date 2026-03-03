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
