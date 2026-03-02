import pytest


@pytest.fixture
async def study_id(client):
    resp = await client.post(
        "/api/v1/studies",
        json={
            "irb_pro_number": "PRO-PAT-TEST",
            "title": "Patient Test Study",
            "pi_name": "Dr. Patient",
        },
    )
    return resp.json()["id"]


class TestPatientMappings:
    async def test_add_patient(self, client, study_id):
        resp = await client.post(
            f"/api/v1/studies/{study_id}/patients",
            json={"mrn": "MRN001", "subject_id": "SUBJ-001"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["subject_id"] == "SUBJ-001"
        assert data["study_id"] == study_id
        # MRN should NOT be in the response
        assert "mrn" not in data

    async def test_list_patients(self, client, study_id):
        await client.post(
            f"/api/v1/studies/{study_id}/patients",
            json={"mrn": "MRN002", "subject_id": "SUBJ-002"},
        )
        resp = await client.get(f"/api/v1/studies/{study_id}/patients")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_duplicate_mrn_rejected(self, client, study_id):
        await client.post(
            f"/api/v1/studies/{study_id}/patients",
            json={"mrn": "MRN-DUP", "subject_id": "SUBJ-DUP-1"},
        )
        resp = await client.post(
            f"/api/v1/studies/{study_id}/patients",
            json={"mrn": "MRN-DUP", "subject_id": "SUBJ-DUP-2"},
        )
        assert resp.status_code == 409

    async def test_duplicate_subject_id_rejected(self, client, study_id):
        await client.post(
            f"/api/v1/studies/{study_id}/patients",
            json={"mrn": "MRN-SUBDUP-1", "subject_id": "SUBJ-SAME"},
        )
        resp = await client.post(
            f"/api/v1/studies/{study_id}/patients",
            json={"mrn": "MRN-SUBDUP-2", "subject_id": "SUBJ-SAME"},
        )
        assert resp.status_code == 409

    async def test_lookup_patient(self, client, study_id):
        await client.post(
            f"/api/v1/studies/{study_id}/patients",
            json={"mrn": "MRN-LOOKUP", "subject_id": "SUBJ-LOOKUP"},
        )
        resp = await client.get(
            f"/api/v1/studies/{study_id}/patients/lookup",
            params={"mrn": "MRN-LOOKUP"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mrn"] == "MRN-LOOKUP"
        assert data["subject_id"] == "SUBJ-LOOKUP"

    async def test_lookup_not_found(self, client, study_id):
        resp = await client.get(
            f"/api/v1/studies/{study_id}/patients/lookup",
            params={"mrn": "DOES-NOT-EXIST"},
        )
        assert resp.status_code == 404
