import pytest

RESEARCHER = {"X-User-Role": "researcher"}


@pytest.fixture
async def study_with_key(client):
    """Create a researcher-owned study in pending_researcher status with a global key."""
    await client.post("/api/v1/keys/global/rotate")
    resp = await client.post(
        "/api/v1/studies",
        json={
            "irb_pro_number": "PRO-ACC-TEST",
            "title": "Accession Test Study",
            "pi_name": "Dr. Accession",
        },
        headers=RESEARCHER,
    )
    study_id = resp.json()["id"]
    return study_id


def _upload_payload(records, **kwargs):
    return {"records": records, **kwargs}


class TestDatasetUpload:
    async def test_upload_happy_path(self, client, study_with_key):
        sid = study_with_key
        resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json=_upload_payload([
                {"mrn": "MRN001", "subject_id": "SUBJ-001", "accession_number": "ACC-001"},
                {"mrn": "MRN001", "subject_id": "SUBJ-001", "accession_number": "ACC-002"},
                {"mrn": "MRN002", "subject_id": "SUBJ-002", "accession_number": "ACC-003"},
            ]),
            headers=RESEARCHER,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["patients_created"] == 2
        assert data["patients_reused"] == 0
        assert data["accessions_created"] == 3
        assert data["manifest"]["record_count"] == 3
        assert data["manifest"]["global_key_version"] >= 1

    async def test_upload_reuses_existing_patients(self, client, study_with_key):
        sid = study_with_key
        # Add patient first via single endpoint
        await client.post(
            f"/api/v1/studies/{sid}/patients",
            json={"mrn": "MRN-EXIST", "subject_id": "SUBJ-EXIST"},
        )
        # Upload with same MRN
        resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json=_upload_payload([
                {"mrn": "MRN-EXIST", "subject_id": "SUBJ-EXIST", "accession_number": "ACC-E1"},
            ]),
            headers=RESEARCHER,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["patients_created"] == 0
        assert data["patients_reused"] == 1
        assert data["accessions_created"] == 1

    async def test_upload_rejects_inconsistent_mrn_subject(self, client, study_with_key):
        sid = study_with_key
        resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json=_upload_payload([
                {"mrn": "MRN-X", "subject_id": "SUBJ-A", "accession_number": "ACC-X1"},
                {"mrn": "MRN-X", "subject_id": "SUBJ-B", "accession_number": "ACC-X2"},
            ]),
            headers=RESEARCHER,
        )
        assert resp.status_code == 422
        assert "validation_errors" in resp.json()["detail"]

    async def test_upload_rejects_duplicate_accession_in_csv(self, client, study_with_key):
        sid = study_with_key
        resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json=_upload_payload([
                {"mrn": "MRN-D", "subject_id": "SUBJ-D", "accession_number": "ACC-DUP"},
                {"mrn": "MRN-D", "subject_id": "SUBJ-D", "accession_number": "ACC-DUP"},
            ]),
            headers=RESEARCHER,
        )
        assert resp.status_code == 422
        assert "validation_errors" in resp.json()["detail"]

    async def test_upload_rejects_existing_accession(self, client, study_with_key):
        sid = study_with_key
        await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json=_upload_payload([
                {"mrn": "MRN-R", "subject_id": "SUBJ-R", "accession_number": "ACC-REPEAT"},
            ]),
            headers=RESEARCHER,
        )
        resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json=_upload_payload([
                {"mrn": "MRN-R", "subject_id": "SUBJ-R", "accession_number": "ACC-REPEAT"},
            ]),
            headers=RESEARCHER,
        )
        assert resp.status_code == 409

    async def test_upload_rejects_subject_id_conflict(self, client, study_with_key):
        sid = study_with_key
        # Existing patient with SUBJ-TAKEN
        await client.post(
            f"/api/v1/studies/{sid}/patients",
            json={"mrn": "MRN-ORIG", "subject_id": "SUBJ-TAKEN"},
        )
        # Upload with different MRN trying to use same subject_id
        resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json=_upload_payload([
                {"mrn": "MRN-OTHER", "subject_id": "SUBJ-TAKEN", "accession_number": "ACC-T1"},
            ]),
            headers=RESEARCHER,
        )
        assert resp.status_code == 409

    async def test_upload_rejects_mrn_subject_mismatch_with_existing(
        self, client, study_with_key
    ):
        sid = study_with_key
        await client.post(
            f"/api/v1/studies/{sid}/patients",
            json={"mrn": "MRN-MM", "subject_id": "SUBJ-MM-ORIG"},
        )
        resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json=_upload_payload([
                {"mrn": "MRN-MM", "subject_id": "SUBJ-MM-WRONG", "accession_number": "ACC-MM1"},
            ]),
            headers=RESEARCHER,
        )
        assert resp.status_code == 409

    async def test_upload_study_not_found(self, client):
        resp = await client.post(
            "/api/v1/studies/00000000-0000-0000-0000-000000000000/datasets/upload",
            json=_upload_payload([
                {"mrn": "M", "subject_id": "S", "accession_number": "A"},
            ]),
        )
        assert resp.status_code == 404

    async def test_upload_no_global_key(self, client):
        # Create researcher-owned study without rotating a global key first
        resp = await client.post(
            "/api/v1/studies",
            json={
                "irb_pro_number": "PRO-NO-KEY",
                "title": "No Key Study",
                "pi_name": "Dr. NoKey",
            },
            headers=RESEARCHER,
        )
        sid = resp.json()["id"]
        resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json=_upload_payload([
                {"mrn": "M", "subject_id": "S", "accession_number": "A"},
            ]),
            headers=RESEARCHER,
        )
        assert resp.status_code == 400

    async def test_upload_empty_records(self, client, study_with_key):
        sid = study_with_key
        resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json={"records": []},
            headers=RESEARCHER,
        )
        assert resp.status_code == 422

    async def test_broker_cannot_upload(self, client, study_with_key):
        sid = study_with_key
        resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json=_upload_payload([
                {"mrn": "MRN001", "subject_id": "SUBJ-001", "accession_number": "ACC-001"},
            ]),
        )
        assert resp.status_code == 403


