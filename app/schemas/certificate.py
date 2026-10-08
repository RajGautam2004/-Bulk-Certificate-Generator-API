from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.domain import CertificateStatus

class CertificateBase(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr

class CertificateCreate(CertificateBase):
    pass

class CertificateResponse(BaseModel):
    id: int
    job_id: int
    name: str = Field(validation_alias='recipient_name')
    email: EmailStr = Field(validation_alias='recipient_email')
    status: CertificateStatus
    file_path: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
