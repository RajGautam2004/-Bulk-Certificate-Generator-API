import asyncio
import os
import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.domain import GenerationJob, Certificate, JobStatus, CertificateStatus
from app.schemas.job import JobCreate
from app.schemas.certificate import CertificateCreate
from app.services.generator import generate_pdf_certificate
from app.core.config import settings

async def create_job(db: AsyncSession, job_data: JobCreate) -> GenerationJob:
    job = GenerationJob(
        event_name=job_data.event_name,
        certificate_title=job_data.certificate_title,
        date=str(job_data.date),
        total_recipients=len(job_data.recipients),
        status=JobStatus.QUEUED
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    certificates = []
    for recipient in job_data.recipients:
        cert = Certificate(
            job_id=job.id,
            recipient_name=recipient.name,
            recipient_email=recipient.email,
            status=CertificateStatus.PENDING
        )
        certificates.append(cert)
    
    db.add_all(certificates)
    await db.commit()
    
    return job

async def get_job(db: AsyncSession, job_id: int) -> GenerationJob | None:
    result = await db.execute(
        select(GenerationJob).options(selectinload(GenerationJob.certificates)).where(GenerationJob.id == job_id)
    )
    return result.scalar_one_or_none()

async def get_jobs(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[GenerationJob]:
    result = await db.execute(select(GenerationJob).offset(skip).limit(limit))
    return list(result.scalars().all())

async def process_certificate(db: AsyncSession, cert: Certificate, job: GenerationJob):
    try:
        filename = f"{uuid.uuid4()}_{cert.id}.pdf"
        output_path = os.path.join(settings.CERTIFICATE_OUTPUT_DIR, filename)
        
        await asyncio.to_thread(
            generate_pdf_certificate, 
            cert.recipient_name, 
            job.event_name,
            job.certificate_title,
            job.date,
            output_path
        )
        
        cert.status = CertificateStatus.GENERATED
        cert.file_path = output_path
    except Exception as e:
        cert.status = CertificateStatus.FAILED
        cert.failure_reason = str(e)
        
    db.add(cert)
    await db.commit()

async def process_job(job_id: int, db_session_factory):
    async with db_session_factory() as db:
        job = await get_job(db, job_id)
        if not job:
            return
            
        job.status = JobStatus.PROCESSING
        db.add(job)
        await db.commit()

        for cert in job.certificates:
            await process_certificate(db, cert, job)
            
            job.processed_count += 1
            if cert.status == CertificateStatus.GENERATED:
                job.successful_count += 1
            else:
                job.failed_count += 1
                
            db.add(job)
            await db.commit()
            
        if job.failed_count == job.total_recipients:
            job.status = JobStatus.FAILED
        elif job.failed_count > 0:
            job.status = JobStatus.COMPLETED_WITH_ERRORS
        else:
            job.status = JobStatus.COMPLETED
            
        db.add(job)
        await db.commit()
