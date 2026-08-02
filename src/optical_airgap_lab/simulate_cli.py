"""Command-line entry point for deterministic camera simulation."""

import argparse
from pathlib import Path
from typing import cast

import cv2
import numpy as np
from numpy.typing import NDArray

from optical_airgap_lab.errors import ImageReadError
from optical_airgap_lab.rendering import write_png
from optical_airgap_lab.simulation import simulate_camera_capture


def build_parser() -> argparse.ArgumentParser:
    """Create the simulation argument parser."""
    parser = argparse.ArgumentParser(description="Simulate photographing a transmitter screen.")
    parser.add_argument("--input", required=True, type=Path, help="Reference transmitter PNG.")
    parser.add_argument("--output", required=True, type=Path, help="Simulated photo output path.")
    parser.add_argument("--width", required=True, type=int, help="Simulated photo width.")
    parser.add_argument("--height", required=True, type=int, help="Simulated photo height.")
    parser.add_argument(
        "--noise", required=True, type=float, help="Gaussian noise standard deviation."
    )
    parser.add_argument("--blur", required=True, type=float, help="Gaussian blur sigma.")
    parser.add_argument(
        "--jpeg-quality", required=True, type=int, help="JPEG quality from 1 to 100."
    )
    parser.add_argument("--seed", required=True, type=int, help="Deterministic random seed.")
    return parser


def main() -> None:
    """Generate one deterministic simulated camera photo."""
    arguments = build_parser().parse_args()
    transmitter = cv2.imread(str(arguments.input), cv2.IMREAD_GRAYSCALE)
    if transmitter is None:
        raise ImageReadError(
            f"Could not read {arguments.input}. Generate the reference image before simulation."
        )
    capture = simulate_camera_capture(
        cast(NDArray[np.uint8], transmitter),
        arguments.width,
        arguments.height,
        arguments.noise,
        arguments.blur,
        arguments.jpeg_quality,
        arguments.seed,
    )
    write_png(capture, arguments.output)
    print(f"Simulated capture={arguments.output}")


if __name__ == "__main__":
    main()
