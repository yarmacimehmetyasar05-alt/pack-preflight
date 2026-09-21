from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    RectangleObject,
    TextStringObject,
)

from pack_preflight.core import inspect_pdf


def _write_image_pdf(
    path: Path,
    *,
    pixel_width: int,
    pixel_height: int,
    placed_width_pt: float = 72.0,
    placed_height_pt: float = 72.0,
    color_space: str = "/DeviceGray",
) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    page.trimbox = RectangleObject([18, 18, 282, 282])
    page.bleedbox = RectangleObject([9, 9, 291, 291])

    image = DecodedStreamObject()
    components = 3 if color_space == "/DeviceRGB" else 4 if color_space == "/DeviceCMYK" else 1
    image.set_data(bytes(pixel_width * pixel_height * components))
    image.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(pixel_width),
            NameObject("/Height"): NumberObject(pixel_height),
            NameObject("/ColorSpace"): NameObject(color_space),
            NameObject("/BitsPerComponent"): NumberObject(8),
        }
    )
    image_ref = writer._add_object(image)

    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/XObject"): DictionaryObject(
                {NameObject("/Im1"): image_ref}
            )
        }
    )

    content = DecodedStreamObject()
    content.set_data(
        (
            "q\n"
            f"{placed_width_pt} 0 0 {placed_height_pt} 0 0 cm\n"
            "/Im1 Do\n"
            "Q\n"
        ).encode("ascii")
    )
    page[NameObject("/Contents")] = writer._add_object(content)

    with path.open("wb") as fh:
        writer.write(fh)


def _write_content_pdf(
    path: Path,
    content_bytes: bytes,
    *,
    resources: DictionaryObject | None = None,
) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    page.trimbox = RectangleObject([18, 18, 282, 282])
    page.bleedbox = RectangleObject([9, 9, 291, 291])
    if resources is not None:
        page[NameObject("/Resources")] = resources

    content = DecodedStreamObject()
    content.set_data(content_bytes)
    page[NameObject("/Contents")] = writer._add_object(content)

    with path.open("wb") as fh:
        writer.write(fh)


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


def test_effective_image_dpi_below_default_threshold_is_reported(tmp_path: Path) -> None:
    pdf = tmp_path / "low-res-image.pdf"
    _write_image_pdf(pdf, pixel_width=300, pixel_height=300)

    report = inspect_pdf(pdf)

    finding = next(
        f
        for f in report["findings"]
        if f["code"] == "image_effective_dpi_below_threshold"
    )
    assert finding["severity"] == "warning"
    assert finding["page"] == 1
    assert "300.0 x 300.0 dpi" in finding["message"]
    assert "350.0 dpi" in finding["message"]


def test_effective_image_dpi_above_default_threshold_is_not_reported(tmp_path: Path) -> None:
    pdf = tmp_path / "high-res-image.pdf"
    _write_image_pdf(pdf, pixel_width=400, pixel_height=400)

    report = inspect_pdf(pdf)

    assert not any(
        f["code"] == "image_effective_dpi_below_threshold"
        for f in report["findings"]
    )


def test_effective_image_dpi_threshold_is_configurable(tmp_path: Path) -> None:
    pdf = tmp_path / "custom-threshold.pdf"
    _write_image_pdf(pdf, pixel_width=300, pixel_height=300)

    report = inspect_pdf(pdf, min_image_dpi=250.0)

    assert not any(
        f["code"] == "image_effective_dpi_below_threshold"
        for f in report["findings"]
    )


def test_used_rgb_vector_content_is_reported(tmp_path: Path) -> None:
    pdf = tmp_path / "rgb-vector.pdf"
    _write_content_pdf(
        pdf,
        b"0.1 0.2 0.3 rg 10 10 40 40 re f\n",
    )

    report = inspect_pdf(pdf)

    assert any(
        f["code"] == "rgb_vector_content_detected"
        for f in report["findings"]
    )
    usage = report["pages"][0]["color_usage"]
    assert usage["rgb"]["vector"] == 1
    assert usage["rgb"]["spaces"] == ["DeviceRGB"]


def test_unused_rgb_resource_does_not_trigger_warning(tmp_path: Path) -> None:
    pdf = tmp_path / "unused-rgb-resource.pdf"
    resources = DictionaryObject(
        {
            NameObject("/ColorSpace"): DictionaryObject(
                {NameObject("/UnusedRGB"): NameObject("/DeviceRGB")}
            )
        }
    )
    _write_content_pdf(
        pdf,
        b"0 0 0 1 k 10 10 40 40 re f\n",
        resources=resources,
    )

    report = inspect_pdf(pdf)

    assert not any(
        f["code"].startswith("rgb_")
        for f in report["findings"]
    )
    usage = report["pages"][0]["color_usage"]
    assert usage["cmyk"]["vector"] == 1


def test_rgb_image_content_is_reported(tmp_path: Path) -> None:
    pdf = tmp_path / "rgb-image.pdf"
    _write_image_pdf(
        pdf,
        pixel_width=400,
        pixel_height=400,
        color_space="/DeviceRGB",
    )

    report = inspect_pdf(pdf)

    assert any(
        f["code"] == "rgb_image_content_detected"
        for f in report["findings"]
    )
    usage = report["pages"][0]["color_usage"]
    assert usage["rgb"]["image"] == 1


