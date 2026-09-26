from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
import numpy as np
import httpx
from PIL import Image
from fastapi.testclient import TestClient
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from app.main import app
from mock_model.main import app as mock_model_app


def dicom_bytes(instance=1, z=0):
    stream = BytesIO()
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = generate_uid()
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.ImplementationClassUID = generate_uid()
    ds = FileDataset(None, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.InstanceNumber = instance
    ds.ImagePositionPatient = [0, 0, z]
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.Rows = 4
    ds.Columns = 4
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.PixelData = np.arange(16, dtype=np.uint16).reshape(4, 4).tobytes()
    ds.save_as(stream, enforce_file_format=True)
    return stream.getvalue()


def zip_bytes(files):
    stream = BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        for name, content in files:
            archive.writestr(name, content)
    stream.seek(0)
    return stream


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def account(client, role, email, doctor_id=None):
    response = client.post("/api/auth/signup", json={
        "name": role.title(), "email": email, "password": "password123", "role": role,
        **({"doctor_id": doctor_id} if doctor_id else {}),
    })
    assert response.status_code == 201, response.text
    token_response = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert token_response.status_code == 200
    return response.json(), {"Authorization": "Bearer " + token_response.json()["access_token"]}


@pytest.fixture
def mock_model(monkeypatch):
    real_async_client = httpx.AsyncClient

    def client_with_mock_model(*, base_url, timeout, **kwargs):
        return real_async_client(transport=httpx.ASGITransport(app=mock_model_app),
                                 base_url="http://mock-model", timeout=timeout, **kwargs)

    monkeypatch.setattr("app.services.model_client.httpx.AsyncClient", client_with_mock_model)


def upload(client, headers, content=None, filename="study.zip", patient_id="P001", scan_type="CT"):
    content = content or zip_bytes([("slice1.dcm", dicom_bytes())])
    return client.post("/api/scans", headers=headers,
                       data={"patient_id": patient_id, "scan_type": scan_type},
                       files={"file": (filename, content, "application/zip")})


def assert_png(response, expected_size=(4, 4)):
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    image = Image.open(BytesIO(response.content))
    image.load()
    assert image.size == expected_size
    return np.asarray(image)


def test_roles_assignment_login_and_invalid_role(client):
    rejected = client.post("/api/auth/signup", json={"name": "Bad", "email": "bad@example.com", "password": "password123", "role": "admin"})
    assert rejected.status_code == 422
    doctor, doctor_auth = account(client, "doctor", "doctor@example.com")
    pathologist, path_auth = account(client, "pathologist", "path@example.com", doctor["id"])
    assert pathologist["assigned_doctor_id"] == doctor["id"]
    assert client.get("/api/auth/me", headers=path_auth).json()["role"] == "pathologist"
    duplicate, _ = account(client, "doctor", "doctor2@example.com")
    response = client.post("/api/auth/signup", json={"name": "Other", "email": "path2@example.com", "password": "password123", "role": "pathologist", "doctor_id": doctor["id"]})
    assert response.status_code == 409


def test_combined_upload_mock_analysis_and_shared_doctor_result(client, mock_model):
    doctor, doctor_auth = account(client, "doctor", "doctor@example.com")
    pathologist, path_auth = account(client, "pathologist", "path@example.com", doctor["id"])
    response = upload(client, path_auth, zip_bytes([("slice2.dcm", dicom_bytes(2, 2)), ("slice1.dcm", dicom_bytes(1, 1))]))
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["patient_id"] == "P001" and result["status"] == "completed"
    assert result["total_slices"] == 2
    assert result["average_brain_height"] == 150
    assert result["per_slice_height"] == 75
    assert result["healthy_volume"] == 825
    assert result["penumbra_volume"] == 825
    assert result["core_volume"] == 750
    assert result["mismatch_volume"] == 75
    assert result["mismatch_ratio"] == pytest.approx(1.1)
    assert client.get("/api/doctor/scans", headers=doctor_auth).json()["scans"][0]["scan_id"] == result["scan_id"]
    assert client.get(f"/api/scans/{result['scan_id']}", headers=path_auth).json() == client.get(f"/api/doctor/scans/{result['scan_id']}", headers=doctor_auth).json()
    npz = client.get(result["result_file_url"], headers=doctor_auth)
    assert npz.status_code == 200 and npz.content.startswith(b"PK\x03\x04")
    core_response = client.get(f"/api/scans/{result['scan_id']}/slices/0/core-mask", headers=doctor_auth)
    penumbra_response = client.get(f"/api/scans/{result['scan_id']}/slices/0/penumbra-mask", headers=doctor_auth)
    original_response = client.get(f"/api/scans/{result['scan_id']}/slices/0/original", headers=doctor_auth)
    core = assert_png(core_response)
    penumbra = assert_png(penumbra_response)
    assert_png(original_response)
    expected_labels = (np.arange(4 * 4 * 2, dtype=np.uint8).reshape(4, 4, 2)[:, :, 0] % 3)
    assert np.array_equal(core, np.where(expected_labels == 2, 255, 0).astype(np.uint8))
    assert np.array_equal(penumbra, np.where(expected_labels == 1, 255, 0).astype(np.uint8))
    assert client.get(f"/api/scans/{result['scan_id']}/slices/2/core-mask", headers=doctor_auth).status_code == 404
    assert client.get(f"/api/scans/{result['scan_id']}/slices/2/penumbra-mask", headers=doctor_auth).status_code == 404
    assert client.get(f"/api/scans/{result['scan_id']}/slices/2/original", headers=doctor_auth).status_code == 404
    assert client.get(f"/api/scans/{result['scan_id']}/slices", headers=doctor_auth).headers["content-type"].startswith("application/json")
    assert len(client.get("/api/pathologist/scans", headers=path_auth).json()["scans"]) == 1


def test_upload_validation_and_role_authorization(client, mock_model):
    doctor, doctor_auth = account(client, "doctor", "doctor@example.com")
    _, path_auth = account(client, "pathologist", "path@example.com", doctor["id"])
    assert upload(client, doctor_auth).status_code == 403
    assert upload(client, path_auth, BytesIO(b"not zip"), "scan.dcm").status_code == 400
    assert upload(client, path_auth, zip_bytes([])).status_code == 400
    assert upload(client, path_auth, zip_bytes([("notes.txt", b"not dicom")])).status_code == 400
    assert upload(client, path_auth, zip_bytes([("../outside.dcm", dicom_bytes())])).status_code == 400
    assert client.post("/api/scans", data={"patient_id": "P1", "scan_type": "CT"}, files={"file": ("scan.zip", zip_bytes([]))}).status_code == 401


def test_scan_and_result_ownership(client, mock_model):
    doctor1, auth_doctor1 = account(client, "doctor", "doc1@example.com")
    doctor2, auth_doctor2 = account(client, "doctor", "doc2@example.com")
    _, path1 = account(client, "pathologist", "path1@example.com", doctor1["id"])
    _, path2 = account(client, "pathologist", "path2@example.com", doctor2["id"])
    scan = upload(client, path1).json()["scan_id"]
    assert client.get(f"/api/scans/{scan}", headers=path2).status_code == 404
    assert client.get(f"/api/scans/{scan}/result-file", headers=auth_doctor2).status_code == 404
    assert client.get(f"/api/scans/{scan}/slices/0/original", headers=auth_doctor2).status_code == 404
    assert client.get(f"/api/scans/{scan}/slices/0/core-mask", headers=auth_doctor2).status_code == 404
    assert client.get(f"/api/scans/{scan}/slices/0/penumbra-mask", headers=auth_doctor2).status_code == 404
    assert client.get("/api/doctor/scans", headers=auth_doctor2).json()["scans"] == []
    assert client.get(f"/api/scans/{scan}/result-file", headers=auth_doctor1).status_code == 200


def test_invalid_npz_marks_scan_failed(client, monkeypatch):
    async def bad_predict(_self, _source_zip, result_path):
        Path(result_path).parent.mkdir(parents=True, exist_ok=True)
        Path(result_path).write_bytes(b"PK\x03\x04not a valid npz")
        return result_path

    monkeypatch.setattr("app.services.scan_service.ModelClient.predict", bad_predict)
    doctor, _ = account(client, "doctor", "doctor@example.com")
    _, auth = account(client, "pathologist", "path@example.com", doctor["id"])
    response = upload(client, auth)
    assert response.status_code == 502, response.text
    assert client.get("/api/pathologist/scans", headers=auth).json()["scans"][0]["status"] == "failed"


def test_mock_model_api_returns_npz(client):
    with TestClient(mock_model_app) as mock_client:
        response = mock_client.post("/predict", files={"file": ("scan.zip", zip_bytes([("a.dcm", dicom_bytes()), ("b.dcm", dicom_bytes(2))]), "application/zip")})
    assert response.status_code == 200 and response.content.startswith(b"PK\x03\x04")
    with np.load(BytesIO(response.content), allow_pickle=False) as archive:
        segmentation = archive["segmentation"]
    assert segmentation.shape == (4, 4, 2)
    assert set(np.unique(segmentation)) == {0, 1, 2}
