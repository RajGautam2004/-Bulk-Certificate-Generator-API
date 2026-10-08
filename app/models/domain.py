import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"

class CertificateStatus(str, enum.Enum):
    PENDING = "PENDING"
    GENERATED = "GENERATED"
    FAILED = "FAILED"

class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_name: Mapped[str] = mapped_column(String, nullable=False)
    certificate_title: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=False)
    total_recipients: Mapped[int] = mapped_column(Integer, default=0)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    successful_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.QUEUED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    certificates: Mapped[List["Certificate"]] = relationship("Certificate", back_populates="job", cascade="all, delete-orphan")

    @property
    def progress_percentage(self) -> float:
        if self.total_recipients == 0:
            return 0.0
        return round((self.processed_count / self.total_recipients) * 100, 2)

class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("generation_jobs.id"), index=True)
    recipient_name: Mapped[str] = mapped_column(String, nullable=False)
    recipient_email: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[CertificateStatus] = mapped_column(Enum(CertificateStatus), default=CertificateStatus.PENDING)
    file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    job: Mapped["GenerationJob"] = relationship("GenerationJob", back_populates="certificates")
