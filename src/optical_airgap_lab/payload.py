"""Synthetic payload validation for the closed-loop experiment."""

import re

from optical_airgap_lab.errors import InvalidLabPayloadError

LAB_PAYLOAD_PATTERN = re.compile(r"LAB-[0-9]{3}\Z")


def validate_lab_payload(payload: str) -> str:
    """Return a validated synthetic identifier such as ``LAB-001``."""
    if LAB_PAYLOAD_PATTERN.fullmatch(payload) is None:
        raise InvalidLabPayloadError(
            f"Payload {payload!r} is not permitted. Use a synthetic identifier matching LAB-000."
        )
    return payload
