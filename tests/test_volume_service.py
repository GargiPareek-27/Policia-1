import numpy as np

from app.services.volume_service import calculate_volumes


def test_labels_and_slice_height_follow_prototype_formula():
    segmentation = np.array([[[0, 1], [2, 0]], [[1, 2], [0, 1]]], dtype=np.uint8)
    result = calculate_volumes(segmentation, 120)
    assert result.per_slice_height == 60
    assert result.healthy_volume == 180
    assert result.penumbra_volume == 180
    assert result.core_volume == 120
    assert result.mismatch_volume == 60
    assert result.mismatch_ratio == 1.5


def test_zero_core_has_no_ratio_or_division_error():
    result = calculate_volumes(np.zeros((2, 2, 2), dtype=np.uint8), 120)
    assert result.core_volume == 0
    assert result.penumbra_volume == 0
    assert result.mismatch_ratio is None
