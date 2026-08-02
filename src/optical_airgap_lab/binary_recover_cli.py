"""Recover a bounded synthetic binary fixture from captured QR images."""

import argparse
from pathlib import Path

from optical_airgap_lab.binary_transfer import (
    decode_packet,
    reassemble_packets,
    validate_scoped_path,
)
from optical_airgap_lab.decoding import decode_text_payload, read_color_image
from optical_airgap_lab.errors import InvalidFixtureError

SUPPORTED_SUFFIXES = frozenset((".jpeg", ".jpg", ".png"))


def build_parser() -> argparse.ArgumentParser:
    """Create the bounded fixture receiver argument parser."""
    parser = argparse.ArgumentParser(
        description="Recover a synthetic fixture from images deliberately staged in captures/."
    )
    parser.add_argument("--captures", required=True, type=Path, help="Directory inside captures/.")
    parser.add_argument("--expected-sha256", required=True, help="Hash printed by the transmitter.")
    parser.add_argument("--output", required=True, type=Path, help="File inside recovered/.")
    return parser


def main() -> None:
    """Decode captured frames and write a hash-verified recovered fixture."""
    arguments = build_parser().parse_args()
    working_directory = Path.cwd()
    captures_directory = validate_scoped_path(
        arguments.captures, working_directory / "captures", "Capture input"
    )
    output_path = validate_scoped_path(
        arguments.output, working_directory / "recovered", "Recovered output"
    )
    if output_path.exists():
        raise InvalidFixtureError(
            f"Recovered output already exists and will not be overwritten: {output_path}."
        )
    if not captures_directory.is_dir():
        raise InvalidFixtureError(
            f"Capture input is not a directory: {captures_directory}."
        )
    image_paths_list: list[Path] = []
    for path in sorted(captures_directory.iterdir()):
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        validated_path = validate_scoped_path(path, captures_directory, "Capture image")
        if validated_path.is_file():
            image_paths_list.append(validated_path)
    image_paths = tuple(image_paths_list)
    if not image_paths:
        raise InvalidFixtureError(
            f"No PNG or JPEG capture images were found in {captures_directory}."
        )
    packets = tuple(
        decode_packet(decode_text_payload(read_color_image(path)).payload)
        for path in image_paths
    )
    recovered = reassemble_packets(packets, arguments.expected_sha256)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(recovered)
    print(
        f"Recovered synthetic fixture bytes={len(recovered)} "
        f"sha256={arguments.expected_sha256.lower()} output={output_path}"
    )


if __name__ == "__main__":
    main()
