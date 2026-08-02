"""QR encoding for low-contrast optical signaling."""

from typing import Final

import numpy as np
import qrcode
from numpy.typing import NDArray
from qrcode.constants import (
    ERROR_CORRECT_H,
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
)

from optical_airgap_lab.errors import InvalidExperimentParameterError
from optical_airgap_lab.payload import validate_lab_payload

ERROR_CORRECTION_LEVELS: Final[dict[str, int]] = {
    "L": ERROR_CORRECT_L,
    "M": ERROR_CORRECT_M,
    "Q": ERROR_CORRECT_Q,
    "H": ERROR_CORRECT_H,
}


def create_qr_mask(
    payload: str,
    version: int,
    border_modules: int,
    error_correction_level: str,
) -> NDArray[np.bool_]:
    """Encode a synthetic lab identifier as a boolean QR module matrix."""
    validated_payload = validate_lab_payload(payload)
    return create_qr_mask_from_bytes(
        validated_payload.encode("ascii"),
        version,
        border_modules,
        error_correction_level,
    )


def create_qr_mask_from_bytes(
    payload: bytes,
    version: int,
    border_modules: int,
    error_correction_level: str,
) -> NDArray[np.bool_]:
    """Encode explicit laboratory packet bytes as a boolean QR module matrix."""
    if not payload:
        raise InvalidExperimentParameterError("QR byte payload must not be empty.")
    if version < 1 or version > 40:
        raise InvalidExperimentParameterError(
            f"QR version must be between 1 and 40; received {version}."
        )
    if border_modules < 4:
        raise InvalidExperimentParameterError(
            f"QR quiet-zone border must be at least 4 modules; received {border_modules}."
        )
    if error_correction_level not in ERROR_CORRECTION_LEVELS:
        allowed_levels = ", ".join(sorted(ERROR_CORRECTION_LEVELS))
        raise InvalidExperimentParameterError(
            f"QR error correction must be one of {allowed_levels}; received "
            f"{error_correction_level!r}."
        )

    qr_code = qrcode.QRCode(
        version=version,
        error_correction=ERROR_CORRECTION_LEVELS[error_correction_level],
        box_size=1,
        border=border_modules,
    )
    qr_code.add_data(payload)
    qr_code.make(fit=False)
    matrix = np.asarray(qr_code.get_matrix(), dtype=np.bool_)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise InvalidExperimentParameterError(
            f"QR encoder returned an invalid matrix shape: {matrix.shape}."
        )
    return matrix