def test_rgb_text_content_is_reported(tmp_path: Path) -> None:
    pdf = tmp_path / "rgb-text.pdf"
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): font}
            )
        }
    )
    _write_content_pdf(
        pdf,
        (
            b"0.1 0.2 0.3 rg "
            b"BT /F1 12 Tf 10 10 Td (RGB text) Tj ET\n"
        ),
        resources=resources,
    )

    report = inspect_pdf(pdf)

    assert any(
        f["code"] == "rgb_text_content_detected"
        for f in report["findings"]
    )
    usage = report["pages"][0]["color_usage"]
    assert usage["rgb"]["text"] == 1


def test_mixed_rgb_and_cmyk_page_is_reported(tmp_path: Path) -> None:
    pdf = tmp_path / "mixed-rgb-cmyk.pdf"
    _write_content_pdf(
        pdf,
        (
            b"0.1 0.2 0.3 rg 10 10 40 40 re f\n"
            b"0 0.5 0.5 0.1 k 60 10 40 40 re f\n"
        ),
    )

    report = inspect_pdf(pdf)

    assert any(
        f["code"] == "mixed_rgb_cmyk_page"
        for f in report["findings"]
    )
    usage = report["pages"][0]["color_usage"]
    assert usage["rgb"]["vector"] == 1
    assert usage["cmyk"]["vector"] == 1


def test_iccbased_rgb_usage_reports_profiled_rgb(tmp_path: Path) -> None:
    pdf = tmp_path / "icc-rgb.pdf"
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    page.trimbox = RectangleObject([18, 18, 282, 282])
    page.bleedbox = RectangleObject([9, 9, 291, 291])

    profile = DecodedStreamObject()
    profile.set_data(b"synthetic-icc-placeholder")
    profile[NameObject("/N")] = NumberObject(3)
    profile_ref = writer._add_object(profile)

    resources = DictionaryObject(
        {
            NameObject("/ColorSpace"): DictionaryObject(
                {
                    NameObject("/CS1"): ArrayObject(
                        [NameObject("/ICCBased"), profile_ref]
                    )
                }
            )
        }
    )
    page[NameObject("/Resources")] = resources

    content = DecodedStreamObject()
    content.set_data(b"/CS1 cs 0.1 0.2 0.3 scn 10 10 40 40 re f\n")
    page[NameObject("/Contents")] = writer._add_object(content)

    with pdf.open("wb") as fh:
        writer.write(fh)

    report = inspect_pdf(pdf)

    usage = report["pages"][0]["color_usage"]
    assert usage["rgb"]["vector"] == 1
    assert usage["rgb"]["spaces"] == ["ICCBased RGB"]
    finding = next(
        f
        for f in report["findings"]
        if f["code"] == "rgb_vector_content_detected"
    )
    assert "ICCBased RGB" in finding["message"]


def _write_black_text_pdf(
    path: Path,
    *,
    c: float,
    m: float,
    y: float,
    k: float,
    font_size: float,
) -> None:
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type3"),
        }
    )
    resources = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): font}
            )
        }
    )
    content = (
        f"{c} {m} {y} {k} k "
        f"BT /F1 {font_size} Tf 10 10 Td (Black text) Tj ET\n"
    ).encode("ascii")
    _write_content_pdf(path, content, resources=resources)


def test_k_only_black_text_is_classified_without_rich_black_warning(
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "k-only-black-text.pdf"
    _write_black_text_pdf(
        pdf,
        c=0.0,
        m=0.0,
        y=0.0,
        k=1.0,
        font_size=8.0,
    )

    report = inspect_pdf(pdf)

    black_text = report["pages"][0]["black_text"]
    assert black_text["k_only"]["occurrences"] == 1
    assert black_text["composite"]["occurrences"] == 0
    assert black_text["k_only"]["constructions"][0]["cmyk_percent"] == [
        0.0,
        0.0,
        0.0,
        100.0,
    ]
    assert not any(
        finding["code"].startswith("rich_black_")
        for finding in report["findings"]
    )


def test_small_rich_black_text_is_a_register_risk_warning(tmp_path: Path) -> None:
    pdf = tmp_path / "small-rich-black-text.pdf"
    _write_black_text_pdf(
        pdf,
        c=0.4,
        m=0.0,
        y=0.0,
        k=1.0,
        font_size=8.0,
    )

    report = inspect_pdf(pdf)

    black_text = report["pages"][0]["black_text"]
    assert black_text["composite"]["occurrences"] == 1
    finding = next(
        finding
        for finding in report["findings"]
        if finding["code"] == "rich_black_small_text"
    )
    assert finding["severity"] == "warning"
    assert finding["page"] == 1
    assert "C40 M0 Y0 K100" in finding["message"]
    assert "8.00 pt" in finding["message"]
    assert "register variation" in finding["message"]


def test_large_display_rich_black_text_is_informational(tmp_path: Path) -> None:
    pdf = tmp_path / "display-rich-black-text.pdf"
    _write_black_text_pdf(
        pdf,
        c=0.4,
        m=0.0,
        y=0.0,
        k=1.0,
        font_size=36.0,
    )

    report = inspect_pdf(pdf)

    finding = next(
        finding
        for finding in report["findings"]
        if finding["code"] == "rich_black_display_text"
    )
    assert finding["severity"] == "info"
    assert "C40 M0 Y0 K100" in finding["message"]
    assert "36.00 pt" in finding["message"]
    assert not any(
        finding["code"] == "rich_black_small_text"
        for finding in report["findings"]
    )
