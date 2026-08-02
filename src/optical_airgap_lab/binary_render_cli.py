"""Render a bounded synthetic binary fixture as low-contrast QR frames."""

import argparse
import json
from pathlib import Path

from optical_airgap_lab.binary_transfer import (
    create_manifest,
    encode_packet,
    packetize_fixture,
    read_fixture,
    validate_scoped_path,
)
from optical_airgap_lab.encoding import create_qr_mask_from_bytes
from optical_airgap_lab.errors import InvalidFixtureError
from optical_airgap_lab.rendering import (
    build_sequence_transmitter_html,
    render_reference_image,
    write_png,
    write_text,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the bounded fixture transmitter argument parser."""
    parser = argparse.ArgumentParser(
        description="Render a file deliberately staged in fixtures/ as synthetic QR frames."
    )
    parser.add_argument("--input", required=True, type=Path, help="File inside fixtures/.")
    parser.add_argument("--frames", required=True, type=Path, help="Directory inside artifacts/.")
    parser.add_argument("--html", required=True, type=Path, help="HTML path inside artifacts/.")
    parser.add_argument("--background", required=True, type=int, help="Background grayscale.")
    parser.add_argument("--contrast", required=True, type=int, help="Foreground intensity delta.")
    parser.add_argument("--frame-ms", required=True, type=int, help="Playback frame duration.")
    return parser


def main() -> None:
    """Packetize and render one explicitly staged synthetic fixture."""
    arguments = build_parser().parse_args()
    working_directory = Path.cwd()
    data = read_fixture(arguments.input, working_directory / "fixtures")
    frames_directory = validate_scoped_path(
        arguments.frames, working_directory / "artifacts", "Frame output"
    )
    html_path = validate_scoped_path(
        arguments.html, working_directory / "artifacts", "HTML output"
    )
    if html_path.exists():
        raise InvalidFixtureError(
            f"HTML output already exists and will not be overwritten: {html_path}."
        )
    if frames_directory.exists() and any(frames_directory.iterdir()):
        raise InvalidFixtureError(
            f"Frame output directory is not empty and will not be overwritten: {frames_directory}."
        )
    manifest = create_manifest(data)
    encoded_packets = tuple(encode_packet(packet) for packet in packetize_fixture(data))
    masks = tuple(
        create_qr_mask_from_bytes(encoded.encode("ascii"), 3, 4, "M")
        for encoded in encoded_packets
    )
    for sequence, mask in enumerate(masks):
        frame = render_reference_image(
            mask, 1200, 900, 18, arguments.background, arguments.contrast
        )
        write_png(frame, frames_directory / f"frame-{sequence:03d}.png")
    manifest_json = json.dumps(
        {"sha256": manifest.sha256, "size": manifest.size, "frames": manifest.frames},
        indent=2,
        sort_keys=True,
    )
    write_text(manifest_json + "\n", frames_directory / "manifest.json")
    html = build_sequence_transmitter_html(
        masks,
        manifest.sha256[:16],
        arguments.background,
        arguments.contrast,
        arguments.frame_ms,
    )
    write_text(html, html_path)
    print(
        f"Rendered synthetic fixture size={manifest.size} frames={manifest.frames} "
        f"sha256={manifest.sha256} html={html_path}"
    )


if __name__ == "__main__":
    main()
