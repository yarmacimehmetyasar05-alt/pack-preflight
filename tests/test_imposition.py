from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    RectangleObject,
)

from pack_preflight.imposition import collect_page_imposition_evidence


def _write_slug_pdf(
    path: Path,
    *,
    text: str | None,
    x: float = 20.0,
    y: float = 20.0,
    rotate: int = 0,
) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=300)
    page.trimbox = RectangleObject([50, 50, 350, 250])
    page.bleedbox = RectangleObject([40, 40, 360, 260])
    if rotate:
        page[NameObject("/Rotate")] = NumberObject(rotate)

    if text is not None:
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): font}
                )
            }
        )
        stream = DecodedStreamObject()
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream.set_data(
            (
                "BT\n"
                "/F1 10 Tf\n"
                f"{x} {y} Td\n"
                f"({escaped}) Tj\n"
                "ET\n"
            ).encode("latin-1")
        )
        page[NameObject("/Contents")] = writer._add_object(stream)

    with path.open("wb") as fh:
        writer.write(fh)


def _evidence(path: Path) -> dict:
    reader = PdfReader(str(path))
    return collect_page_imposition_evidence(reader.pages[0])


def test_collects_physical_sheet_size_and_rotation(tmp_path: Path) -> None:
    pdf = tmp_path / "rotated-sheet.pdf"
    _write_slug_pdf(pdf, text=None, rotate=90)

    evidence = _evidence(pdf)

    assert evidence["media_width_mm"] == 141.11
    assert evidence["media_height_mm"] == 105.83
    assert evidence["trim_width_mm"] == 105.83
    assert evidence["trim_height_mm"] == 70.56
    assert evidence["rotation"] == 90
    assert evidence["pairing_status"] == "not_evaluated"


def test_extracts_slug_identity_outside_trimbox(tmp_path: Path) -> None:
    pdf = tmp_path / "sig3-front.pdf"
    _write_slug_pdf(pdf, text="Job 721 - Sig 3 - FRONT - folio 16 1 2 15")

    evidence = _evidence(pdf)

    assert evidence["extractable_text_present"] is True
    assert evidence["slug_text"] == ["Job 721 - Sig 3 - FRONT - folio 16 1 2 15"]
    assert evidence["signature_ids"] == ["3"]
    assert evidence["side_ids"] == ["front"]
    assert "16" in evidence["numeric_tokens"]
    assert "15" in evidence["numeric_tokens"]
    assert evidence["text_fragments"][0]["outside_trim"] is True


def test_text_inside_trim_is_not_treated_as_slug_identity(tmp_path: Path) -> None:
    pdf = tmp_path / "inside-artwork.pdf"
    _write_slug_pdf(pdf, text="Sig 9 FRONT", x=100, y=100)

    evidence = _evidence(pdf)

    assert evidence["extractable_text_present"] is True
    assert evidence["slug_text"] == []
    assert evidence["signature_ids"] == []
    assert evidence["side_ids"] == []
    assert evidence["text_fragments"][0]["outside_trim"] is False


def test_missing_extractable_slug_is_not_a_pairing_mismatch(tmp_path: Path) -> None:
    pdf = tmp_path / "outlined-or-empty-slug.pdf"
    _write_slug_pdf(pdf, text=None)

    evidence = _evidence(pdf)

    assert evidence["extractable_text_present"] is False
    assert evidence["slug_text"] == []
    assert evidence["signature_ids"] == []
    assert evidence["side_ids"] == []
    assert evidence["pairing_status"] == "not_evaluated"
