"""Pure rendering functions for the low-contrast transmitter."""

import html
import json
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from optical_airgap_lab.errors import InvalidExperimentParameterError


def validate_intensities(background_intensity: int, contrast_delta: int) -> tuple[int, int]:
    """Validate and return background and foreground grayscale intensities."""
    if background_intensity < 1 or background_intensity > 255:
        raise InvalidExperimentParameterError(
            f"Background intensity must be between 1 and 255; received {background_intensity}."
        )
    if contrast_delta < 1 or contrast_delta > background_intensity:
        raise InvalidExperimentParameterError(
            "Contrast delta must be positive and no greater than the background intensity; "
            f"received delta={contrast_delta}, background={background_intensity}."
        )
    return background_intensity, background_intensity - contrast_delta


def render_reference_image(
    qr_mask: NDArray[np.bool_],
    canvas_width: int,
    canvas_height: int,
    module_pixels: int,
    background_intensity: int,
    contrast_delta: int,
) -> NDArray[np.uint8]:
    """Render a centered low-contrast QR code on a grayscale canvas."""
    background, foreground = validate_intensities(background_intensity, contrast_delta)
    if canvas_width < 1 or canvas_height < 1 or module_pixels < 1:
        raise InvalidExperimentParameterError(
            "Canvas dimensions and module size must be positive; "
            f"received width={canvas_width}, height={canvas_height}, module={module_pixels}."
        )

    qr_pixels = np.repeat(np.repeat(qr_mask, module_pixels, axis=0), module_pixels, axis=1)
    qr_height, qr_width = qr_pixels.shape
    if qr_width > canvas_width or qr_height > canvas_height:
        raise InvalidExperimentParameterError(
            "Rendered QR does not fit on the requested canvas; "
            f"QR={qr_width}x{qr_height}, canvas={canvas_width}x{canvas_height}."
        )

    canvas = np.full((canvas_height, canvas_width), background, dtype=np.uint8)
    top = (canvas_height - qr_height) // 2
    left = (canvas_width - qr_width) // 2
    rendered_qr = np.where(qr_pixels, foreground, background).astype(np.uint8)
    result = canvas.copy()
    result[top : top + qr_height, left : left + qr_width] = rendered_qr
    return result


def write_png(image: NDArray[np.uint8], output_path: Path) -> None:
    """Write a grayscale experiment image or raise a specific error."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = cv2.imwrite(str(output_path), image)
    if not written:
        raise OSError(f"OpenCV could not write image to {output_path}.")


def build_transmitter_html(
    qr_mask: NDArray[np.bool_],
    payload: str,
    background_intensity: int,
    contrast_delta: int,
) -> str:
    """Build a dependency-free responsive transmitter page."""
    background, foreground = validate_intensities(background_intensity, contrast_delta)
    matrix_rows = [[1 if value else 0 for value in row] for row in qr_mask.tolist()]
    matrix_json = json.dumps(matrix_rows, separators=(",", ":"))
    safe_payload = html.escape(payload, quote=True)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Optical Air-Gap Lab Transmitter</title>
  <style>
    html, body, canvas {{ width: 100%; height: 100%; margin: 0; overflow: hidden; }}
    body {{ background: rgb({background}, {background}, {background}); cursor: none; }}
    canvas {{ display: block; }}
  </style>
</head>
<body>
  <!-- Synthetic payload: {safe_payload} -->
  <canvas id="transmitter" aria-label="Low-contrast synthetic laboratory pattern"></canvas>
  <script>
    "use strict";
    const modules = {matrix_json};
    const background = {background};
    const foreground = {foreground};
    const canvas = document.getElementById("transmitter");
    const context = canvas.getContext("2d", {{ alpha: false }});

    function drawTransmitter() {{
      const ratio = window.devicePixelRatio;
      canvas.width = Math.round(window.innerWidth * ratio);
      canvas.height = Math.round(window.innerHeight * ratio);
      context.imageSmoothingEnabled = false;
      context.fillStyle = `rgb(${{background}}, ${{background}}, ${{background}})`;
      context.fillRect(0, 0, canvas.width, canvas.height);

      const moduleCount = modules.length;
      const maximumPatternSize = Math.floor(Math.min(canvas.width, canvas.height) * 0.82);
      const moduleSize = Math.max(1, Math.floor(maximumPatternSize / moduleCount));
      const patternSize = moduleSize * moduleCount;
      const left = Math.floor((canvas.width - patternSize) / 2);
      const top = Math.floor((canvas.height - patternSize) / 2);
      context.fillStyle = `rgb(${{foreground}}, ${{foreground}}, ${{foreground}})`;

      for (let row = 0; row < moduleCount; row += 1) {{
        for (let column = 0; column < moduleCount; column += 1) {{
          if (modules[row][column] === 1) {{
            context.fillRect(
              left + column * moduleSize,
              top + row * moduleSize,
              moduleSize,
              moduleSize
            );
          }}
        }}
      }}
    }}

    window.addEventListener("resize", drawTransmitter);
    drawTransmitter();
  </script>
</body>
</html>
"""


