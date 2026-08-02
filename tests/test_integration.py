"""Integration coverage for the full synthetic optical round trip."""

import cv2
import numpy as np

from optical_airgap_lab.decoding import decode_expected_payload
from optical_airgap_lab.encoding import create_qr_mask
from optical_airgap_lab.grid_decoding import reconstruct_frame_filling_capture
from optical_airgap_lab.rendering import render_reference_image
from optical_airgap_lab.simulation import simulate_camera_capture


def test_low_contrast_round_trip_through_simulated_camera() -> None:
    """Recover the fixed identifier after perspective, noise, blur, and JPEG compression."""
    payload = "LAB-001"
    qr_mask = create_qr_mask(payload, 3, 4, "M")
    transmitter = render_reference_image(qr_mask, 1200, 900, 18, 248, 12)
    capture = simulate_camera_capture(transmitter, 1600, 1200, 0.8, 0.35, 94, 20260801)

    result = decode_expected_payload(capture, payload)

    assert result.payload == payload
    assert result.reconstructed_image.ndim == 2
    assert result.method in {"dynamic-range", "clahe", "unsharp-mask", "otsu", "adaptive"}
    assert set(np.unique(result.reconstructed_image).tolist()) == {0, 255}


def test_frame_filling_grid_reconstruction_uses_observed_modules() -> None:
    """Recover a tightly framed QR whose active modules have no photographed quiet zone."""
    payload = "LAB-001"
    active_mask = create_qr_mask(payload, 3, 4, "M")[4:-4, 4:-4]
    grayscale = render_reference_image(active_mask, 900, 900, 28, 248, 20)
    capture = cv2.cvtColor(grayscale, cv2.COLOR_GRAY2BGR)

    reconstruction, geometry_score, calibration_accuracy = (
        reconstruct_frame_filling_capture(capture)
    )
    decoded_payload, _, _ = cv2.QRCodeDetector().detectAndDecode(reconstruction)

    assert decoded_payload == payload
    assert geometry_score >= 0.85
    assert calibration_accuracy >= 0.95
