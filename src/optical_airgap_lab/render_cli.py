"""Command-line entry point for creating the static transmitter."""

import argparse
from pathlib import Path

from optical_airgap_lab.encoding import create_qr_mask
from optical_airgap_lab.rendering import (
    build_transmitter_html,
    render_reference_image,
    write_png,
    write_text,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the transmitter argument parser."""
    parser = argparse.ArgumentParser(description="Render a low-contrast synthetic QR transmitter.")
    parser.add_argument("--payload", required=True, help="Synthetic identifier matching LAB-000.")
    parser.add_argument("--html", required=True, type=Path, help="Output transmitter HTML path.")
    parser.add_argument("--reference", required=True, type=Path, help="Output reference PNG path.")
    parser.add_argument("--background", required=True, type=int, help="Background grayscale value.")
    parser.add_argument("--contrast", required=True, type=int, help="Foreground intensity delta.")
    parser.add_argument(
        "--qr-version", required=True, type=int, help="QR version from 1 through 40."
    )
    parser.add_argument(
        "--qr-border", required=True, type=int, help="Quiet-zone modules, at least 4."
    )
    parser.add_argument(
        "--error-correction",
        required=True,
        choices=("L", "M", "Q", "H"),
        help="QR error-correction level.",
    )
    parser.add_argument("--canvas-width", required=True, type=int, help="Reference image width.")
    parser.add_argument("--canvas-height", required=True, type=int, help="Reference image height.")
    parser.add_argument(
        "--module-pixels", required=True, type=int, help="Reference pixels per module."
    )
    return parser


def main() -> None:
    """Render the transmitter page and reference image."""
    arguments = build_parser().parse_args()
    qr_mask = create_qr_mask(
        arguments.payload,
        arguments.qr_version,
        arguments.qr_border,
        arguments.error_correction,
    )
    reference = render_reference_image(
        qr_mask,
        arguments.canvas_width,
        arguments.canvas_height,
        arguments.module_pixels,
        arguments.background,
        arguments.contrast,
    )
    transmitter_html = build_transmitter_html(
        qr_mask,
        arguments.payload,
        arguments.background,
        arguments.contrast,
    )
    write_png(reference, arguments.reference)
    write_text(transmitter_html, arguments.html)
    contrast_percent = 100.0 * arguments.contrast / 255.0
    print(
        f"Rendered payload={arguments.payload} contrast={contrast_percent:.2f}% "
        f"html={arguments.html} reference={arguments.reference}"
    )


if __name__ == "__main__":
    main()
