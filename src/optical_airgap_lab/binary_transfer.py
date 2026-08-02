"""Bounded packet framing for synthetic binary optical-transfer experiments."""

import base64
import binascii
import hashlib
import math
import struct
import zlib
from pathlib import Path
from typing import Final, NamedTuple

from optical_airgap_lab.errors import InvalidFixtureError, InvalidTransferPacketError

MAGIC: Final = b"OAL1"
MAX_FIXTURE_BYTES: Final = 256
CHUNK_BYTES: Final = 14
HEADER: Final = struct.Struct(">4s8sBBB")
CHECKSUM: Final = struct.Struct(">I")


class BinaryPacket(NamedTuple):
    """One ordered, checksummed binary fixture fragment."""

    transfer_id: bytes
    sequence: int
    total: int
    payload: bytes


class TransferManifest(NamedTuple):
    """Reproducibility metadata for one bounded fixture transfer."""

    sha256: str
    size: int
    frames: int


def validate_scoped_path(path: Path, allowed_directory: Path, purpose: str) -> Path:
    """Resolve a path and require it to remain under one explicit laboratory directory."""
    resolved_directory = allowed_directory.resolve()
    resolved_path = path.resolve()
    if not resolved_path.is_relative_to(resolved_directory):
        raise InvalidFixtureError(
            f"{purpose} must be inside {resolved_directory}; received {resolved_path}."
        )
    if path.is_symlink():
        raise InvalidFixtureError(f"{purpose} must not be a symbolic link: {path}.")
    return resolved_path


def read_fixture(path: Path, fixtures_directory: Path) -> bytes:
    """Read one deliberately staged, small, regular fixture file."""
    resolved_path = validate_scoped_path(path, fixtures_directory, "Fixture input")
    if not resolved_path.is_file():
        raise InvalidFixtureError(f"Fixture input is not a regular file: {resolved_path}.")
    size = resolved_path.stat().st_size
    if size < 1 or size > MAX_FIXTURE_BYTES:
        raise InvalidFixtureError(
            f"Fixture size must be from 1 through {MAX_FIXTURE_BYTES} bytes; "
            f"received {size} bytes from {resolved_path}."
        )
    return resolved_path.read_bytes()


def create_manifest(data: bytes) -> TransferManifest:
    """Describe the complete fixture before it is packetized."""
    if not data or len(data) > MAX_FIXTURE_BYTES:
        raise InvalidFixtureError(
            f"Fixture data must be from 1 through {MAX_FIXTURE_BYTES} bytes; "
            f"received {len(data)} bytes."
        )
    digest = hashlib.sha256(data).hexdigest()
    return TransferManifest(digest, len(data), math.ceil(len(data) / CHUNK_BYTES))


def packetize_fixture(data: bytes) -> tuple[BinaryPacket, ...]:
    """Split a bounded fixture into numbered packets identified by its hash prefix."""
    manifest = create_manifest(data)
    transfer_id = bytes.fromhex(manifest.sha256)[:8]
    return tuple(
        BinaryPacket(
            transfer_id,
            sequence,
            manifest.frames,
            data[sequence * CHUNK_BYTES : (sequence + 1) * CHUNK_BYTES],
        )
        for sequence in range(manifest.frames)
    )


def encode_packet(packet: BinaryPacket) -> str:
    """Encode one packet as ASCII suitable for interoperable QR decoders."""
    if len(packet.transfer_id) != 8:
        raise InvalidTransferPacketError(
            f"Transfer identifier must contain 8 bytes; received {len(packet.transfer_id)}."
        )
    if packet.total < 1 or packet.total > 255:
        raise InvalidTransferPacketError(
            f"Packet total must be from 1 through 255; received {packet.total}."
        )
    if packet.sequence < 0 or packet.sequence >= packet.total:
        raise InvalidTransferPacketError(
            f"Packet sequence must be below total; received {packet.sequence}/{packet.total}."
        )
    if not packet.payload or len(packet.payload) > CHUNK_BYTES:
        raise InvalidTransferPacketError(
            f"Packet payload must be from 1 through {CHUNK_BYTES} bytes; "
            f"received {len(packet.payload)}."
        )
    body = HEADER.pack(
        MAGIC,
        packet.transfer_id,
        packet.sequence,
        packet.total,
        len(packet.payload),
    ) + packet.payload
    raw_packet = body + CHECKSUM.pack(zlib.crc32(body))
    encoded = base64.b85encode(raw_packet)
    if len(encoded) > 42:
        raise InvalidTransferPacketError(
            f"Encoded packet exceeds version-three QR capacity: {len(encoded)} bytes."
        )
    return encoded.decode("ascii")


