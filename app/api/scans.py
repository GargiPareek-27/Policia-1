from pathlib import Path
from io import BytesIO
import logging
from uuid import uuid4

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from PIL import Image
import pydicom
from sqlalchemy.orm import Session

from app.api.deps import current_doctor, current_pathologist, current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.scan import Patient, Scan, ScanSlice
from app.models.user import User
from app.services.scan_service import accessible_scan, analyze_scan
from app.services.volume_service import load_segmentation
from app.utils.file_utils import ingest_upload

router = APIRouter(tags=["scans"])
log = logging.getLogger(__name__)
pathologist_router = APIRouter(prefix="/pathologist", tags=["pathologist"])
doctor_router = APIRouter(prefix="/doctor", tags=["doctor"])


def scan_payload(scan: Scan):
    return {
        "scan_id": scan.id,
        "patient_id": scan.patient.patient_identifier,
        "status": scan.status,
        "scan_type": scan.scan_type,
        "total_slices": scan.total_slices,
        "healthy_volume": scan.healthy_volume,
        "penumbra_volume": scan.penumbra_volume,
        "core_volume": scan.core_volume,
        "mismatch_volume": scan.mismatch_volume,
        "mismatch_ratio": scan.mismatch_ratio,
        "average_brain_height": scan.average_brain_height,
        "per_slice_height": scan.per_slice_height,
        "created_at": scan.created_at,
        "result_file_url": f"/api/scans/{scan.id}/result-file" if scan.result_npz_path else None,
        "slices_url": f"/api/scans/{scan.id}/slices",
    }


