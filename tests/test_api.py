import pytest
import os
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

from app.services.job_service import process_job
from app.models.domain import JobStatus, CertificateStatus
from app.core.database import get_db_factory

pytestmark = pytest.mark.asyncio

async def test_health_check(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200

async def test_create_job_valid(async_client: AsyncClient):
    payload = {
        "event_name": "Test Event",
        "certificate_title": "Test Title",
        "date": "2026-10-07",
        "recipients": [{"name": "Alice", "email": "alice@example.com"}]
    }
    with patch("app.api.routes.BackgroundTasks.add_task") as mock_add_task:
        response = await async_client.post("/api/v1/jobs", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "QUEUED"
    assert data["total_recipients"] == 1

async def test_input_validation_missing_fields(async_client: AsyncClient):
    payload = {"event_name": "Event"}
    response = await async_client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

async def test_input_validation_empty_recipients(async_client: AsyncClient):
    payload = {
        "event_name": "Event",
        "certificate_title": "Title",
        "date": "2026-10-07",
        "recipients": []
    }
    response = await async_client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

async def test_input_validation_empty_recipient_name(async_client: AsyncClient):
    payload = {
        "event_name": "Event",
        "certificate_title": "Title",
        "date": "2026-10-07",
        "recipients": [{"name": "", "email": "alice@example.com"}]
    }
    response = await async_client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

async def test_input_validation_invalid_email(async_client: AsyncClient):
    payload = {
        "event_name": "Event",
        "certificate_title": "Title",
        "date": "2026-10-07",
        "recipients": [{"name": "Alice", "email": "invalid"}]
    }
    response = await async_client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

async def test_input_validation_invalid_date(async_client: AsyncClient):
    payload = {
        "event_name": "Event",
        "certificate_title": "Title",
        "date": "not-a-date",
        "recipients": [{"name": "Alice", "email": "alice@example.com"}]
    }
    response = await async_client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

async def test_certificate_generation_and_job_status(async_client: AsyncClient):
    payload = {
        "event_name": "Gen Event",
        "certificate_title": "Gen Title",
        "date": "2026-10-07",
        "recipients": [{"name": "Gen", "email": "gen@example.com"}]
    }
    
    with patch("app.api.routes.BackgroundTasks.add_task"):
        response = await async_client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["id"]

    from app.main import app
    db_factory = app.dependency_overrides.get(get_db_factory, get_db_factory)()
    await process_job(job_id, db_factory)

    job_res = await async_client.get(f"/api/v1/jobs/{job_id}")
    job_data = job_res.json()
    assert job_data["status"] == "COMPLETED"
    assert job_data["processed_count"] == 1
    assert job_data["successful_count"] == 1
    assert job_data["progress_percentage"] == 100.0

    certs_res = await async_client.get(f"/api/v1/jobs/{job_id}/certificates")
    certs = certs_res.json()
    assert len(certs) == 1
    assert certs[0]["status"] == "GENERATED"
    assert certs[0]["file_path"] is not None
    assert os.path.exists(certs[0]["file_path"])

async def test_individual_certificate_failure(async_client: AsyncClient):
    payload = {
        "event_name": "Fail Event",
        "certificate_title": "Fail Title",
        "date": "2026-10-07",
        "recipients": [
            {"name": "Valid", "email": "valid@example.com"},
            {"name": "Fail", "email": "fail@example.com"}
        ]
    }
    
    with patch("app.api.routes.BackgroundTasks.add_task"):
        response = await async_client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["id"]

    original_generate = __import__("app.services.generator", fromlist=["generate_pdf_certificate"]).generate_pdf_certificate

    def mock_generate(name, event, title, date, path):
        if name == "Fail":
            raise ValueError("Simulated failure")
        return original_generate(name, event, title, date, path)

    with patch("app.services.job_service.generate_pdf_certificate", side_effect=mock_generate):
        from app.main import app
        db_factory = app.dependency_overrides.get(get_db_factory, get_db_factory)()
        await process_job(job_id, db_factory)

    job_res = await async_client.get(f"/api/v1/jobs/{job_id}")
    job_data = job_res.json()
    assert job_data["status"] == "COMPLETED_WITH_ERRORS"
    assert job_data["total_recipients"] == 2
    assert job_data["processed_count"] == 2
    assert job_data["successful_count"] == 1
    assert job_data["failed_count"] == 1

    certs_res = await async_client.get(f"/api/v1/jobs/{job_id}/certificates")
    certs = certs_res.json()
    
    valid_cert = next(c for c in certs if c["name"] == "Valid")
    fail_cert = next(c for c in certs if c["name"] == "Fail")

    assert valid_cert["status"] == "GENERATED"
    assert os.path.exists(valid_cert["file_path"])

    assert fail_cert["status"] == "FAILED"
    assert "Simulated failure" in fail_cert["failure_reason"]

async def test_certificate_download(async_client: AsyncClient):
    payload = {
        "event_name": "Download Event",
        "certificate_title": "Title",
        "date": "2026-10-07",
        "recipients": [{"name": "Downloader", "email": "down@example.com"}]
    }
    
    with patch("app.api.routes.BackgroundTasks.add_task"):
        response = await async_client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["id"]

    from app.main import app
    db_factory = app.dependency_overrides.get(get_db_factory, get_db_factory)()
    await process_job(job_id, db_factory)

    certs_res = await async_client.get(f"/api/v1/jobs/{job_id}/certificates")
    cert_id = certs_res.json()[0]["id"]

    dl_response = await async_client.get(f"/api/v1/certificates/{cert_id}/download")
    assert dl_response.status_code == 200
    assert dl_response.headers["content-type"] == "application/pdf"

async def test_nonexistent_certificate_download(async_client: AsyncClient):
    dl_response = await async_client.get("/api/v1/certificates/9999/download")
    assert dl_response.status_code == 404

async def test_failed_certificate_download(async_client: AsyncClient):
    payload = {
        "event_name": "DL Fail Event",
        "certificate_title": "DL Fail Title",
        "date": "2026-10-07",
        "recipients": [{"name": "FailDownloader", "email": "fail@example.com"}]
    }
    
    with patch("app.api.routes.BackgroundTasks.add_task"):
        response = await async_client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["id"]

    def mock_generate(*args, **kwargs):
        raise ValueError("Simulated failure")

    with patch("app.services.job_service.generate_pdf_certificate", side_effect=mock_generate):
        from app.main import app
        db_factory = app.dependency_overrides.get(get_db_factory, get_db_factory)()
        await process_job(job_id, db_factory)

    certs_res = await async_client.get(f"/api/v1/jobs/{job_id}/certificates")
    cert_id = certs_res.json()[0]["id"]

    dl_response = await async_client.get(f"/api/v1/certificates/{cert_id}/download")
    assert dl_response.status_code == 404
