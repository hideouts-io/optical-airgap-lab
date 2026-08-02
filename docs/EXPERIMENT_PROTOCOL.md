# Physical Experiment Protocol

## Objective

Determine the smallest static bright-on-bright contrast difference that can be recovered from an
iPhone photograph of the test MacBook while transmitting only the synthetic identifier
`LAB-001`.

## Controlled variables

Record these values for every capture:

- MacBook model and display resolution
- Display brightness percentage
- True Tone and Night Shift state
- Browser and browser version
- Camera model
- Camera-to-display distance in centimeters
- Approximate horizontal and vertical angle
- Ambient lighting description
- Transmitter background and contrast values
- Original image dimensions and format

## Procedure

1. Run the automated tests before the physical experiment.
2. Generate a transmitter with contrast 20.
3. Open the transmitter in a full-screen browser.
4. Clean the display and remove direct reflections.
5. Capture the entire display straight-on, preserving a white margin around the QR.
6. Transfer the original photo without cropping, rescaling, messaging compression, or a
   screenshot intermediary.
7. Run `optical-decode` and preserve the original capture and reconstruction.
8. If decoding succeeds, repeat with contrasts 16, 12, 8, 6, and 5.
9. If decoding fails, repeat once at the same contrast before changing a controlled variable.
10. Record every result, including failures.

## Success criterion

A trial succeeds only when the offline decoder returns exactly `LAB-001`. Visual recognition of
the pattern or an iPhone QR notification is not the success criterion.

## Failure interpretation

- No iPhone notification: expected at low contrast; proceed to offline reconstruction.
- Pattern absent from photo: reduce display clipping or increase contrast.
- Pattern visible but decoder fails: preserve more quiet-zone margin, remove perspective, avoid
  glare, use the original photo, and increase contrast for the next baseline.
- Different payload decoded: stop and treat the run as a validation failure.

## Scope

Use only owned or explicitly authorized equipment in a controlled room. Do not encode personal,
confidential, credential, keystroke, or third-party information. Do not add persistence, hidden
collection, camera compromise, or network forwarding.
