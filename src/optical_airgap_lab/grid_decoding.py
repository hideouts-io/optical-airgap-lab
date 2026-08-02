"""Reconstruct a frame-filling version-three QR capture from its module grid."""

from typing import Final, cast

import cv2
import numpy as np
from numpy.typing import NDArray

from optical_airgap_lab.encoding import create_qr_mask
from optical_airgap_lab.errors import DecodeError

MODULE_COUNT: Final = 29


def create_function_module_mask() -> NDArray[np.bool_]:
    """Mark version-three finder, separator, timing, alignment, and dark modules."""
    mask = np.zeros((MODULE_COUNT, MODULE_COUNT), dtype=np.bool_)
    for origin_x, origin_y in ((0, 0), (22, 0), (0, 22)):
        mask[origin_y : origin_y + 7, origin_x : origin_x + 7] = True

    mask[7, 0:8] = True
    mask[0:8, 7] = True
    mask[7, 21:29] = True
    mask[0:8, 21] = True
    mask[21:29, 7] = True
    mask[21, 0:8] = True
    mask[6, 8:21] = True
    mask[8:21, 6] = True
    mask[20:25, 20:25] = True
    mask[21, 8] = True
    return mask


def create_initial_quad(image_width: int, image_height: int) -> NDArray[np.float32]:
    """Place an initial active-code quadrilateral five percent inside the frame."""
    inset_x = image_width * 0.05
    inset_y = image_height * 0.05
    return np.asarray(
        (
            (inset_x, inset_y),
            (image_width - inset_x, inset_y),
            (image_width - inset_x, image_height - inset_y),
            (inset_x, image_height - inset_y),
        ),
        dtype=np.float32,
    )


def create_module_centers() -> NDArray[np.float32]:
    """Create canonical center coordinates for all active QR modules."""
    coordinates = np.arange(MODULE_COUNT, dtype=np.float32) + 0.5
    grid_x, grid_y = np.meshgrid(coordinates, coordinates)
    return cast(
        NDArray[np.float32],
        np.stack((grid_x, grid_y), axis=-1).reshape(1, -1, 2),
    )


