# Stroke Core–Penumbra Backend

FastAPI prototype with doctor and pathologist accounts, one-to-one assignment, DICOM ZIP uploads, an external NPZ model contract, and shared scan results. The mock segmentation is deterministic and is for software testing only.

## Local setup

From `backend/`, install dependencies and configure `.env`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Set DATABASE_URL and JWT_SECRET. PostgreSQL is recommended; SQLite also works locally.
python -m alembic upgrade head
```

Start PostgreSQL, then run the mock model service in one terminal and the backend in another:

```powershell
python -m uvicorn mock_model.main:app --host 127.0.0.1 --port 8001
python -m uvicorn app.main:app --reload
```

The backend uses `MODEL_API_URL` to call the model service. To use the real model, point it at a service implementing `POST /predict` with a ZIP `file` multipart field and an NPZ binary response.

Run tests with `python -m pytest -q`.

## Account and assignment flow

Create a doctor first, then assign a pathologist by providing the doctor's account ID during pathologist signup. A doctor and pathologist can only be assigned to one another once.

```json
{"name":"Dr Example","email":"doctor@example.com","password":"password123","role":"doctor"}
```

```json
{"name":"Pathologist Example","email":"path@example.com","password":"password123","role":"pathologist","doctor_id":"<doctor-account-id>"}
```

Login at `POST /api/auth/login`; send its bearer token on protected requests. `GET /api/auth/me` returns account role and assignment.

## Upload a patient scan

`POST /api/scans` accepts multipart fields `patient_id`, `scan_type` (`CT` or `MRI`), and `file` (ZIP containing `.dcm` files). Upload performs extraction, DICOM validation and ordering, model request, NPZ validation, and volume calculation in one request.

```powershell
curl.exe -X POST http://localhost:8000/api/scans `
  -H "Authorization: Bearer $TOKEN" `
  -F "patient_id=P001" -F "scan_type=CT" -F "file=@stroke_scan.zip"
```

Example completed response:

```json
{
  "scan_id":"<scan-id>","patient_id":"P001","status":"completed","scan_type":"CT",
  "total_slices":2,"healthy_volume":825,"penumbra_volume":825,"core_volume":750,
  "mismatch_volume":75,"mismatch_ratio":1.1,"average_brain_height":150,
  "per_slice_height":75,"result_file_url":"/api/scans/<scan-id>/result-file",
  "slices_url":"/api/scans/<scan-id>/slices"
}
```

Volumes follow the requested prototype calculation: label pixel counts multiplied by `AVERAGE_BRAIN_HEIGHT_MM / slice_count`. Values are pixel-count·mm, not clinical physical volumes. Label values are 0 healthy, 1 penumbra, 2 core. A zero core volume yields a null mismatch ratio.

Pathologists can list their scans at `GET /api/pathologist/scans`. Doctors can list assigned scans at `GET /api/doctor/scans`. Both roles can access authorized scan details, `GET /api/scans/{scan_id}/result-file`, original DICOM slices, and derived PNG core/penumbra masks. No separate analyze endpoint is used.

## Storage and configuration

The original ZIP, extracted DICOM files, and `result.npz` are stored under `UPLOAD_DIR/<scan_id>/`. PostgreSQL stores paths and analysis metadata, not NPZ bytes. Existing legacy scans are migrated as failed records because their previous image-based analysis files are not NPZ results.

Important settings are in `.env.example`: `DATABASE_URL`, `JWT_SECRET`, `MODEL_API_URL`, `UPLOAD_DIR`, `MAX_UPLOAD_MB`, and `AVERAGE_BRAIN_HEIGHT_MM`.
