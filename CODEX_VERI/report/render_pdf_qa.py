"""Render a PDF to page PNGs and contact sheets for visual QA."""

from __future__ import annotations

import argparse
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from pypdf import PdfReader


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(str(args.pdf))
    page_paths: list[Path] = []
    thumbs: list[Image.Image] = []

    for index, page in enumerate(pdf):
        image = page.render(scale=1.7).to_pil().convert("RGB")
        page_path = args.output / f"page-{index + 1:02d}.png"
        image.save(page_path)
        page_paths.append(page_path)
        thumb = image.copy()
        thumb.thumbnail((390, 550))
        thumbs.append(thumb)

    for sheet_index in range(0, len(thumbs), 4):
        group = thumbs[sheet_index : sheet_index + 4]
        canvas = Image.new("RGB", (840, 1180), "#d9dde2")
        draw = ImageDraw.Draw(canvas)
        for slot, thumb in enumerate(group):
            x = 20 + (slot % 2) * 410
            y = 35 + (slot // 2) * 570
            canvas.paste(thumb, (x, y))
            draw.text((x, y - 23), f"Page {sheet_index + slot + 1}", fill="black")
        canvas.save(args.output / f"contact-{sheet_index // 4 + 1:02d}.png")

    reader = PdfReader(str(args.pdf))
    extracted = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    (args.output / "extracted_text.txt").write_text(extracted, encoding="utf-8")
    print(f"pages={len(page_paths)}")
    print(f"metadata_title={reader.metadata.title if reader.metadata else ''}")
    print(f"render_dir={args.output.resolve()}")


if __name__ == "__main__":
    main()
