from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import FileResponse
from typing import List
import os

from app.core.database import get_db, get_db_factory
from app.schemas.job import JobCreate, JobResponse, JobDetailResponse
from app.schemas.certificate import CertificateResponse
from app.services.job_service import create_job, get_job, get_jobs, process_job
from app.models.domain import Certificate
from sqlalchemy import select

router = APIRouter()

@router.post("/jobs", response_model=JobResponse, status_code=201)
async def create_generation_job(
    job_in: JobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    db_factory = Depends(get_db_factory)
):
    job = await create_job(db, job_in)
    
    background_tasks.add_task(process_job, job.id, db_factory)
    
    return job

@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    jobs = await get_jobs(db, skip=skip, limit=limit)
    return jobs

@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job_details(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/jobs/{job_id}/certificates", response_model=List[CertificateResponse])
async def get_job_certificates(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.certificates

@router.get("/certificates/{cert_id}/download")
async def download_certificate(cert_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Certificate).where(Certificate.id == cert_id))
    cert = result.scalar_one_or_none()
    
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
        
    if not cert.file_path or not os.path.exists(cert.file_path):
        raise HTTPException(status_code=404, detail="Certificate file not found or not generated yet")
        
    return FileResponse(
        path=cert.file_path, 
        filename=os.path.basename(cert.file_path),
        media_type="application/pdf"
    )
