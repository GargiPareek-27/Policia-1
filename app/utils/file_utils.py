import shutil
from pathlib import Path, PurePosixPath, PureWindowsPath
from zipfile import BadZipFile, ZipFile

import pydicom
from fastapi import UploadFile

from app.core.config import settings


def _slice_order(dataset):
    """Return a spatially meaningful ordering key when DICOM metadata allows it."""
    position = getattr(dataset, "ImagePositionPatient", None)
    orientation = getattr(dataset, "ImageOrientationPatient", None)
    try:
        if position is not None and orientation is not None:
            row = [float(v) for v in orientation[:3]]
            column = [float(v) for v in orientation[3:6]]
            normal = (
                row[1] * column[2] - row[2] * column[1],
                row[2] * column[0] - row[0] * column[2],
                row[0] * column[1] - row[1] * column[0],
            )
            distance = sum(float(position[i]) * normal[i] for i in range(3))
            return (0, distance)
    except (TypeError, ValueError, IndexError):
        pass
    try:
        return (1, float(dataset.SliceLocation))
    except (AttributeError, TypeError, ValueError):
        pass
    try:
        return (2, float(dataset.InstanceNumber))
    except (AttributeError, TypeError, ValueError):
        return (3, 0.0)


async def ingest_upload(upload: UploadFile, scan_id: str) -> tuple[str, list[tuple[str, tuple[float, float, float] | None]]]:
    """Store the source ZIP and safely extract and validate its DICOM series."""
    name = Path(upload.filename or "scan.zip").name
    if Path(name).suffix.lower() != ".zip":
        raise ValueError("Upload must be a ZIP file")

    root = Path(settings.upload_dir).resolve() / scan_id
    root.mkdir(parents=True, exist_ok=True)
    target = root / "source.zip"
    size = 0
    try:
        with target.open("wb") as out:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_mb * 1024 * 1024:
                    raise ValueError("Upload exceeds configured size limit")
                out.write(chunk)

        if size == 0:
            raise ValueError("Uploaded ZIP is empty")

        extracted = root / "dicom"
        extracted.mkdir()
        candidates = []
        expanded = 0
        try:
            with ZipFile(target) as archive:
                members = archive.infolist()
                if not members:
                    raise ValueError("ZIP archive is empty")
                for item in members:
                    posix = PurePosixPath(item.filename)
                    windows = PureWindowsPath(item.filename)
                    if posix.is_absolute() or windows.is_absolute() or windows.drive or ".." in posix.parts or ".." in windows.parts:
                        raise ValueError("Unsafe path in ZIP archive")
                    if item.is_dir():
                        continue
                    # Ignore non-DICOM files; extract only files with the accepted extension.
                    if posix.suffix.lower() != ".dcm":
                        continue
                    expanded += item.file_size
                    if expanded > settings.max_upload_mb * 1024 * 1024:
                        raise ValueError("Expanded ZIP exceeds configured size limit")
                    destination = extracted.joinpath(*posix.parts)
                    if not destination.resolve().is_relative_to(extracted.resolve()):
                        raise ValueError("Unsafe path in ZIP archive")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(item) as source, destination.open("wb") as output:
                        shutil.copyfileobj(source, output)
                    candidates.append(destination)
        except BadZipFile as exc:
            raise ValueError("Invalid ZIP archive") from exc
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Failed to extract ZIP archive") from exc

        if not candidates:
            raise ValueError("ZIP archive contains no DICOM (.dcm) files")

        records = []
        for path in candidates:
            try:
                dataset = pydicom.dcmread(path, stop_before_pixels=True)
            except Exception as exc:
                raise ValueError("ZIP archive contains an invalid or corrupted DICOM file") from exc
            spacing = None
            try:
                pixel_spacing = [float(v) for v in dataset.PixelSpacing]
                thickness = float(getattr(dataset, "SliceThickness", 0))
                spacing = (pixel_spacing[0], pixel_spacing[1], thickness)
            except (AttributeError, TypeError, ValueError, IndexError):
                pass
            records.append((_slice_order(dataset), str(path), spacing))

        records.sort(key=lambda record: (record[0], record[1].casefold()))
        return str(root), [(path, spacing) for _, path, spacing in records]
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise
    finally:
        await upload.close()
