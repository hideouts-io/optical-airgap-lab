# Synthetic Binary Transfer Lab

## Purpose and boundary

This exercise demonstrates that an optical QR channel carries bytes, not merely human-readable
strings. It transfers only a deliberately staged synthetic fixture between owned or explicitly
authorized machines. The implementation reads exclusively from `fixtures/`, writes exclusively
to `recovered/`, rejects symbolic links, and limits operational transfers to 256 bytes.

The 256-byte limit is intentional. This is an observable, reproducible classroom experiment,
not a bulk-transfer or file-collection tool. Do not use personal, confidential, credential,
keystroke, clipboard, browser, or third-party data.

## What the code transmits

Each QR contains a Base85 representation of one binary packet:

| Field | Size | Purpose |
|---|---:|---|
| Magic | 4 bytes | Identifies the `OAL1` laboratory format |
| Transfer ID | 8 bytes | First eight bytes of the fixture SHA-256 |
| Sequence | 1 byte | Zero-based packet position |
| Total | 1 byte | Number of packets in the transfer |
| Payload length | 1 byte | Number of fixture bytes in this packet |
| Payload | 1–14 bytes | The actual synthetic binary data |
| CRC32 | 4 bytes | Detects corruption within the packet |

Base85 makes arbitrary packet bytes interoperable with QR libraries that return decoded text.
It is transport encoding, not encryption. QR error correction repairs some visual damage, CRC32
rejects a damaged packet, and the final SHA-256 verifies the completely reassembled fixture.

The implementation is in
[`binary_transfer.py`](../src/optical_airgap_lab/binary_transfer.py). It uses pure functions for
packet creation, encoding, parsing, reassembly, and capacity estimation.

## Machine A: prepare the synthetic fixture

Install the project and create a deterministic 128-byte fixture from code:

```bash
git clone https://github.com/hideouts-io/optical-airgap-lab.git
cd optical-airgap-lab
uv sync --all-groups

./.venv/bin/python -c \
  'from pathlib import Path; Path("fixtures/sample.bin").write_bytes(bytes(range(128)))'
```

This produces a known byte sequence rather than copying a personal file into the experiment.

Render it as numbered low-contrast frames:

```bash
./.venv/bin/optical-render-fixture \
  --input fixtures/sample.bin \
  --frames artifacts/binary-001 \
  --html artifacts/binary-001.html \
  --background 248 \
  --contrast 20 \
  --frame-ms 1500
```

The command prints the original SHA-256 and writes:

- `artifacts/binary-001.html`: a full-screen frame player;
- `artifacts/binary-001/frame-NNN.png`: reference images;
- `artifacts/binary-001/manifest.json`: size, frame count, and expected hash.

Open the HTML on Machine A. It begins paused. Use the left and right arrow keys to select one
frame at a time, or Space to start and stop playback. The page visibly identifies itself as an
academic synthetic-fixture experiment.

## Optical path between the machines

Machine B must have a camera capable of photographing Machine A's display, or an owned camera
can serve as the capture intermediary:

```text
Machine A fixture
  -> checksummed packet frames
  -> low-contrast QR images on Machine A display
  -> owned camera photographs each frame
  -> original photographs placed in Machine B captures/run-001/
  -> QR reconstruction and packet validation on Machine B
  -> recovered/sample.bin
```

Capture at least one clear photograph of every distinct frame. Preserve the entire QR quiet
zone and use the original camera files. Duplicate captures are acceptable when they decode to
the same sequence and bytes. Missing or conflicting frames cause an explicit failure.

Write down the SHA-256 printed by Machine A. Treat it as experimental ground truth; it is not a
secret. On Machine B, place only the frame photographs in `captures/run-001/`, then run:

```bash
cd optical-airgap-lab

./.venv/bin/optical-recover-fixture \
  --captures captures/run-001 \
  --expected-sha256 REPLACE_WITH_THE_64_CHARACTER_HASH \
  --output recovered/sample.bin
```

The receiver fails if an image cannot be decoded, a packet CRC is wrong, sequences are missing,
transfers are mixed, or the final SHA-256 differs. Success means the bytes written to
`recovered/sample.bin` match the sender's fixture exactly.

## Verify the result independently

Run SHA-256 on both machines:

```bash
shasum -a 256 fixtures/sample.bin
shasum -a 256 recovered/sample.bin
```

For the deterministic fixture, this Python comparison should also print `True`:

```bash
./.venv/bin/python -c \
  'from pathlib import Path; print(Path("fixtures/sample.bin").read_bytes() == Path("recovered/sample.bin").read_bytes())'
```

Record the frame count, contrast, frame duration, display brightness, camera distance, camera
model, failures, retries, and both hashes. The useful result is the measured reliability, not
merely a successful transfer.

## Academic feasibility model for 15 MiB

The operational tool intentionally refuses a 15 MiB file. Its frame-count estimator performs
only arithmetic and never reads or transmits such a file:

```bash
./.venv/bin/optical-estimate \
  --bytes 15728640 \
  --frames-per-second 5 \
  --repetitions 1
```

With this deliberately conservative packet format, each unique frame carries 14 fixture bytes.
Fifteen mebibytes (`15 × 1024 × 1024 = 15,728,640` bytes) would therefore require 1,123,475
unique frames.

| Ideal decoded rate | No repetitions | Ideal duration |
|---:|---:|---:|
| 1 frame/s | 1,123,475 frames | about 13.00 days |
| 5 frames/s | 1,123,475 frames | about 62.42 hours |
| 10 frames/s | 1,123,475 frames | about 31.21 hours |

These are lower-bound calculations, not demonstrated performance. Exposure time, refresh-rate
interaction, dropped frames, synchronization, repeated packets, decoding failures, and physical
handling would increase the duration. The current experiment has validated a static frame, not
a sustained high-rate video channel. For an authorized 15 MB transfer, use AirDrop, removable
media, or an authenticated network protocol instead.