@router.post("/scans", status_code=201)
async def upload_scan(
    patient_id: str = Form(..., min_length=1, max_length=120),
    scan_type: str = Form(...),
    file: UploadFile = File(..., description="ZIP archive containing a DICOM series (.dcm files)"),
    db: Session = Depends(get_db),
    pathologist: User = Depends(current_pathologist),
):
    scan_type = scan_type.upper()
    if scan_type not in {"CT", "MRI"}:
        raise HTTPException(422, "scan_type must be CT or MRI")
    patient_id = patient_id.strip()
    if not patient_id:
        raise HTTPException(422, "patient_id must not be empty")

    patient = db.query(Patient).filter_by(created_by_pathologist_id=pathologist.id, patient_identifier=patient_id).first()
    if not patient:
        patient = Patient(patient_identifier=patient_id, created_by_pathologist_id=pathologist.id)
        db.add(patient)
        db.flush()
    scan_id = str(uuid4())
    source_path = str((Path(settings.upload_dir).resolve() / scan_id / "source.zip"))
    scan = Scan(id=scan_id, patient=patient, pathologist_id=pathologist.id,
                original_filename=Path(file.filename or "scan.zip").name[:255],
                source_zip_path=source_path, scan_type=scan_type, status="processing")
    db.add(scan)
    db.commit()
    db.refresh(scan)

    try:
        _, records = await ingest_upload(file, scan.id)
        scan.total_slices = len(records)
        for index, (path, spacing) in enumerate(records):
            sx, sy, thickness = spacing if spacing else (None, None, None)
            db.add(ScanSlice(scan_id=scan.id, slice_index=index, original_image_path=path,
                             pixel_spacing_x=sx, pixel_spacing_y=sy, slice_thickness=thickness))
        db.commit()
        await analyze_scan(db, scan)
    except ValueError as exc:
        db.rollback()
        failed = db.get(Scan, scan.id)
        if failed:
            failed.status = "failed"
            db.commit()
        raise HTTPException(400, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Scan upload failed for scan %s", scan.id)
        db.rollback()
        failed = db.get(Scan, scan.id)
        if failed:
            failed.status = "failed"
            db.commit()
        raise HTTPException(500, "Scan upload failed") from exc
    return scan_payload(scan)


@pathologist_router.get("/scans")
def pathologist_scans(db: Session = Depends(get_db), pathologist: User = Depends(current_pathologist)):
    scans = db.query(Scan).filter_by(pathologist_id=pathologist.id).order_by(Scan.created_at.desc()).all()
    return {"scans": [scan_payload(scan) for scan in scans]}


@doctor_router.get("/scans")
def doctor_scans(db: Session = Depends(get_db), doctor: User = Depends(current_doctor)):
    if not doctor.pathologist:
        return {"scans": []}
    scans = db.query(Scan).filter_by(pathologist_id=doctor.pathologist.id).order_by(Scan.created_at.desc()).all()
    return {"scans": [scan_payload(scan) for scan in scans]}


@doctor_router.get("/scans/{scan_id}")
def doctor_scan(scan_id: str, db: Session = Depends(get_db), doctor: User = Depends(current_doctor)):
    return scan_payload(accessible_scan(db, scan_id, doctor))


@router.get("/scans/{scan_id}")
def get_scan(scan_id: str, db: Session = Depends(get_db), account: User = Depends(current_user)):
    return scan_payload(accessible_scan(db, scan_id, account))


@router.get("/scans/{scan_id}/result-file")
def result_file(scan_id: str, db: Session = Depends(get_db), account: User = Depends(current_user)):
    scan = accessible_scan(db, scan_id, account)
    if scan.status != "completed" or not scan.result_npz_path or not Path(scan.result_npz_path).is_file():
        raise HTTPException(404, "Segmentation result not found")
    return FileResponse(scan.result_npz_path, media_type="application/octet-stream", filename=f"{scan.id}.npz")


@router.get("/scans/{scan_id}/slices")
def slices(scan_id: str, db: Session = Depends(get_db), account: User = Depends(current_user)):
    scan = accessible_scan(db, scan_id, account)
    return {"scan_id": scan.id, "total_slices": scan.total_slices, "slices": [
        {"index": row.slice_index,
         "original_url": f"/api/scans/{scan.id}/slices/{row.slice_index}/original",
         "core_mask_url": f"/api/scans/{scan.id}/slices/{row.slice_index}/core-mask",
         "penumbra_mask_url": f"/api/scans/{scan.id}/slices/{row.slice_index}/penumbra-mask"}
        for row in scan.slices]}


@router.get("/scans/{scan_id}/slices/{slice_index}/original")
def original_slice(scan_id: str, slice_index: int, db: Session = Depends(get_db), account: User = Depends(current_user)):
    scan = accessible_scan(db, scan_id, account)
    row = next((item for item in scan.slices if item.slice_index == slice_index), None)
    if not row or not Path(row.original_image_path).is_file():
        raise HTTPException(404, "Slice not found")
    try:
        dataset = pydicom.dcmread(row.original_image_path)
        pixels = np.asarray(dataset.pixel_array)
        if pixels.ndim != 2 or not np.issubdtype(pixels.dtype, np.number) or not np.isfinite(pixels).all():
            raise ValueError("Unsupported DICOM pixel array")
        minimum, maximum = float(pixels.min()), float(pixels.max())
        if maximum > minimum:
            display_pixels = np.rint((pixels.astype(np.float64) - minimum) * (255.0 / (maximum - minimum))).astype(np.uint8)
        else:
            display_pixels = np.zeros(pixels.shape, dtype=np.uint8)
        if getattr(dataset, "PhotometricInterpretation", "") == "MONOCHROME1":
            display_pixels = 255 - display_pixels
    except Exception as exc:
        raise HTTPException(422, "DICOM slice pixels could not be converted to PNG") from exc
    buffer = BytesIO()
    Image.fromarray(display_pixels).save(buffer, format="PNG")
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="image/png")


def mask_response(scan: Scan, slice_index: int, label: int):
    if scan.status != "completed" or not scan.result_npz_path:
        raise HTTPException(404, "Segmentation result not found")
    segmentation = load_segmentation(scan.result_npz_path, scan.total_slices)
    if not 0 <= slice_index < scan.total_slices:
        raise HTTPException(404, "Slice not found")
    buffer = BytesIO()
    Image.fromarray(np.where(segmentation[:, :, slice_index] == label, 255, 0).astype(np.uint8)).save(buffer, format="PNG")
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="image/png")


@router.get("/scans/{scan_id}/slices/{slice_index}/core-mask")
def core_mask(scan_id: str, slice_index: int, db: Session = Depends(get_db), account: User = Depends(current_user)):
    return mask_response(accessible_scan(db, scan_id, account), slice_index, 2)


@router.get("/scans/{scan_id}/slices/{slice_index}/penumbra-mask")
def penumbra_mask(scan_id: str, slice_index: int, db: Session = Depends(get_db), account: User = Depends(current_user)):
    return mask_response(accessible_scan(db, scan_id, account), slice_index, 1)