def decode_packet(encoded_packet: str) -> BinaryPacket:
    """Parse and verify one ASCII packet recovered from a QR frame."""
    try:
        raw_packet = base64.b85decode(encoded_packet.encode("ascii"))
    except (UnicodeEncodeError, ValueError, binascii.Error) as error:
        raise InvalidTransferPacketError(
            f"Recovered QR text is not a valid Base85 laboratory packet: {encoded_packet!r}."
        ) from error
    minimum_size = HEADER.size + 1 + CHECKSUM.size
    if len(raw_packet) < minimum_size:
        raise InvalidTransferPacketError(
            f"Decoded packet is too short: expected at least {minimum_size}, "
            f"received {len(raw_packet)} bytes."
        )
    body = raw_packet[:-CHECKSUM.size]
    observed_checksum = CHECKSUM.unpack(raw_packet[-CHECKSUM.size :])[0]
    expected_checksum = zlib.crc32(body)
    if observed_checksum != expected_checksum:
        raise InvalidTransferPacketError(
            "Packet CRC32 mismatch: "
            f"expected {expected_checksum:08x}, observed {observed_checksum:08x}."
        )
    magic, transfer_id, sequence, total, payload_length = HEADER.unpack(body[: HEADER.size])
    if magic != MAGIC:
        raise InvalidTransferPacketError(
            f"Packet magic must be {MAGIC!r}; observed {magic!r}."
        )
    payload = body[HEADER.size :]
    if len(payload) != payload_length:
        raise InvalidTransferPacketError(
            f"Packet payload length says {payload_length}; decoded {len(payload)} bytes."
        )
    packet = BinaryPacket(transfer_id, sequence, total, payload)
    encode_packet(packet)
    return packet


def reassemble_packets(
    packets: tuple[BinaryPacket, ...], expected_sha256: str
) -> bytes:
    """Deduplicate, order, and verify all packets against an externally recorded hash."""
    if len(expected_sha256) != 64:
        raise InvalidTransferPacketError(
            f"Expected SHA-256 must contain 64 hexadecimal characters: {expected_sha256!r}."
        )
    try:
        expected_digest = bytes.fromhex(expected_sha256)
    except ValueError as error:
        raise InvalidTransferPacketError(
            f"Expected SHA-256 is not hexadecimal: {expected_sha256!r}."
        ) from error
    if not packets:
        raise InvalidTransferPacketError("At least one decoded packet is required.")

    transfer_id = packets[0].transfer_id
    total = packets[0].total
    if transfer_id != expected_digest[:8]:
        raise InvalidTransferPacketError(
            f"Transfer identifier {transfer_id.hex()} does not match expected SHA-256 prefix."
        )
    unique_packets: dict[int, bytes] = {}
    for packet in packets:
        if packet.transfer_id != transfer_id or packet.total != total:
            raise InvalidTransferPacketError("Captured packets describe mixed transfers.")
        existing = unique_packets.get(packet.sequence)
        if existing is not None and existing != packet.payload:
            raise InvalidTransferPacketError(
                f"Conflicting duplicate packets were captured for sequence {packet.sequence}."
            )
        unique_packets[packet.sequence] = packet.payload
    missing = tuple(sequence for sequence in range(total) if sequence not in unique_packets)
    if missing:
        raise InvalidTransferPacketError(f"Transfer is incomplete; missing sequences {missing}.")

    recovered = b"".join(unique_packets[sequence] for sequence in range(total))
    observed_sha256 = hashlib.sha256(recovered).hexdigest()
    if observed_sha256 != expected_sha256.lower():
        raise InvalidTransferPacketError(
            f"Recovered SHA-256 mismatch: expected {expected_sha256.lower()}, "
            f"observed {observed_sha256}."
        )
    return recovered


def estimate_frame_count(data_bytes: int) -> int:
    """Calculate frame count without reading or transmitting any file."""
    if data_bytes < 1:
        raise InvalidFixtureError(
            f"Estimated data size must be positive; received {data_bytes} bytes."
        )
    return math.ceil(data_bytes / CHUNK_BYTES)