def sample_module_contrast(
    blurred_image: NDArray[np.float32],
    quad: NDArray[np.float32],
    module_centers: NDArray[np.float32],
) -> NDArray[np.float32]:
    """Perspective-map module centers and remove smooth illumination variation."""
    canonical_quad = np.asarray(
        ((0, 0), (MODULE_COUNT, 0), (MODULE_COUNT, MODULE_COUNT), (0, MODULE_COUNT)),
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(canonical_quad, quad)
    image_points = cv2.perspectiveTransform(module_centers, transform).reshape(
        MODULE_COUNT, MODULE_COUNT, 2
    )
    sampled = cast(
        NDArray[np.float32],
        cv2.remap(
            blurred_image,
            image_points[:, :, 0],
            image_points[:, :, 1],
            cv2.INTER_LINEAR,
        ),
    )
    local_background = cast(
        NDArray[np.float32], cv2.GaussianBlur(sampled, (0, 0), 0.65)
    )
    return local_background - sampled


def function_pattern_score(
    module_contrast: NDArray[np.float32],
    function_mask: NDArray[np.bool_],
    function_values: NDArray[np.bool_],
) -> float:
    """Measure agreement with payload-independent QR function modules."""
    observed = module_contrast[function_mask].astype(np.float64)
    expected = function_values[function_mask].astype(np.float64)
    correlation = float(np.corrcoef(observed, expected)[0, 1])
    if not np.isfinite(correlation):
        raise DecodeError("Function-pattern correlation is not finite; the capture is unusable.")
    return correlation


def optimize_function_geometry(
    blurred_image: NDArray[np.float32],
    initial_quad: NDArray[np.float32],
    module_centers: NDArray[np.float32],
    function_mask: NDArray[np.bool_],
    function_values: NDArray[np.bool_],
) -> tuple[NDArray[np.float32], float]:
    """Fit the QR quadrilateral using only payload-independent function modules."""
    random_generator = np.random.default_rng(20260801)
    best_quad = initial_quad.copy()
    best_score = function_pattern_score(
        sample_module_contrast(blurred_image, best_quad, module_centers),
        function_mask,
        function_values,
    )
    step = min(blurred_image.shape) * 0.009

    for _ in range(6):
        for _ in range(500):
            candidate = cast(
                NDArray[np.float32],
                (
                    best_quad + random_generator.normal(0.0, step, best_quad.shape)
                ).astype(np.float32),
            )
            candidate[:, 0] = np.clip(candidate[:, 0], 0, blurred_image.shape[1] - 1)
            candidate[:, 1] = np.clip(candidate[:, 1], 0, blurred_image.shape[0] - 1)
            if not cv2.isContourConvex(candidate.astype(np.float32)):
                continue
            candidate_score = function_pattern_score(
                sample_module_contrast(blurred_image, candidate, module_centers),
                function_mask,
                function_values,
            )
            if candidate_score > best_score:
                best_quad = candidate
                best_score = candidate_score
        step *= 0.5

    return best_quad, best_score


def classify_modules(
    module_contrast: NDArray[np.float32],
    function_mask: NDArray[np.bool_],
    function_values: NDArray[np.bool_],
) -> tuple[NDArray[np.bool_], float]:
    """Calibrate a dark-module threshold from known QR function modules."""
    calibration_values = module_contrast[function_mask]
    low = float(np.percentile(calibration_values, 2))
    high = float(np.percentile(calibration_values, 98))
    if high <= low:
        raise DecodeError(
            f"Function modules have no usable contrast range: low={low}, high={high}."
        )

    best_accuracy = 0.0
    best_threshold = low
    for threshold in np.linspace(low, high, 1000):
        accuracy = float(
            np.mean(
                (module_contrast[function_mask] > threshold)
                == function_values[function_mask]
            )
        )
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = float(threshold)

    return module_contrast > best_threshold, best_accuracy


def render_observed_modules(
    dark_modules: NDArray[np.bool_], module_pixels: int, border_modules: int
) -> NDArray[np.uint8]:
    """Render only the classified photographed modules with a clean quiet zone."""
    active_code = np.where(dark_modules, 0, 255).astype(np.uint8)
    upscaled = cast(
        NDArray[np.uint8],
        cv2.resize(
            active_code,
            (MODULE_COUNT * module_pixels, MODULE_COUNT * module_pixels),
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


def reconstruct_frame_filling_capture(
    color_image: NDArray[np.uint8],
) -> tuple[NDArray[np.uint8], float, float]:
    """Reconstruct a tightly framed version-three QR without using its data modules."""
    grayscale = cast(NDArray[np.uint8], cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY))
    module_pixels = min(grayscale.shape) / MODULE_COUNT
    blurred = cast(
        NDArray[np.float32],
        cv2.GaussianBlur(grayscale.astype(np.float32), (0, 0), module_pixels * 0.08),
    )
    function_mask = create_function_module_mask()
    reference = create_qr_mask("LAB-000", 3, 4, "M")[4:-4, 4:-4]
    centers = create_module_centers()
    initial_quad = create_initial_quad(grayscale.shape[1], grayscale.shape[0])
    fitted_quad, geometry_score = optimize_function_geometry(
        blurred, initial_quad, centers, function_mask, reference
    )
    module_contrast = sample_module_contrast(blurred, fitted_quad, centers)
    dark_modules, calibration_accuracy = classify_modules(
        module_contrast, function_mask, reference
    )
    if geometry_score < 0.85 or calibration_accuracy < 0.95:
        raise DecodeError(
            "Frame-filling grid reconstruction was unreliable: "
            f"geometry_score={geometry_score:.3f}, "
            f"calibration_accuracy={calibration_accuracy:.3f}."
        )
    return render_observed_modules(dark_modules, 16, 4), geometry_score, calibration_accuracy