def build_sequence_transmitter_html(
    qr_masks: tuple[NDArray[np.bool_], ...],
    transfer_id: str,
    background_intensity: int,
    contrast_delta: int,
    frame_milliseconds: int,
) -> str:
    """Build a transparent, keyboard-controllable player for synthetic fixture frames."""
    background, foreground = validate_intensities(background_intensity, contrast_delta)
    if not qr_masks:
        raise InvalidExperimentParameterError("At least one QR frame is required.")
    if frame_milliseconds < 250:
        raise InvalidExperimentParameterError(
            f"Frame duration must be at least 250 ms; received {frame_milliseconds}."
        )
    matrix_shape = qr_masks[0].shape
    if any(mask.shape != matrix_shape for mask in qr_masks):
        raise InvalidExperimentParameterError("All QR sequence frames must have the same shape.")
    matrix_json = json.dumps(
        [
            [[1 if value else 0 for value in row] for row in mask.tolist()]
            for mask in qr_masks
        ],
        separators=(",", ":"),
    )
    safe_transfer_id = html.escape(transfer_id, quote=True)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Optical Binary Fixture Lab</title>
  <style>
    html, body {{ width: 100%; height: 100%; margin: 0; overflow: hidden; }}
    body {{ background: rgb({background}, {background}, {background}); }}
    canvas {{ width: 100%; height: 100%; display: block; }}
    #status {{ position: fixed; left: 16px; bottom: 12px; color: #222;
      font: 14px system-ui, sans-serif; }}
  </style>
</head>
<body>
  <canvas id="transmitter" aria-label="Synthetic binary fixture QR sequence"></canvas>
  <div id="status">Academic fixture {safe_transfer_id}</div>
  <script>
    "use strict";
    const frames = {matrix_json};
    const background = {background};
    const foreground = {foreground};
    const frameMilliseconds = {frame_milliseconds};
    const canvas = document.getElementById("transmitter");
    const context = canvas.getContext("2d", {{ alpha: false }});
    const status = document.getElementById("status");
    let frameIndex = 0;
    let playing = false;
    let timer = null;

    function drawFrame() {{
      const ratio = window.devicePixelRatio;
      canvas.width = Math.round(window.innerWidth * ratio);
      canvas.height = Math.round(window.innerHeight * ratio);
      context.imageSmoothingEnabled = false;
      context.fillStyle = `rgb(${{background}}, ${{background}}, ${{background}})`;
      context.fillRect(0, 0, canvas.width, canvas.height);
      const modules = frames[frameIndex];
      const maximumPatternSize = Math.floor(Math.min(canvas.width, canvas.height) * 0.82);
      const moduleSize = Math.max(1, Math.floor(maximumPatternSize / modules.length));
      const patternSize = moduleSize * modules.length;
      const left = Math.floor((canvas.width - patternSize) / 2);
      const top = Math.floor((canvas.height - patternSize) / 2);
      context.fillStyle = `rgb(${{foreground}}, ${{foreground}}, ${{foreground}})`;
      for (let row = 0; row < modules.length; row += 1) {{
        for (let column = 0; column < modules.length; column += 1) {{
          if (modules[row][column] === 1) {{
            context.fillRect(
              left + column * moduleSize,
              top + row * moduleSize,
              moduleSize,
              moduleSize
            );
          }}
        }}
      }}
      status.textContent =
        `Academic fixture {safe_transfer_id} — frame ${{frameIndex + 1}}/${{frames.length}} — ` +
        (playing ? "playing" : "paused");
    }}

    function advance(delta) {{
      frameIndex = (frameIndex + delta + frames.length) % frames.length;
      drawFrame();
    }}

    function setPlaying(nextPlaying) {{
      playing = nextPlaying;
      if (timer !== null) {{
        window.clearInterval(timer);
        timer = null;
      }}
      if (playing) {{
        timer = window.setInterval(() => advance(1), frameMilliseconds);
      }}
      drawFrame();
    }}

    window.addEventListener("resize", drawFrame);
    window.addEventListener("keydown", (event) => {{
      if (event.code === "Space") {{
        event.preventDefault();
        setPlaying(!playing);
      }} else if (event.code === "ArrowRight") {{
        setPlaying(false);
        advance(1);
      }} else if (event.code === "ArrowLeft") {{
        setPlaying(false);
        advance(-1);
      }}
    }});
    drawFrame();
  </script>
</body>
</html>
"""


def write_text(text: str, output_path: Path) -> None:
    """Write UTF-8 text and make parent directories when required."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
