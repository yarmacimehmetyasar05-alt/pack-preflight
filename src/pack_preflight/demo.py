from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import RectangleObject


PT_PER_MM = 72.0 / 25.4


def _pt(mm: float) -> float:
    return mm * PT_PER_MM


def _add_boxed_page(
    writer: PdfWriter,
    *,
    trim_width_mm: float,
    trim_height_mm: float,
    bleed_mm: float,
) -> None:
    media_width = trim_width_mm + (2 * bleed_mm)
    media_height = trim_height_mm + (2 * bleed_mm)

    page = writer.add_blank_page(
        width=_pt(media_width),
        height=_pt(media_height),
    )

    trim = RectangleObject(
        [
            _pt(bleed_mm),
            _pt(bleed_mm),
            _pt(bleed_mm + trim_width_mm),
            _pt(bleed_mm + trim_height_mm),
        ]
    )
    bleed = RectangleObject(
        [0, 0, _pt(media_width), _pt(media_height)]
    )

    page.trimbox = trim
    page.bleedbox = bleed


def generate_demo_pdfs(output_dir: str | Path) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    paths = {
        "clean": output / "clean-explicit-boxes.pdf",
        "zero_bleed": output / "zero-bleed-warning.pdf",
        "mixed_sizes": output / "mixed-page-sizes.pdf",
        "encrypted": output / "encrypted-failure.pdf",
    }

    clean = PdfWriter()
    _add_boxed_page(
        clean,
        trim_width_mm=210.0,
        trim_height_mm=297.0,
        bleed_mm=3.0,
    )
    with paths["clean"].open("wb") as handle:
        clean.write(handle)

    zero_bleed = PdfWriter()
    _add_boxed_page(
        zero_bleed,
        trim_width_mm=210.0,
        trim_height_mm=297.0,
        bleed_mm=0.0,
    )
    with paths["zero_bleed"].open("wb") as handle:
        zero_bleed.write(handle)

    mixed = PdfWriter()
    _add_boxed_page(
        mixed,
        trim_width_mm=210.0,
        trim_height_mm=297.0,
        bleed_mm=3.0,
    )
    _add_boxed_page(
        mixed,
        trim_width_mm=148.0,
        trim_height_mm=210.0,
        bleed_mm=3.0,
    )
    with paths["mixed_sizes"].open("wb") as handle:
        mixed.write(handle)

    encrypted = PdfWriter()
    _add_boxed_page(
        encrypted,
        trim_width_mm=210.0,
        trim_height_mm=297.0,
        bleed_mm=3.0,
    )
    encrypted.encrypt("pack-preflight-demo")
    with paths["encrypted"].open("wb") as handle:
        encrypted.write(handle)

    return paths
