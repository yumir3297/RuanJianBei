from __future__ import annotations

import math
import sys
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw


def main() -> None:
    pdf_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)
    pages_dir = output_dir / "pages"
    sheets_dir = output_dir / "sheets"
    pages_dir.mkdir(exist_ok=True)
    sheets_dir.mkdir(exist_ok=True)

    pdf = pdfium.PdfDocument(str(pdf_path))
    page_paths: list[Path] = []
    scale = 2.0
    for index in range(len(pdf)):
        page = pdf[index]
        bitmap = page.render(scale=scale, rotation=0)
        image = bitmap.to_pil().convert("RGB")
        path = pages_dir / f"page-{index + 1:03d}.png"
        image.save(path, quality=95)
        page_paths.append(path)

    per_sheet = 4
    for sheet_index in range(math.ceil(len(page_paths) / per_sheet)):
        group = page_paths[sheet_index * per_sheet : (sheet_index + 1) * per_sheet]
        images = [Image.open(path).convert("RGB") for path in group]
        thumb_width = 850
        thumbs = []
        for page_num, image in enumerate(images, start=sheet_index * per_sheet + 1):
            ratio = thumb_width / image.width
            resized = image.resize((thumb_width, int(image.height * ratio)))
            canvas = Image.new("RGB", (thumb_width + 24, resized.height + 54), "white")
            canvas.paste(resized, (12, 38))
            draw = ImageDraw.Draw(canvas)
            draw.text((12, 10), f"Page {page_num}", fill="black")
            thumbs.append(canvas)

        cell_w = max(image.width for image in thumbs)
        cell_h = max(image.height for image in thumbs)
        sheet = Image.new("RGB", (cell_w * 2, cell_h * 2), "#D5D9DE")
        for idx, image in enumerate(thumbs):
            x = (idx % 2) * cell_w
            y = (idx // 2) * cell_h
            sheet.paste(image, (x, y))
        sheet.save(sheets_dir / f"sheet-{sheet_index + 1:02d}.jpg", quality=90)

    print(f"PAGES={len(page_paths)} SHEETS={math.ceil(len(page_paths) / per_sheet)}")


if __name__ == "__main__":
    main()
