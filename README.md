# Bulk Certificate Generator

## 1. Project Overview
The Bulk Certificate Generator is a robust, asynchronous backend application that automates the mass generation of personalized PDF certificates for events. Built with Python and FastAPI, it scales to handle bulk jobs asynchronously, tracks detailed progress, handles individual generation failures gracefully without stopping entire batches, and provides immediate endpoint feedback.

## 2. Architecture
The system employs an event-driven, background processing architecture:

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI Router
    participant DB as PostgreSQL
    participant Worker as BackgroundTasks
    participant Disk as File System

    Client->>API: POST /api/v1/jobs
    API->>DB: Save Job (QUEUED) & Certificates (PENDING)
    DB-->>API: Return Job ID
    API->>Worker: Enqueue Background Task
    API-->>Client: 201 Created (Job ID)
    
    rect rgb(30, 30, 30)
    Note over Worker,Disk: Asynchronous Processing
    Worker->>DB: Update Job Status (PROCESSING)
    loop Every Certificate
        Worker->>Disk: ReportLab: Generate PDF
        alt Success
            Worker->>DB: Status: GENERATED, Update Counts
        else Failure
            Worker->>DB: Status: FAILED, Log Error Reason
        end
    end
    Worker->>DB: Final Job Status (COMPLETED / FAILED)
    end
```

1. **API Layer**: Receives HTTP requests, validates input using Pydantic, instantly records jobs to the database, and returns a Job ID.
2. **Background Processing**: Delegates the heavy lifting of PDF generation to FastAPI `BackgroundTasks`. 
3. **Service Layer**: Orchestrates database transactions and PDF rendering per recipient, ensuring each operation is independently handled and gracefully caught if it fails.
4. **Data Layer**: Asynchronous PostgreSQL connectivity tracks job states and individual certificate records in real-time.

## 3. Technology Stack
- **Python 3.12+**
- **FastAPI**: Modern, fast web framework for APIs.
- **PostgreSQL**: Relational database for production data persistence.
- **SQLAlchemy 2.x**: Asynchronous ORM.
- **Pydantic v2**: Strict input validation and serialization.
- **Alembic**: Database migrations.
- **ReportLab**: PDF certificate template generation.
- **Pytest & HTTPX**: Comprehensive API testing.

## 4. Project Structure
The project follows a clean, modular structure separating concerns:
```text
.
├── alembic/              # Database migration configurations
├── app/
│   ├── api/              # API routers and endpoints (routes.py)
│   ├── core/             # Configuration and database setup
│   ├── models/           # SQLAlchemy domain models
│   ├── schemas/          # Pydantic schemas for request/response validation
│   ├── services/         # Business logic (job processing, generator)
│   └── main.py           # FastAPI application entry point
├── tests/                # Comprehensive test suite
├── certificates_output/  # Directory for generated PDF certificates
├── alembic.ini           # Alembic configuration
├── pytest.ini            # Pytest configuration
├── requirements.txt      # Project dependencies
└── README.md
```

## 5. Prerequisites
- Python 3.12 or higher
- PostgreSQL running locally or remotely (for production)
- (Optional) Docker for running Postgres easily

## 6. Environment Variables
You can configure the application using a `.env` file in the root directory. By default, it uses the following variables (fallback defaults exist if `.env` is absent):
```env
PROJECT_NAME="Bulk Certificate Generator"
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/certificates"
CERTIFICATE_OUTPUT_DIR="certificates_output"
```

## 7. PostgreSQL Database Setup
Ensure you have a PostgreSQL instance running. 
Create a database named `certificates` (or update `DATABASE_URL` appropriately).
```bash
# Example if using psql
CREATE DATABASE certificates;
```

## 8. Installation
```bash
# Create and activate a virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

## 9. Database Migration Commands
Initialize the database tables utilizing Alembic:
```bash
alembic upgrade head
```
*(Note: To generate a new migration after model changes, run `alembic revision --autogenerate -m "Message"`)*

## 10. How to Run the Application
Start the FastAPI server utilizing `uvicorn`:
```bash
uvicorn app.main:app --reload
```
The API will be accessible at `http://127.0.0.1:8000`. 
Interactive API documentation is automatically provided at `http://127.0.0.1:8000/docs`.

## 11. How to Run Tests
The test suite utilizes an isolated, in-memory SQLite database (`sqlite+aiosqlite:///:memory:`), completely independent of external dependencies and active PostgreSQL servers.
```bash
pytest
```

## 12. API Endpoints
- `GET /health` : Application health check
- `POST /api/v1/jobs` : Create a new bulk generation job
- `GET /api/v1/jobs` : List all generation jobs
- `GET /api/v1/jobs/{job_id}` : Get detailed job status and progress
- `GET /api/v1/jobs/{job_id}/certificates` : List all certificates tied to a job
- `GET /api/v1/certificates/{certificate_id}/download` : Download a generated PDF certificate

