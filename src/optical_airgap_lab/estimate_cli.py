"""Estimate optical frame counts without reading or transmitting a file."""

import argparse

from optical_airgap_lab.binary_transfer import estimate_frame_count
from optical_airgap_lab.errors import InvalidExperimentParameterError


def build_parser() -> argparse.ArgumentParser:
    """Create the non-transmitting capacity-estimator argument parser."""
    parser = argparse.ArgumentParser(description="Estimate bounded packet-channel frame counts.")
    parser.add_argument("--bytes", required=True, type=int, help="Hypothetical data size.")
    parser.add_argument(
        "--frames-per-second", required=True, type=float, help="Hypothetical decoded frame rate."
    )
    parser.add_argument(
        "--repetitions", required=True, type=int, help="Hypothetical repetitions per frame."
    )
    return parser


def main() -> None:
    """Print a theoretical frame and duration estimate without touching user data."""
    arguments = build_parser().parse_args()
    if arguments.frames_per_second <= 0:
        raise InvalidExperimentParameterError(
            "Frames per second must be positive; "
            f"received {arguments.frames_per_second}."
        )
    if arguments.repetitions < 1:
        raise InvalidExperimentParameterError(
            f"Repetitions must be positive; received {arguments.repetitions}."
        )
    unique_frames = estimate_frame_count(arguments.bytes)
    displayed_frames = unique_frames * arguments.repetitions
    seconds = displayed_frames / arguments.frames_per_second
    print(
        f"bytes={arguments.bytes} payload_bytes_per_frame=14 "
        f"unique_frames={unique_frames} displayed_frames={displayed_frames} "
        f"ideal_seconds={seconds:.1f} ideal_hours={seconds / 3600:.2f}"
    )


if __name__ == "__main__":
    main()
