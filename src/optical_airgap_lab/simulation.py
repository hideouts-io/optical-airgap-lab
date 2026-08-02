"""Deterministic camera-capture simulation for integration verification."""

from typing import cast

import cv2
import numpy as np
from numpy.typing import NDArray

from optical_airgap_lab.errors import InvalidExperimentParameterError


def simulate_camera_capture(
    transmitter_image: NDArray[np.uint8],
    output_width: int,
    output_height: int,
    noise_standard_deviation: float,
    blur_sigma: float,
    jpeg_quality: int,
    random_seed: int,
) -> NDArray[np.uint8]:
    """Return a perspective-warped, noisy JPEG-like photo of a screen."""
    if output_width < 320 or output_height < 240:
        raise InvalidExperimentParameterError(
            f"Simulated capture must be at least 320x240; received {output_width}x{output_height}."
        )
    if noise_standard_deviation < 0 or blur_sigma < 0:
        raise InvalidExperimentParameterError(
            "Noise standard deviation and blur sigma must be nonnegative; "
            f"received noise={noise_standard_deviation}, blur={blur_sigma}."
        )
    if jpeg_quality < 1 or jpeg_quality > 100:
        raise InvalidExperimentParameterError(
            f"JPEG quality must be between 1 and 100; received {jpeg_quality}."
        )

    source_height, source_width = transmitter_image.shape
    source_points = np.asarray(
        [
            [0, 0],
            [source_width - 1, 0],
            [source_width - 1, source_height - 1],
            [0, source_height - 1],
        ],
        dtype=np.float32,
    )
    margin_x = output_width * 0.08
    margin_y = output_height * 0.08
    destination_points = np.asarray(
        [
            [margin_x * 1.15, margin_y * 1.30],
            [output_width - margin_x * 0.80, margin_y * 0.75],
            [output_width - margin_x * 1.20, output_height - margin_y * 1.15],
            [margin_x * 0.75, output_height - margin_y * 0.70],
        ],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(source_points, destination_points)
    room = np.full((output_height, output_width), 28, dtype=np.uint8)
    screen = cv2.warpPerspective(
        transmitter_image,
        transform,
        (output_width, output_height),
        dst=room.copy(),
        borderMode=cv2.BORDER_TRANSPARENT,
    )

    horizontal_gradient = np.linspace(0.97, 1.03, output_width, dtype=np.float32)
    illuminated = np.clip(screen.astype(np.float32) * horizontal_gradient[np.newaxis, :], 0, 255)
    blurred = cv2.GaussianBlur(illuminated, (0, 0), blur_sigma) if blur_sigma > 0 else illuminated
    random_generator = np.random.default_rng(random_seed)
    noise = random_generator.normal(0.0, noise_standard_deviation, blurred.shape)
    noisy = np.clip(blurred + noise, 0, 255).astype(np.uint8)
    color = cv2.cvtColor(noisy, cv2.COLOR_GRAY2BGR)
    encoded, jpeg = cv2.imencode(".jpg", color, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
    if not encoded:
        raise OSError("OpenCV could not encode the simulated camera capture as JPEG.")
    decoded = cv2.imdecode(jpeg, cv2.IMREAD_COLOR)
    if decoded is None:
        raise OSError("OpenCV could not decode its simulated JPEG camera capture.")
    return cast(NDArray[np.uint8], decoded)
