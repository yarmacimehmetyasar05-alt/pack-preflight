from pathlib import Path

from pypdf import PdfWriter

from pack_preflight.core import inspect_pdf


def test_clean_single_page_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "simple.pdf"
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    page.trimbox = [18, 18, 282, 282]
    page.bleedbox = [9, 9, 291, 291]
    with pdf.open("wb") as fh:
        writer.write(fh)

    report = inspect_pdf(pdf, min_bleed_mm=3.0)

    assert report["page_count"] == 1
    assert report["ok"] is True
    assert not any(f["code"] == "bleed_below_minimum" for f in report["findings"])


def test_bleed_warning(tmp_path: Path) -> None:
    pdf = tmp_path / "no-bleed.pdf"
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    page.trimbox = [0, 0, 300, 300]
    page.bleedbox = [0, 0, 300, 300]
    with pdf.open("wb") as fh:
        writer.write(fh)

    report = inspect_pdf(pdf, min_bleed_mm=3.0)

    assert any(f["code"] == "bleed_below_minimum" for f in report["findings"])
