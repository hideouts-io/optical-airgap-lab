"""Command-line entry point for offline image reconstruction."""

import argparse
from pathlib import Path

from optical_airgap_lab.decoding import decode_expected_payload, read_color_image
from optical_airgap_lab.rendering import write_png


def build_parser() -> argparse.ArgumentParser:
    """Create the decoder argument parser."""
    parser = argparse.ArgumentParser(description="Decode a photographed lab transmitter.")
    parser.add_argument("--input", required=True, type=Path, help="Captured photo path.")
    parser.add_argument("--expected", required=True, help="Expected identifier matching LAB-000.")
    parser.add_argument(
        "--reconstruction",
        required=True,
        type=Path,
        help="Output path for the successful reconstructed image.",
    )
    return parser


def main() -> None:
    """Decode one captured photo and verify its synthetic identifier."""
    arguments = build_parser().parse_args()
    image = read_color_image(arguments.input)
    result = decode_expected_payload(image, arguments.expected)
    write_png(result.reconstructed_image, arguments.reconstruction)
    print(
        f"Decoded payload={result.payload} method={result.method} "
        f"reconstruction={arguments.reconstruction}"
    )


if __name__ == "__main__":
    main()
