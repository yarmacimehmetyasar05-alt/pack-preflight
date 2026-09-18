from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import RectangleObject

from pack_preflight.core import inspect_pdf


def test_clean_single_page_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "simple.pdf"
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    page.trimbox = RectangleObject([18, 18, 282, 282])
    page.bleedbox = RectangleObject([9, 9, 291, 291])
    with pdf.open("wb") as fh:
        writer.write(fh)

    report = inspect_pdf(pdf, min_bleed_mm=3.0)

    assert report["page_count"] == 1
    assert report["ok"] is True
    assert report["pages"][0]["trimbox_explicit"] is True
    assert report["pages"][0]["bleedbox_explicit"] is True
    assert not any(f["code"] == "bleed_below_minimum" for f in report["findings"])


def test_bleed_warning(tmp_path: Path) -> None:
    pdf = tmp_path / "no-bleed.pdf"
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    page.trimbox = RectangleObject([0, 0, 300, 300])
    page.bleedbox = RectangleObject([0, 0, 300, 300])
    with pdf.open("wb") as fh:
        writer.write(fh)

    report = inspect_pdf(pdf, min_bleed_mm=3.0)

    assert any(f["code"] == "bleed_below_minimum" for f in report["findings"])


def test_missing_explicit_page_boxes_are_reported(tmp_path: Path) -> None:
    pdf = tmp_path / "missing-boxes.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    with pdf.open("wb") as fh:
        writer.write(fh)

    report = inspect_pdf(pdf, min_bleed_mm=3.0)
    codes = {f["code"] for f in report["findings"]}

    assert "trimbox_not_explicit" in codes
    assert "bleedbox_not_explicit" in codes
    assert report["pages"][0]["trim_width_mm"] == 105.83
    assert report["pages"][0]["trim_height_mm"] == 105.83
    assert report["pages"][0]["trimbox_explicit"] is False
    assert report["pages"][0]["bleedbox_explicit"] is False
