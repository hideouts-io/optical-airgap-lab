"""Specific errors raised by the optical signaling lab."""


class OpticalLabError(Exception):
    """Base error for expected experiment failures."""


class InvalidExperimentParameterError(OpticalLabError):
    """Raised when an experiment parameter is outside its valid range."""


class InvalidLabPayloadError(OpticalLabError):
    """Raised when a payload is not a synthetic lab identifier."""


class ImageReadError(OpticalLabError):
    """Raised when an image cannot be loaded."""


class DecodeError(OpticalLabError):
    """Raised when no QR payload can be reconstructed."""


class PayloadMismatchError(OpticalLabError):
    """Raised when the reconstructed payload differs from the expected identifier."""


class InvalidFixtureError(OpticalLabError):
    """Raised when a binary fixture is outside the bounded laboratory scope."""


class InvalidTransferPacketError(OpticalLabError):
    """Raised when a binary laboratory packet is malformed or corrupted."""
