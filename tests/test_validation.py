"""Boundary validation for controlled lab inputs."""

import pytest

from optical_airgap_lab.errors import (
    InvalidExperimentParameterError,
    InvalidLabPayloadError,
)
from optical_airgap_lab.payload import validate_lab_payload
from optical_airgap_lab.rendering import validate_intensities


def test_payload_is_restricted_to_synthetic_identifier() -> None:
    """Reject arbitrary content instead of turning the lab into a general exfiltration utility."""
    with pytest.raises(InvalidLabPayloadError, match="not permitted"):
        validate_lab_payload("private-file-content")


def test_contrast_must_fit_inside_background_intensity() -> None:
    """Reject an impossible foreground intensity."""
    with pytest.raises(InvalidExperimentParameterError, match="Contrast delta"):
        validate_intensities(8, 9)
