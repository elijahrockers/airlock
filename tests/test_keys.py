import pytest


class TestGlobalKeys:
    async def test_rotate_creates_key(self, client):
        resp = await client.post("/api/v1/keys/global/rotate")
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_active"] is True
        assert data["version"] >= 1

    async def test_list_global_keys(self, client):
        await client.post("/api/v1/keys/global/rotate")
        resp = await client.get("/api/v1/keys/global")
        assert resp.status_code == 200
        keys = resp.json()
        assert len(keys) >= 1

    async def test_rotation_retires_old_key(self, client):
        resp1 = await client.post("/api/v1/keys/global/rotate")
        v1 = resp1.json()["version"]
        resp2 = await client.post("/api/v1/keys/global/rotate")
        v2 = resp2.json()["version"]
        assert v2 == v1 + 1

        keys = (await client.get("/api/v1/keys/global")).json()
        active_keys = [k for k in keys if k["is_active"]]
        assert len(active_keys) == 1
        assert active_keys[0]["version"] == v2


class TestKeyExport:
    @pytest.fixture
    async def study_with_global_key(self, client):
        await client.post("/api/v1/keys/global/rotate")
        resp = await client.post(
            "/api/v1/studies",
            json={
                "irb_pro_number": "PRO-KEY-EXPORT",
                "title": "Key Export Test",
                "pi_name": "Dr. Key",
            },
        )
        return resp.json()["id"]

    async def test_export_keys(self, client, study_with_global_key):
        study_id = study_with_global_key
        resp = await client.get(f"/api/v1/keys/study/{study_id}/export")
        assert resp.status_code == 200
        data = resp.json()
        assert data["study_id"] == study_id
        assert len(data["global_key"]) == 44
        assert len(data["project_key"]) == 44
        assert data["global_key_version"] >= 1

    async def test_export_includes_temporal_policy(self, client, study_with_global_key):
        study_id = study_with_global_key
        resp = await client.get(f"/api/v1/keys/study/{study_id}/export")
        assert resp.status_code == 200
        assert resp.json()["temporal_policy"] == "removed"

    async def test_export_temporal_policy_shifted(self, client):
        await client.post("/api/v1/keys/global/rotate")
        resp = await client.post(
            "/api/v1/studies",
            json={
                "irb_pro_number": "PRO-KEY-TP-SHIFT",
                "title": "Key Export Shifted Test",
                "pi_name": "Dr. Key Shifted",
                "temporal_policy": "shifted",
            },
        )
        study_id = resp.json()["id"]
        resp = await client.get(f"/api/v1/keys/study/{study_id}/export")
        assert resp.status_code == 200
        assert resp.json()["temporal_policy"] == "shifted"

    async def test_export_keys_no_study(self, client):
        resp = await client.get(
            "/api/v1/keys/study/00000000-0000-0000-0000-000000000000/export"
        )
        assert resp.status_code == 404
