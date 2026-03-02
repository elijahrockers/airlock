import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.models import DatasetType, StudyStatus

# --- Study ---

class StudyCreate(BaseModel):
    irb_pro_number: str = Field(max_length=50)
    title: str = Field(max_length=500)
    description: str | None = None
    pi_name: str = Field(max_length=200)
    requestor: str | None = Field(default=None, max_length=200)


class StudyUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    pi_name: str | None = Field(default=None, max_length=200)
    requestor: str | None = Field(default=None, max_length=200)
    status: StudyStatus | None = None


class StudyResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    irb_pro_number: str
    title: str
    description: str | None
    pi_name: str
    requestor: str | None
    status: StudyStatus
    created_at: datetime
    updated_at: datetime


# --- Global Hash Key ---

class GlobalHashKeyResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    version: int
    is_active: bool
    created_at: datetime
    retired_at: datetime | None


class KeyExportResponse(BaseModel):
    study_id: uuid.UUID
    global_key: str
    global_key_version: int
    project_key: str


# --- Patient Mapping ---

class PatientMappingCreate(BaseModel):
    mrn: str = Field(max_length=50)
    subject_id: str = Field(max_length=100)


class PatientMappingResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    study_id: uuid.UUID
    subject_id: str
    created_at: datetime


class PatientLookupResponse(BaseModel):
    id: uuid.UUID
    study_id: uuid.UUID
    mrn: str
    subject_id: str


class PatientRevealResponse(BaseModel):
    id: uuid.UUID
    study_id: uuid.UUID
    mrn: str
    subject_id: str


class PatientBulkRevealResponse(BaseModel):
    study_id: uuid.UUID
    count: int
    patients: list[PatientRevealResponse]


# --- Dataset Manifest ---

class DatasetManifestCreate(BaseModel):
    dataset_type: DatasetType
    description: str | None = None
    record_count: int | None = None
    metadata_json: dict | None = None


class DatasetManifestResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    study_id: uuid.UUID
    global_hash_key_id: uuid.UUID
    global_key_version: int
    dataset_type: DatasetType
    description: str | None
    record_count: int | None
    metadata_json: dict | None
    created_at: datetime


# --- Accession Mapping ---


class AccessionMappingResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    patient_mapping_id: uuid.UUID
    study_id: uuid.UUID
    dataset_manifest_id: uuid.UUID
    created_at: datetime


class AccessionRevealResponse(BaseModel):
    id: uuid.UUID
    patient_mapping_id: uuid.UUID
    study_id: uuid.UUID
    dataset_manifest_id: uuid.UUID
    accession_number: str
    subject_id: str


class AccessionBulkRevealResponse(BaseModel):
    study_id: uuid.UUID
    count: int
    accessions: list[AccessionRevealResponse]


# --- Dataset Upload ---


class DatasetUploadRow(BaseModel):
    mrn: str = Field(max_length=50)
    subject_id: str = Field(max_length=100)
    accession_number: str = Field(max_length=100)


class DatasetUploadRequest(BaseModel):
    dataset_type: DatasetType = DatasetType.dicom_images
    description: str | None = None
    records: list[DatasetUploadRow] = Field(min_length=1)


class DatasetUploadResponse(BaseModel):
    manifest: DatasetManifestResponse
    patients_created: int
    patients_reused: int
    accessions_created: int


# --- Audit Log ---

class AuditLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    timestamp: datetime
    actor: str
    action: str
    resource_type: str
    resource_id: str | None
    detail: dict | None
    ip_address: str | None
