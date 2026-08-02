"""Offline reconstruction of low-contrast QR images."""

from pathlib import Path
from typing import NamedTuple, cast

import cv2
import numpy as np
from numpy.typing import NDArray

from optical_airgap_lab.errors import DecodeError, ImageReadError, PayloadMismatchError
from optical_airgap_lab.grid_decoding import reconstruct_frame_filling_capture
from optical_airgap_lab.payload import validate_lab_payload


class DecodeResult(NamedTuple):
    """Successful payload reconstruction and the image that produced it."""

    payload: str
    method: str
    reconstructed_image: NDArray[np.uint8]


def read_color_image(input_path: Path) -> NDArray[np.uint8]:
    """Load an image from disk as BGR pixels."""
    image = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ImageReadError(
            f"Could not read {input_path}. Confirm that the path exists and is a supported image."
        )
    return cast(NDArray[np.uint8], image)


def stretch_dynamic_range(image: NDArray[np.uint8]) -> NDArray[np.uint8]:
    """Stretch grayscale values to the full eight-bit range."""
    low = float(np.percentile(image, 0.5))
    high = float(np.percentile(image, 99.5))
    if high <= low:
        raise DecodeError(
            f"Image has no usable intensity range: low percentile={low}, high percentile={high}."
        )
    stretched = np.clip((image.astype(np.float32) - low) * (255.0 / (high - low)), 0, 255)
    return cast(NDArray[np.uint8], stretched.astype(np.uint8))


def build_reconstruction_candidates(
    color_image: NDArray[np.uint8],
) -> tuple[tuple[str, NDArray[np.uint8]], ...]:
    """Create explicit reconstruction variants described by the paper's processing stages."""
    grayscale = cast(NDArray[np.uint8], cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY))
    stretched = stretch_dynamic_range(grayscale)
    clahe = cast(
        NDArray[np.uint8], cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8)).apply(grayscale)
    )
    sharpened = cast(
        NDArray[np.uint8],
        cv2.addWeighted(stretched, 1.8, cv2.GaussianBlur(stretched, (0, 0), 2.0), -0.8, 0),
    )
    _, raw_otsu = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    otsu = cast(NDArray[np.uint8], raw_otsu)
    adaptive = cast(
        NDArray[np.uint8],
        cv2.adaptiveThreshold(
            clahe,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            51,
            3,
        ),
    )
    return (
        ("dynamic-range", stretched),
        ("clahe", clahe),
        ("unsharp-mask", sharpened),
        ("otsu", otsu),
        ("adaptive", adaptive),
    )


def render_straight_qr(
    straight_qr: NDArray[np.uint8], module_pixels: int, border_modules: int
) -> NDArray[np.uint8]:
    """Render OpenCV's normalized QR matrix as legible reconstruction evidence."""
    height, width = straight_qr.shape
    upscaled = cast(
        NDArray[np.uint8],
        cv2.resize(
            straight_qr,
            (width * module_pixels, height * module_pixels),
            interpolation=cv2.INTER_NEAREST,
        ),
    )
    border_pixels = border_modules * module_pixels
    return cast(
        NDArray[np.uint8],
        cv2.copyMakeBorder(
            upscaled,
            border_pixels,
            border_pixels,
            border_pixels,
            border_pixels,
            cv2.BORDER_CONSTANT,
            value=255,
        ),
    )


def decode_expected_payload(
    color_image: NDArray[np.uint8],
    expected_payload: str,
) -> DecodeResult:
    """Decode and verify one permitted synthetic identifier from a captured image."""
    validated_expected_payload = validate_lab_payload(expected_payload)
    result = decode_text_payload(color_image)
    if result.payload != validated_expected_payload:
        raise PayloadMismatchError(
            f"Decoded payload did not match {validated_expected_payload!r}; "
            f"observed {result.payload!r}."
        )
    return result


def decode_text_payload(color_image: NDArray[np.uint8]) -> DecodeResult:
    """Decode one explicit ASCII laboratory payload from a captured image."""
    detector = cv2.QRCodeDetector()

    for method, candidate in build_reconstruction_candidates(color_image):
        payload, _, straight_qr = detector.detectAndDecode(candidate)
        if payload:
            if straight_qr is None:
                raise DecodeError(
                    f"OpenCV decoded {payload!r} with {method} but returned no normalized QR image."
                )
            reconstruction = render_straight_qr(
                cast(NDArray[np.uint8], straight_qr),
                16,
                4,
            )
            return DecodeResult(payload, method, reconstruction)

    grid_reconstruction, geometry_score, calibration_accuracy = (
        reconstruct_frame_filling_capture(color_image)
    )
    payload, _, _ = detector.detectAndDecode(grid_reconstruction)
    if payload:
        method = (
            f"grid-sampled(geometry={geometry_score:.3f},"
            f"calibration={calibration_accuracy:.3f})"
        )
        return DecodeResult(payload, method, grid_reconstruction)
    raise DecodeError(
        "No QR payload was reconstructed. Capture the display straight-on, fill more of the "
        "camera frame, avoid glare, and begin with a larger contrast delta."
    )
