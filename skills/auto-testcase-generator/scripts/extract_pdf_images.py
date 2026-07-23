#!/usr/bin/env python3
"""Extract unique useful images from a PDF.

This helper is optional and requires PyMuPDF. Do not install dependencies unless
the user approves the package, version, license, and install location.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

try:
    import fitz
except ImportError:
    print("PyMuPDF is required. Install with approval: pip install PyMuPDF")
    raise SystemExit(1)


def extract_unique_images(
    pdf_path: Path,
    output_dir: Path | None = None,
    min_width: int = 100,
    min_height: int = 100,
    min_size: int = 5120,
) -> list[dict[str, object]]:
    pdf_path = pdf_path.resolve()
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return []

    target_dir = output_dir.resolve() if output_dir else pdf_path.parent / "images"
    target_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    xrefs = set()
    for page in doc:
        for image in page.get_images():
            xrefs.add(image[0])

    seen_hashes: set[str] = set()
    saved: list[dict[str, object]] = []
    for xref in sorted(xrefs):
        try:
            pix = fitz.Pixmap(doc, xref)
            data = pix.tobytes()
            digest = hashlib.md5(data).hexdigest()
            if pix.width <= min_width or pix.height <= min_height or len(data) <= min_size or digest in seen_hashes:
                pix = None
                continue

            if pix.n - pix.alpha >= 4:
                converted = fitz.Pixmap(fitz.csRGB, pix)
                pix = converted

            filename = f"image_{len(saved) + 1:02d}_{pix.width}x{pix.height}.png"
            path = target_dir / filename
            pix.save(str(path))
            seen_hashes.add(digest)
            saved.append(
                {
                    "filename": filename,
                    "path": str(path),
                    "xref": xref,
                    "width": pix.width,
                    "height": pix.height,
                    "size": len(data),
                    "hash": digest[:8],
                }
            )
            pix = None
        except Exception as exc:
            print(f"skip xref={xref}: {exc}")

    doc.close()
    return saved


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python extract_pdf_images.py <input.pdf> [output-dir]")
        return 1

    min_width = int(os.environ.get("MIN_WIDTH", "100"))
    min_height = int(os.environ.get("MIN_HEIGHT", "100"))
    min_size = int(os.environ.get("MIN_SIZE", "5120"))
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    saved = extract_unique_images(Path(sys.argv[1]), output_dir, min_width, min_height, min_size)
    print(f"saved_images={len(saved)}")
    for image in saved:
        print(f"- {image['filename']} {image['width']}x{image['height']} {image['hash']}")
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
