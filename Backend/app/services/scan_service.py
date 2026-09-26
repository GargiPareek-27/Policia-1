import logging
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.scan import Scan
from app.services.model_client import ModelClient
from app.services.volume_service import calculate_volumes, load_segmentation

log = logging.getLogger(__name__)


async def analyze_scan(db: Session, scan: Scan) -> Scan:
    """Run model, validate NPZ, calculate prototype volumes, and persist one result."""
    scan.status = "processing"
    db.commit()
    result_path = Path(settings.upload_dir).resolve() / scan.id / "result.npz"
    try:
        scan.result_npz_path = await ModelClient().predict(scan.source_zip_path, str(result_path))
        segmentation = load_segmentation(scan.result_npz_path, scan.total_slices)
        volumes = calculate_volumes(segmentation, settings.average_brain_height_mm)
        scan.healthy_volume = volumes.healthy_volume
        scan.penumbra_volume = volumes.penumbra_volume
        scan.core_volume = volumes.core_volume
        scan.mismatch_volume = volumes.mismatch_volume
        scan.mismatch_ratio = volumes.mismatch_ratio
        scan.average_brain_height = volumes.average_brain_height
        scan.per_slice_height = volumes.per_slice_height
        scan.status = "completed"
        db.commit()
        db.refresh(scan)
        return scan
    except Exception as exc:
        db.rollback()
        current = db.get(Scan, scan.id)
        if current:
            current.status = "failed"
            current.result_npz_path = None
            db.commit()
        try:
            result_path.unlink(missing_ok=True)
        except OSError:
            log.warning("Could not remove invalid result file for scan %s", scan.id)
        log.exception("Scan analysis failed for scan %s", scan.id)
        raise HTTPException(502, "Scan analysis failed") from exc


def accessible_scan(db: Session, scan_id: str, account) -> Scan:
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if account.role == "pathologist" and scan.pathologist_id == account.id:
        return scan
    if account.role == "doctor" and scan.pathologist.assigned_doctor_id == account.id:
        return scan
    raise HTTPException(404, "Scan not found")
