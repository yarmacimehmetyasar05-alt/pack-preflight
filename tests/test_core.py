from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    NameObject,
    RectangleObject,
    TextStringObject,
)

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


def test_pdfx_metadata_and_output_intent_are_reported(tmp_path: Path) -> None:
    pdf = tmp_path / "pdfx-like.pdf"
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    page.trimbox = RectangleObject([18, 18, 282, 282])
    page.bleedbox = RectangleObject([9, 9, 291, 291])

    writer.add_metadata(
        {
            "/GTS_PDFXVersion": "PDF/X-4",
            "/GTS_PDFXConformance": "PDF/X-4",
        }
    )

    output_intent = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/OutputIntent"),
            NameObject("/S"): NameObject("/GTS_PDFX"),
            NameObject("/OutputConditionIdentifier"): TextStringObject("FOGRA39"),
            NameObject("/RegistryName"): TextStringObject("http://www.color.org"),
            NameObject("/Info"): TextStringObject("ISO Coated v2"),
        }
    )
    writer._root_object[NameObject("/OutputIntents")] = ArrayObject([output_intent])

    with pdf.open("wb") as fh:
        writer.write(fh)

    report = inspect_pdf(pdf)

    assert report["pdfx"]["version"] == "PDF/X-4"
    assert report["pdfx"]["conformance"] == "PDF/X-4"
    assert len(report["output_intents"]) == 1
    assert report["output_intents"][0]["subtype"] == "/GTS_PDFX"
    assert (
        report["output_intents"][0]["output_condition_identifier"] == "FOGRA39"
    )
    assert not any(
        f["code"] == "output_intent_missing" for f in report["findings"]
    )


def test_missing_output_intent_is_informational(tmp_path: Path) -> None:
    pdf = tmp_path / "plain.pdf"
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    page.trimbox = RectangleObject([18, 18, 282, 282])
    page.bleedbox = RectangleObject([9, 9, 291, 291])
    with pdf.open("wb") as fh:
        writer.write(fh)

    report = inspect_pdf(pdf)

    finding = next(
        f for f in report["findings"] if f["code"] == "output_intent_missing"
    )
    assert finding["severity"] == "info"
