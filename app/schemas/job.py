from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date
from app.models.domain import JobStatus
from app.schemas.certificate import CertificateCreate, CertificateResponse

class JobCreate(BaseModel):
    event_name: str = Field(..., min_length=1)
    certificate_title: str = Field(..., min_length=1)
    date: date
    recipients: List[CertificateCreate] = Field(..., min_length=1, max_length=1000)

class JobResponse(BaseModel):
    id: int
    event_name: str
    certificate_title: str
    date: date
    total_recipients: int
    processed_count: int
    successful_count: int
    failed_count: int
    status: JobStatus
    progress_percentage: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class JobDetailResponse(JobResponse):
    certificates: List[CertificateResponse]
