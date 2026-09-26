"""Prototype label-count × slice-height calculation (units: pixel-count·mm)."""
from dataclasses import dataclass

import numpy as np
from zipfile import BadZipFile


@dataclass(frozen=True)
class Volumes:
    healthy_volume: float
    penumbra_volume: float
    core_volume: float
    mismatch_volume: float
    mismatch_ratio: float | None
    average_brain_height: float
    per_slice_height: float


def load_segmentation(npz_path: str, expected_slices: int) -> np.ndarray:
    try:
        with np.load(npz_path, allow_pickle=False) as archive:
            if "segmentation" not in archive.files:
                raise ValueError("NPZ is missing the segmentation array")
            array = np.asarray(archive["segmentation"])
    except (OSError, ValueError, KeyError, BadZipFile, EOFError) as exc:
        raise ValueError("Model returned an invalid NPZ segmentation") from exc
    if array.ndim != 3 or array.shape[2] != expected_slices or array.shape[0] < 1 or array.shape[1] < 1:
        raise ValueError("Segmentation dimensions do not match the uploaded series")
    if not np.issubdtype(array.dtype, np.integer) or not set(np.unique(array)).issubset({0, 1, 2}):
        raise ValueError("Segmentation must contain integer labels 0, 1, and 2 only")
    return array.astype(np.uint8, copy=False)


def calculate_volumes(segmentation: np.ndarray, average_brain_height_mm: float) -> Volumes:
    if segmentation.ndim != 3 or segmentation.shape[2] < 1:
        raise ValueError("Segmentation must contain at least one 2D slice")
    if average_brain_height_mm <= 0:
        raise ValueError("Average brain height must be positive")
    count = segmentation.shape[2]
    slice_height = float(average_brain_height_mm) / count
    healthy = int(np.count_nonzero(segmentation == 0)) * slice_height
    penumbra = int(np.count_nonzero(segmentation == 1)) * slice_height
    core = int(np.count_nonzero(segmentation == 2)) * slice_height
    return Volumes(healthy, penumbra, core, penumbra - core, penumbra / core if core else None,
                   float(average_brain_height_mm), slice_height)
