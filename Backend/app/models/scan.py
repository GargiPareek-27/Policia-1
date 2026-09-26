import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (UniqueConstraint("created_by_pathologist_id", "patient_identifier", name="uq_patient_pathologist_identifier"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_identifier: Mapped[str] = mapped_column(String(120), nullable=False)
    created_by_pathologist_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    pathologist = relationship("User", back_populates="patients")
    scans = relationship("Scan", back_populates="patient")


class Scan(Base):
    __tablename__ = "scans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False)
    pathologist_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_zip_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    result_npz_path: Mapped[str | None] = mapped_column(String(1024))
    scan_type: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="processing", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    total_slices: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    healthy_volume: Mapped[float | None] = mapped_column(Float)
    penumbra_volume: Mapped[float | None] = mapped_column(Float)
    core_volume: Mapped[float | None] = mapped_column(Float)
    mismatch_volume: Mapped[float | None] = mapped_column(Float)
    mismatch_ratio: Mapped[float | None] = mapped_column(Float)
    average_brain_height: Mapped[float | None] = mapped_column(Float)
    per_slice_height: Mapped[float | None] = mapped_column(Float)

    patient = relationship("Patient", back_populates="scans")
    pathologist = relationship("User", back_populates="scans")
    slices = relationship("ScanSlice", back_populates="scan", cascade="all, delete-orphan", order_by="ScanSlice.slice_index")


class ScanSlice(Base):
    __tablename__ = "scan_slices"
    __table_args__ = (UniqueConstraint("scan_id", "slice_index"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), index=True)
    slice_index: Mapped[int] = mapped_column(Integer, nullable=False)
    original_image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    pixel_spacing_x: Mapped[float | None] = mapped_column(Float)
    pixel_spacing_y: Mapped[float | None] = mapped_column(Float)
    slice_thickness: Mapped[float | None] = mapped_column(Float)
    scan = relationship("Scan", back_populates="slices")