class TestAccessionEndpoints:
    @pytest.fixture
    async def uploaded_study(self, client, study_with_key):
        sid = study_with_key
        resp = await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json=_upload_payload([
                {"mrn": "MRN-A1", "subject_id": "SUBJ-A1", "accession_number": "ACC-A1"},
                {"mrn": "MRN-A1", "subject_id": "SUBJ-A1", "accession_number": "ACC-A2"},
                {"mrn": "MRN-A2", "subject_id": "SUBJ-A2", "accession_number": "ACC-A3"},
            ]),
            headers=RESEARCHER,
        )
        manifest_id = resp.json()["manifest"]["id"]
        return sid, manifest_id

    async def test_list_accessions(self, client, uploaded_study):
        sid, _ = uploaded_study
        resp = await client.get(f"/api/v1/studies/{sid}/accessions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        # No plaintext in list response
        assert "accession_number" not in data[0]

    async def test_list_accessions_filter_by_dataset(self, client, uploaded_study):
        sid, manifest_id = uploaded_study
        resp = await client.get(
            f"/api/v1/studies/{sid}/accessions", params={"dataset_id": manifest_id}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 3

        # Filter with a non-existent dataset_id
        resp = await client.get(
            f"/api/v1/studies/{sid}/accessions",
            params={"dataset_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    async def test_reveal_single_accession(self, client, uploaded_study):
        sid, _ = uploaded_study
        accessions = (await client.get(f"/api/v1/studies/{sid}/accessions")).json()
        acc_id = accessions[0]["id"]

        resp = await client.get(f"/api/v1/studies/{sid}/accessions/{acc_id}/reveal")
        assert resp.status_code == 200
        data = resp.json()
        assert data["accession_number"] in {"ACC-A1", "ACC-A2", "ACC-A3"}
        assert data["subject_id"] in {"SUBJ-A1", "SUBJ-A2"}

    async def test_reveal_accession_wrong_study(self, client, uploaded_study):
        sid, _ = uploaded_study
        accessions = (await client.get(f"/api/v1/studies/{sid}/accessions")).json()
        acc_id = accessions[0]["id"]

        # Create a different study
        resp = await client.post(
            "/api/v1/studies",
            json={
                "irb_pro_number": "PRO-ACC-OTHER",
                "title": "Other Study",
                "pi_name": "Dr. Other",
            },
            headers=RESEARCHER,
        )
        other_sid = resp.json()["id"]

        resp = await client.get(f"/api/v1/studies/{other_sid}/accessions/{acc_id}/reveal")
        assert resp.status_code == 404

    async def test_reveal_all_accessions(self, client, uploaded_study):
        sid, _ = uploaded_study
        resp = await client.get(f"/api/v1/studies/{sid}/accessions/reveal-all")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3
        acc_nums = {a["accession_number"] for a in data["accessions"]}
        assert acc_nums == {"ACC-A1", "ACC-A2", "ACC-A3"}

    async def test_reveal_all_accessions_empty(self, client):
        resp = await client.post(
            "/api/v1/studies",
            json={
                "irb_pro_number": "PRO-ACC-EMPTY",
                "title": "Empty Accession Study",
                "pi_name": "Dr. Empty",
            },
            headers=RESEARCHER,
        )
        sid = resp.json()["id"]
        resp = await client.get(f"/api/v1/studies/{sid}/accessions/reveal-all")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0
        assert resp.json()["accessions"] == []


class TestAccessionRoleAccess:
    @pytest.fixture
    async def uploaded_study(self, client, study_with_key):
        sid = study_with_key
        await client.post(
            f"/api/v1/studies/{sid}/datasets/upload",
            json=_upload_payload([
                {"mrn": "MRN-R1", "subject_id": "SUBJ-R1", "accession_number": "ACC-R1"},
            ]),
            headers=RESEARCHER,
        )
        return sid

    async def test_researcher_cannot_reveal_all(self, client, uploaded_study):
        sid = uploaded_study
        resp = await client.get(
            f"/api/v1/studies/{sid}/accessions/reveal-all",
            headers=RESEARCHER,
        )
        assert resp.status_code == 403

    async def test_researcher_cannot_reveal_one(self, client, uploaded_study):
        sid = uploaded_study
        accessions = (await client.get(f"/api/v1/studies/{sid}/accessions")).json()
        acc_id = accessions[0]["id"]
        resp = await client.get(
            f"/api/v1/studies/{sid}/accessions/{acc_id}/reveal",
            headers=RESEARCHER,
        )
        assert resp.status_code == 403
