# Image And PDF Evidence

Use visual evidence only when it is part of the provided source set or has been captured through an approved tool.

## Screenshots And Designs

- Record screenshot filename, capture time if known, page name, and source ID.
- Extract visible controls, fields, states, dialogs, messages, and layout constraints.
- Treat screenshots and Figma frames as possibly stale unless the user confirms they are current.
- When visual evidence conflicts with live page or release scope, apply [source oracle policy](source-oracle-policy.md).

## PDF Images

Use `scripts/extract_pdf_images.py` only when the user asks to analyze embedded PDF images or when visual diagrams are needed for test design.

The script requires PyMuPDF and writes image files to the selected output directory. Do not install PyMuPDF without approval.

Recommended command:

```powershell
python scripts/extract_pdf_images.py <input.pdf> <output-images-dir>
```

Useful environment variables:

- `MIN_WIDTH`
- `MIN_HEIGHT`
- `MIN_SIZE`

## Diagram Mapping

- Flowcharts: map paths and decision branches.
- State diagrams: map states, transitions, invalid transitions, and rollback.
- Sequence diagrams: map request/response, async events, timeouts, and integration failures.
- UI mockups: map controls and visible expectations, not hidden business behavior.
