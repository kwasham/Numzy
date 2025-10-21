**Project:** Numzy Backend (FastAPI + Clerk Auth + Async Receipt Processing)

**Goal:** Implement and refine the Phase 1 backend features that power the new receipt dashboard UI.

**Requirements:**

1. **Project Setup**
   - Ensure the project uses FastAPI with async endpoints.
   - Configure CORS to allow requests from the Next.js frontend (localhost:3000 and production domains).
   - Verify environment variables for:
     - `CLERK_SECRET_KEY` → used to validate Clerk JWTs.
     - `AWS_S3_BUCKET` or `LOCAL_UPLOAD_DIR` for receipt storage (pick one for now).

2. **Authentication Dependency**
   - Create a `get_current_user` dependency that:
     - Reads the `Authorization: Bearer <token>` header.
     - Validates the token using Clerk’s JWT verification endpoint.
     - Returns a user object `{ id, email }`.
   - Apply it to all `/receipts/*` routes.

3. **Routes to Implement**
   - `POST /receipts`
     - Accept multipart/form-data (`file: UploadFile`).
     - Validate content type (`image/*` or `application/pdf`) and max size (10 MB).
     - Save file to S3 or `/data/receipts/{user_id}/{uuid}.ext`.
     - Insert DB record:  
       ```python
       {
         "id": uuid4(),
         "user_id": current_user.id,
         "filename": file.filename,
         "status": "processing",
         "extraction_progress": 0,
         "audit_progress": 0,
         "created_at": datetime.utcnow()
       }
       ```
     - Kick off a background task (using Dramatiq, Celery, or asyncio.create_task) to simulate or perform extraction.
     - Return the new record JSON.

   - `GET /receipts/summary`
     - Query receipts by `user_id` ordered by `created_at DESC`.
     - Return key fields: id, filename, status, created_at, extraction_progress, audit_progress, merchant, total.

   - `GET /receipts/{id}`
     - Return the full record including `extracted_data` and `audit_decision`.
     - If status != "completed", return partial data + status.

   - `GET /receipts/{id}/download_url`
     - Generate a short-lived presigned S3 URL (or local file path link).

   - `POST /receipts/{id}/reprocess`
     - Reset `status` to "processing", zero out progress, enqueue new job.

   - `GET /receipts/events`
     - Implement Server-Sent Events to push updates when a receipt’s status changes.
     - Example event JSON:
       ```json
       { "id": "<uuid>", "status": "completed", "extraction_progress": 100, "audit_progress": 100 }
       ```

4. **Background Task Simulation**
   - Create a simple async task (`process_receipt`) that:
     - Waits 2-3 seconds,
     - Updates extraction_progress and audit_progress gradually,
     - Writes fake `extracted_data` and `audit_decision` JSON to DB,
     - Marks `status="completed"`.
   - Broadcast an event via an in-memory pub/sub (e.g. `asyncio.Queue` or `Broadcaster`).

5. **Database Layer**
   - Use SQLModel or SQLAlchemy ORM.
   - Models:  
     ```python
     class Receipt(SQLModel, table=True):
         id: UUID
         user_id: str
         filename: str
         status: str
         extraction_progress: int
         audit_progress: int
         extracted_data: dict | None
         audit_decision: dict | None
         created_at: datetime
         updated_at: datetime
     ```
   - Create CRUD helpers under `/services/receipts.py`.

6. **Error Handling**
   - Return structured errors (`{"error": "Invalid file type"}`) with correct status codes.
   - Use FastAPI’s `HTTPException`.
   - Log every upload, status change, and background error with timestamps.

7. **Testing**
   - Add sample cURL or pytest tests:
     ```bash
     curl -X POST -H "Authorization: Bearer <JWT>" -F "file=@sample.jpg" http://localhost:8000/receipts
     ```
   - Ensure responses conform to OpenAPI schema.

**Goal:** After running `uvicorn app.main:app`, the frontend can:
- Upload a receipt → immediately receive record with status = processing.
- Poll `/receipts/summary` → see it progressing toward completed.
- Open `/receipts/{id}` → view extracted_data and audit flags.
- Listen to `/receipts/events` → see live updates.
