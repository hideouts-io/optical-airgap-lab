"""Integration coverage for bounded synthetic binary fixture transfers."""

import cv2
import pytest

from optical_airgap_lab.binary_transfer import (
    create_manifest,
    decode_packet,
    encode_packet,
    packetize_fixture,
    reassemble_packets,
)
from optical_airgap_lab.decoding import decode_text_payload
from optical_airgap_lab.encoding import create_qr_mask_from_bytes
from optical_airgap_lab.errors import InvalidFixtureError
from optical_airgap_lab.rendering import render_reference_image


def test_binary_fixture_round_trip_through_qr_images() -> None:
    """Recover every byte after actual QR encoding, image decoding, and packet assembly."""
    fixture = bytes(range(64))
    manifest = create_manifest(fixture)
    recovered_packets = []

    for packet in packetize_fixture(fixture):
        encoded_packet = encode_packet(packet)
        qr_mask = create_qr_mask_from_bytes(encoded_packet.encode("ascii"), 3, 4, "M")
        grayscale = render_reference_image(qr_mask, 900, 900, 20, 255, 255)
        capture = cv2.cvtColor(grayscale, cv2.COLOR_GRAY2BGR)
        decoded_text = decode_text_payload(capture).payload
        recovered_packets.append(decode_packet(decoded_text))

    recovered = reassemble_packets(tuple(reversed(recovered_packets)), manifest.sha256)

    assert recovered == fixture


def test_binary_fixture_limit_rejects_bulk_transfer() -> None:
    """Keep the operational exercise bounded to a small synthetic fixture."""
    with pytest.raises(InvalidFixtureError, match="1 through 256 bytes"):
        create_manifest(bytes(257))