## 13. Example POST Request for Creating a Generation Job
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/v1/jobs' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "event_name": "AI Workshop 2026",
  "certificate_title": "Certificate of Participation",
  "date": "2026-10-07",
  "recipients": [
    {
      "name": "Alice Johnson",
      "email": "alice@example.com"
    },
    {
      "name": "Bob Smith",
      "email": "bob@example.com"
    }
  ]
}'
```

## 14. Example Response
```json
{
  "id": 1,
  "event_name": "AI Workshop 2026",
  "certificate_title": "Certificate of Participation",
  "date": "2026-10-07",
  "total_recipients": 2,
  "processed_count": 0,
  "successful_count": 0,
  "failed_count": 0,
  "status": "QUEUED",
  "progress_percentage": 0.0,
  "created_at": "2026-10-07T12:00:00Z",
  "updated_at": "2026-10-07T12:00:00Z"
}
```

## 15. How to Check Job Status
Track real-time progress of a bulk generation job:
```bash
curl -X 'GET' 'http://127.0.0.1:8000/api/v1/jobs/1' -H 'accept: application/json'
```

## 16. How to Retrieve Certificates
Retrieve all certificate states for a specific job:
```bash
curl -X 'GET' 'http://127.0.0.1:8000/api/v1/jobs/1/certificates' -H 'accept: application/json'
```

## 17. How to Download a Certificate
Download the generated PDF file (if successful) using its certificate ID:
```bash
curl -X 'GET' 'http://127.0.0.1:8000/api/v1/certificates/1/download' --output certificate.pdf
```

## 18. Bulk Processing Flow
1. **Creation**: Endpoint validates payload and inserts a `GenerationJob` (status `QUEUED`) alongside initial `Certificate` entries (`PENDING`) synchronously.
2. **Delegation**: The HTTP response is returned immediately to the client to prevent blocking. 
3. **Execution**: A FastAPI `BackgroundTask` takes over, changing job status to `PROCESSING`. It sequentially generates PDFs. 
4. **State Tracking**: `processed_count`, `successful_count`, and `failed_count` are incrementally updated in real-time inside the database.
5. **Completion**: Once all recipients are processed, the job shifts to `COMPLETED`, `COMPLETED_WITH_ERRORS`, or `FAILED`.

## 19. Failure Handling Strategy
Individual failure isolation is rigorously implemented. The generation logic for each recipient is encased in an independent `try...except` block within the background task loop. If a recipient's generation fails (e.g., due to invalid characters disrupting the PDF rendering engine), the specific certificate record stores the exact error message in its `failure_reason` column and transitions to `FAILED`. 
Critically, this caught exception does not halt the overarching loop; processing moves directly to the next recipient in the queue, ensuring all valid recipients receive their certificates.

## 20. Database Design
- **generation_jobs**: `id`, `event_name`, `certificate_title`, `date`, `total_recipients`, `processed_count`, `successful_count`, `failed_count`, `status`, `created_at`, `updated_at`.
- **certificates**: `id`, `job_id` (Foreign Key), `recipient_name`, `recipient_email`, `status`, `file_path`, `failure_reason`, `created_at`, `updated_at`.
- **Relationships**: `GenerationJob` has a one-to-many relationship with `Certificate`. Uses indexing on primary and foreign keys for efficient lookup and retrieval.

## 21. Certificate Generation Approach
We utilize **ReportLab** to procedurally draw the PDF. Instead of loading complex external templates, the application programmatically generates a premium, clean layout dynamically fitting the user's provided `recipient_name`, `certificate_title`, `event_name`, and `date`. This guarantees uniform reliability, strict single-template adherence, and high performance without relying on external file parsing tools. 

## 22. Background Processing Decision and Reasoning
**Decision**: Utilized FastAPI's built-in `BackgroundTasks`. 
**Reasoning**: Generating thousands of PDF files is an I/O heavy and CPU-intensive task. Processing synchronously would result in immediate HTTP timeout errors and block the web server thread, creating poor user experiences. `BackgroundTasks` provided a lightweight, framework-native solution to return an immediate `201 Created` while reliably generating assets. It sidesteps the complexity of heavy external message brokers (like Celery/Redis), which would add unnecessary overhead for the scope of this assignment. 

## 23. Important Design Decisions
- **Complete Decoupling**: File I/O (ReportLab operations) are decoupled into a dedicated `generator.py` service. The API routing strictly handles HTTP concerns.
- **In-Memory Test Database**: Tests automatically override the database factory to utilize `sqlite+aiosqlite:///:memory:`. This ensures test concurrency, cleanliness, and removes reliance on active PostgreSQL connections.
- **Enum Tracking**: Strict string Enums enforce state machines for certificates and jobs preventing invalid state transitions.

## 24. Limitations / Future Scope
- **Memory Scaling**: `BackgroundTasks` run on the same event loop. Massive multi-million record jobs would eventually block the main server. A future scope would migrate this to a distributed Celery/Redis architecture for true horizontal scaling.
- **Storage Strategy**: Currently relying on local file systems (`certificates_output`). Future implementation should integrate cloud bucket providers like AWS S3.
