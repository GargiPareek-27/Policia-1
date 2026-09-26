from io import BytesIO
from zipfile import BadZipFile, ZipFile

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response

app = FastAPI(title="Stroke segmentation mock model")


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    try:
        data = await file.read()
        with ZipFile(BytesIO(data)) as archive:
            count = sum(1 for entry in archive.infolist() if not entry.is_dir() and entry.filename.lower().endswith(".dcm"))
    except (BadZipFile, OSError):
        raise HTTPException(400, "Expected a ZIP containing DICOM slices")
    if count < 1:
        raise HTTPException(400, "ZIP contains no DICOM slices")
    segmentation = (np.arange(4 * 4 * count, dtype=np.uint8).reshape(4, 4, count) % 3)
    output = BytesIO()
    np.savez_compressed(output, segmentation=segmentation)
    return Response(output.getvalue(), media_type="application/octet-stream", headers={"Content-Disposition": "attachment; filename=segmentation.npz"})
