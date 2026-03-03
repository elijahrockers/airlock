import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class StudyStatus(str, enum.Enum):
    requested = "requested"
    draft = "draft"
    active = "active"
    completed = "completed"
    archived = "archived"
    rejected = "rejected"


class DatasetType(str, enum.Enum):
    dicom_images = "dicom_images"
    clinical_data = "clinical_data"
    pathology = "pathology"
    genomics = "genomics"
    other = "other"


class TemporalPolicy(str, enum.Enum):
    removed = "removed"
    shifted = "shifted"
    unshifted = "unshifted"


class ReidentificationStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    denied = "denied"


class Study(Base):
    __tablename__ = "studies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    irb_pro_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    pi_name: Mapped[str] = mapped_column(String(200), nullable=False)
    requestor: Mapped[str | None] = mapped_column(String(200))
    requested_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[StudyStatus] = mapped_column(
        Enum(StudyStatus), default=StudyStatus.draft, nullable=False
    )
    temporal_policy: Mapped[TemporalPolicy] = mapped_column(
        Enum(TemporalPolicy), default=TemporalPolicy.removed, nullable=False
    )
    expiration_alert_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project_key: Mapped["ProjectHashKey | None"] = relationship(back_populates="study")
    patient_mappings: Mapped[list["PatientMapping"]] = relationship(back_populates="study")
    dataset_manifests: Mapped[list["DatasetManifest"]] = relationship(back_populates="study")
    reidentification_requests: Mapped[list["ReidentificationRequest"]] = relationship(
        back_populates="study"
    )


class GlobalHashKey(Base):
    __tablename__ = "global_hash_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    key_material: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectHashKey(Base):
    __tablename__ = "project_hash_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id"), unique=True, nullable=False
    )
    key_material: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    study: Mapped["Study"] = relationship(back_populates="project_key")


class PatientMapping(Base):
    __tablename__ = "patient_mappings"
    __table_args__ = (
        UniqueConstraint("study_id", "mrn_hash", name="uq_study_mrn"),
        UniqueConstraint("study_id", "subject_id", name="uq_study_subject"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id"), nullable=False
    )
    mrn_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    mrn_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    study: Mapped["Study"] = relationship(back_populates="patient_mappings")
    accession_mappings: Mapped[list["AccessionMapping"]] = relationship(
        back_populates="patient_mapping"
    )


class DatasetManifest(Base):
    __tablename__ = "dataset_manifests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id"), nullable=False
    )
    global_hash_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("global_hash_keys.id"), nullable=False
    )
    global_key_version: Mapped[int] = mapped_column(Integer, nullable=False)
    dataset_type: Mapped[DatasetType] = mapped_column(
        Enum(DatasetType), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    record_count: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    study: Mapped["Study"] = relationship(back_populates="dataset_manifests")
    global_hash_key: Mapped["GlobalHashKey"] = relationship()
    accession_mappings: Mapped[list["AccessionMapping"]] = relationship(
        back_populates="dataset_manifest"
    )


class AccessionMapping(Base):
    __tablename__ = "accession_mappings"
    __table_args__ = (
        UniqueConstraint("study_id", "accession_hash", name="uq_study_accession"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_mapping_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patient_mappings.id"), nullable=False
    )
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id"), nullable=False
    )
    dataset_manifest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_manifests.id"), nullable=False
    )
    accession_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    accession_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    patient_mapping: Mapped["PatientMapping"] = relationship(
        back_populates="accession_mappings"
    )
    study: Mapped["Study"] = relationship()
    dataset_manifest: Mapped["DatasetManifest"] = relationship(
        back_populates="accession_mappings"
    )


class ReidentificationRequest(Base):
    __tablename__ = "reidentification_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id"), nullable=False
    )
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ReidentificationStatus] = mapped_column(
        Enum(ReidentificationStatus), default=ReidentificationStatus.pending, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[str | None] = mapped_column(String(200))

    study: Mapped["Study"] = relationship(back_populates="reidentification_requests")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(100))
    detail: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(45))
