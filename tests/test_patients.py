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

    async def test_reveal_patient(self, client, study_id):
        resp = await client.post(
            f"/api/v1/studies/{study_id}/patients",
            json={"mrn": "MRN-REVEAL", "subject_id": "SUBJ-REVEAL"},
        )
        patient_id = resp.json()["id"]

        resp = await client.get(
            f"/api/v1/studies/{study_id}/patients/{patient_id}/reveal"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mrn"] == "MRN-REVEAL"
        assert data["subject_id"] == "SUBJ-REVEAL"
        assert data["id"] == patient_id

    async def test_reveal_patient_not_found(self, client, study_id):
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await client.get(
            f"/api/v1/studies/{study_id}/patients/{fake_id}/reveal"
        )
        assert resp.status_code == 404

    async def test_reveal_patient_wrong_study(self, client, study_id):
        resp = await client.post(
            "/api/v1/studies",
            json={
                "irb_pro_number": "PRO-REVEAL-CROSS",
                "title": "Cross Study Reveal Test",
                "pi_name": "Dr. Cross",
            },
        )
        other_study_id = resp.json()["id"]

        resp = await client.post(
            f"/api/v1/studies/{study_id}/patients",
            json={"mrn": "MRN-CROSS", "subject_id": "SUBJ-CROSS"},
        )
        patient_id = resp.json()["id"]

        resp = await client.get(
            f"/api/v1/studies/{other_study_id}/patients/{patient_id}/reveal"
        )
        assert resp.status_code == 404

    async def test_reveal_all_patients(self, client, study_id):
        await client.post(
            f"/api/v1/studies/{study_id}/patients",
            json={"mrn": "MRN-BULK-1", "subject_id": "SUBJ-BULK-1"},
        )
        await client.post(
            f"/api/v1/studies/{study_id}/patients",
            json={"mrn": "MRN-BULK-2", "subject_id": "SUBJ-BULK-2"},
        )

        resp = await client.get(f"/api/v1/studies/{study_id}/patients/reveal-all")
        assert resp.status_code == 200
        data = resp.json()
        assert data["study_id"] == study_id
        assert data["count"] >= 2
        mrns = {p["mrn"] for p in data["patients"]}
        assert "MRN-BULK-1" in mrns
        assert "MRN-BULK-2" in mrns

    async def test_reveal_offset_null_when_removed(self, client, study_id):
        resp = await client.post(
            f"/api/v1/studies/{study_id}/patients",
            json={"mrn": "MRN-OFF-REM", "subject_id": "SUBJ-OFF-REM"},
        )
        patient_id = resp.json()["id"]
        resp = await client.get(
            f"/api/v1/studies/{study_id}/patients/{patient_id}/reveal"
        )
        assert resp.status_code == 200
        assert resp.json()["date_offset_days"] is None

    async def test_reveal_offset_present_when_shifted(self, client):
        resp = await client.post(
            "/api/v1/studies",
            json={
                "irb_pro_number": "PRO-SHIFTED-OFF",
                "title": "Shifted Offset Test",
                "pi_name": "Dr. Offset",
                "temporal_policy": "shifted",
            },
        )
        shifted_study_id = resp.json()["id"]
        resp = await client.post(
            f"/api/v1/studies/{shifted_study_id}/patients",
            json={"mrn": "MRN-OFF-SHIFT", "subject_id": "SUBJ-OFF-SHIFT"},
        )
        patient_id = resp.json()["id"]
        resp = await client.get(
            f"/api/v1/studies/{shifted_study_id}/patients/{patient_id}/reveal"
        )
        assert resp.status_code == 200
        offset = resp.json()["date_offset_days"]
        assert offset is not None
        assert 1 <= offset <= 3650

    async def test_reveal_all_offset_present_when_shifted(self, client):
        resp = await client.post(
            "/api/v1/studies",
            json={
                "irb_pro_number": "PRO-SHIFTED-BULK",
                "title": "Shifted Bulk Offset Test",
                "pi_name": "Dr. Bulk",
                "temporal_policy": "shifted",
            },
        )
        shifted_study_id = resp.json()["id"]
        await client.post(
            f"/api/v1/studies/{shifted_study_id}/patients",
            json={"mrn": "MRN-BULK-OFF-1", "subject_id": "SUBJ-BULK-OFF-1"},
        )
        await client.post(
            f"/api/v1/studies/{shifted_study_id}/patients",
            json={"mrn": "MRN-BULK-OFF-2", "subject_id": "SUBJ-BULK-OFF-2"},
        )
        resp = await client.get(
            f"/api/v1/studies/{shifted_study_id}/patients/reveal-all"
        )
        assert resp.status_code == 200
        for p in resp.json()["patients"]:
            assert p["date_offset_days"] is not None
            assert 1 <= p["date_offset_days"] <= 3650

    async def test_reveal_offset_deterministic(self, client):
        resp = await client.post(
            "/api/v1/studies",
            json={
                "irb_pro_number": "PRO-SHIFTED-DET",
                "title": "Shifted Deterministic Test",
                "pi_name": "Dr. Det",
                "temporal_policy": "shifted",
            },
        )
        shifted_study_id = resp.json()["id"]
        resp = await client.post(
            f"/api/v1/studies/{shifted_study_id}/patients",
            json={"mrn": "MRN-DET", "subject_id": "SUBJ-DET"},
        )
        patient_id = resp.json()["id"]
        resp1 = await client.get(
            f"/api/v1/studies/{shifted_study_id}/patients/{patient_id}/reveal"
        )
        resp2 = await client.get(
            f"/api/v1/studies/{shifted_study_id}/patients/{patient_id}/reveal"
        )
        assert resp1.json()["date_offset_days"] == resp2.json()["date_offset_days"]

    async def test_date_offset_happy_path(self, client):
        resp = await client.post(
            "/api/v1/studies",
            json={
                "irb_pro_number": "PRO-DATEOFF-OK",
                "title": "Date Offset Happy Path",
                "pi_name": "Dr. Offset",
                "temporal_policy": "shifted",
            },
        )
        shifted_study_id = resp.json()["id"]
        await client.post(
            f"/api/v1/studies/{shifted_study_id}/patients",
            json={"mrn": "MRN-DO-1", "subject_id": "SUBJ-DO-1"},
        )

        resp = await client.get(
            f"/api/v1/studies/{shifted_study_id}/patients/date-offset",
            params={"mrn": "MRN-DO-1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["study_id"] == shifted_study_id
        assert data["subject_id"] == "SUBJ-DO-1"
        assert 1 <= data["date_offset_days"] <= 3650
        # No MRN in response
        assert "mrn" not in data

    async def test_date_offset_409_when_not_shifted(self, client, study_id):
        # Default study fixture has temporal_policy=removed
        await client.post(
            f"/api/v1/studies/{study_id}/patients",
            json={"mrn": "MRN-DO-REM", "subject_id": "SUBJ-DO-REM"},
        )
        resp = await client.get(
            f"/api/v1/studies/{study_id}/patients/date-offset",
            params={"mrn": "MRN-DO-REM"},
        )
        assert resp.status_code == 409

    async def test_date_offset_404_unknown_mrn(self, client):
        resp = await client.post(
            "/api/v1/studies",
            json={
                "irb_pro_number": "PRO-DATEOFF-404",
                "title": "Date Offset 404 Test",
                "pi_name": "Dr. NotFound",
                "temporal_policy": "shifted",
            },
        )
        shifted_study_id = resp.json()["id"]
        resp = await client.get(
            f"/api/v1/studies/{shifted_study_id}/patients/date-offset",
            params={"mrn": "DOES-NOT-EXIST"},
        )
        assert resp.status_code == 404

    async def test_date_offset_matches_reveal(self, client):
        resp = await client.post(
            "/api/v1/studies",
            json={
                "irb_pro_number": "PRO-DATEOFF-MATCH",
                "title": "Date Offset Consistency",
                "pi_name": "Dr. Match",
                "temporal_policy": "shifted",
            },
        )
        shifted_study_id = resp.json()["id"]
        resp = await client.post(
            f"/api/v1/studies/{shifted_study_id}/patients",
            json={"mrn": "MRN-DO-MATCH", "subject_id": "SUBJ-DO-MATCH"},
        )
        patient_id = resp.json()["id"]

        offset_resp = await client.get(
            f"/api/v1/studies/{shifted_study_id}/patients/date-offset",
            params={"mrn": "MRN-DO-MATCH"},
        )
        reveal_resp = await client.get(
            f"/api/v1/studies/{shifted_study_id}/patients/{patient_id}/reveal"
        )
        assert offset_resp.json()["date_offset_days"] == reveal_resp.json()["date_offset_days"]

    async def test_date_offset_deterministic(self, client):
        resp = await client.post(
            "/api/v1/studies",
            json={
                "irb_pro_number": "PRO-DATEOFF-DET",
                "title": "Date Offset Deterministic",
                "pi_name": "Dr. Det",
                "temporal_policy": "shifted",
            },
        )
        shifted_study_id = resp.json()["id"]
        await client.post(
            f"/api/v1/studies/{shifted_study_id}/patients",
            json={"mrn": "MRN-DO-DET", "subject_id": "SUBJ-DO-DET"},
        )

        resp1 = await client.get(
            f"/api/v1/studies/{shifted_study_id}/patients/date-offset",
            params={"mrn": "MRN-DO-DET"},
        )
        resp2 = await client.get(
            f"/api/v1/studies/{shifted_study_id}/patients/date-offset",
            params={"mrn": "MRN-DO-DET"},
        )
        assert resp1.json()["date_offset_days"] == resp2.json()["date_offset_days"]

    async def test_reveal_all_empty_study(self, client):
        resp = await client.post(
            "/api/v1/studies",
            json={
                "irb_pro_number": "PRO-REVEAL-EMPTY",
                "title": "Empty Reveal Test",
                "pi_name": "Dr. Empty",
            },
        )
        empty_study_id = resp.json()["id"]

        resp = await client.get(
            f"/api/v1/studies/{empty_study_id}/patients/reveal-all"
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 0
        assert resp.json()["patients"] == []
