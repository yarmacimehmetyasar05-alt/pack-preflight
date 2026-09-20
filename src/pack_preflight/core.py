from __future__ import annotations

from dataclasses import dataclass, asdict
from math import hypot
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.generic import (
    ArrayObject,
    ContentStream,
    DictionaryObject,
    IndirectObject,
    NameObject,
)


MM_PER_PT = 25.4 / 72.0


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    page: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _resolve(obj: Any) -> Any:
    return obj.get_object() if isinstance(obj, IndirectObject) else obj


def _box_mm(box: Any) -> tuple[float, float, float, float]:
    vals = [float(v) * MM_PER_PT for v in box]
    return tuple(vals)  # type: ignore[return-value]


def _as_text(value: Any) -> str | None:
    value = _resolve(value)
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _read_pdfx_metadata(reader: PdfReader) -> dict[str, str | None]:
    info = _resolve(reader.trailer.get("/Info"))
    if not isinstance(info, DictionaryObject):
        return {"version": None, "conformance": None}
    return {
        "version": _as_text(info.get("/GTS_PDFXVersion")),
        "conformance": _as_text(info.get("/GTS_PDFXConformance")),
    }


def _read_output_intents(reader: PdfReader) -> list[dict[str, Any]]:
    root = _resolve(reader.trailer.get("/Root"))
    if not isinstance(root, DictionaryObject):
        return []

    raw_intents = _resolve(root.get("/OutputIntents"))
    if not isinstance(raw_intents, ArrayObject):
        return []

    intents: list[dict[str, Any]] = []
    for raw in raw_intents:
        intent = _resolve(raw)
        if not isinstance(intent, DictionaryObject):
            continue
        intents.append(
            {
                "subtype": _as_text(intent.get("/S")),
                "output_condition_identifier": _as_text(
                    intent.get("/OutputConditionIdentifier")
                ),
                "registry_name": _as_text(intent.get("/RegistryName")),
                "info": _as_text(intent.get("/Info")),
                "has_destination_profile": "/DestOutputProfile" in intent,
            }
        )
    return intents


def _colorspace_info(
    obj: Any,
    resources: DictionaryObject | None = None,
    seen: set[int] | None = None,
) -> tuple[str, str]:
    """Return (kind, label) for a PDF color space.

    kind is one of rgb, cmyk, gray, spot, pattern, or other.
    """
    obj = _resolve(obj)
    seen = set() if seen is None else seen
    identity = id(obj)
    if identity in seen:
        return ("other", "recursive")
    seen.add(identity)

    name = str(obj) if isinstance(obj, (NameObject, str)) else None
    if name:
        if name == "/DeviceRGB":
            return ("rgb", "DeviceRGB")
        if name == "/DeviceCMYK":
            return ("cmyk", "DeviceCMYK")
        if name == "/DeviceGray":
            return ("gray", "DeviceGray")
        if name == "/Pattern":
            return ("pattern", "Pattern")

        if resources is not None:
            spaces = _resolve(resources.get("/ColorSpace"))
            if isinstance(spaces, DictionaryObject) and obj in spaces:
                return _colorspace_info(spaces.get(obj), resources, seen)
        return ("other", name.lstrip("/"))

    if isinstance(obj, ArrayObject) and obj:
        family = str(_resolve(obj[0]))
        if family == "/CalRGB":
            return ("rgb", "CalRGB")
        if family == "/CalGray":
            return ("gray", "CalGray")
        if family == "/ICCBased" and len(obj) >= 2:
            profile = _resolve(obj[1])
            if isinstance(profile, DictionaryObject):
                try:
                    components = int(profile.get("/N", 0))
                except (TypeError, ValueError):
                    components = 0
                if components == 3:
                    return ("rgb", "ICCBased RGB")
                if components == 4:
                    return ("cmyk", "ICCBased CMYK")
                if components == 1:
                    return ("gray", "ICCBased Gray")
            return ("other", "ICCBased")
        if family == "/Indexed" and len(obj) >= 2:
            kind, label = _colorspace_info(obj[1], resources, seen)
            return (kind, f"Indexed {label}")
        if family in {"/Separation", "/DeviceN"}:
            return ("spot", family.lstrip("/"))
        if family == "/Pattern":
            if len(obj) >= 2:
                kind, label = _colorspace_info(obj[1], resources, seen)
                return (kind, f"Pattern {label}")
            return ("pattern", "Pattern")

    return ("other", "unknown")


def _new_color_usage() -> dict[str, Any]:
    return {
        "rgb": {"image": 0, "vector": 0, "text": 0},
        "cmyk": {"image": 0, "vector": 0, "text": 0},
        "gray": {"image": 0, "vector": 0, "text": 0},
        "spaces": {"rgb": set(), "cmyk": set(), "gray": set()},
    }


def _record_color_usage(
    usage: dict[str, Any],
    kind: str,
    content_type: str,
    label: str,
) -> None:
    if kind not in {"rgb", "cmyk", "gray"}:
        return
    usage[kind][content_type] += 1
    usage["spaces"][kind].add(label)


def _resolved_named_colorspace(
    value: Any,
    resources: DictionaryObject,
) -> tuple[str, str]:
    return _colorspace_info(value, resources)


def _scan_color_usage(
    stream_obj: Any,
    resources_obj: Any,
    reader: PdfReader,
    usage: dict[str, Any],
    *,
    inherited_nonstroke: tuple[str, str] = ("gray", "DeviceGray"),
    inherited_stroke: tuple[str, str] = ("gray", "DeviceGray"),
    inherited_text_render_mode: int = 0,
    active_forms: set[int] | None = None,
    depth: int = 0,
) -> None:
    if stream_obj is None or depth > 8:
        return

    resources = _resolve(resources_obj)
    if not isinstance(resources, DictionaryObject):
        resources = DictionaryObject()

    try:
        content = ContentStream(stream_obj, reader)
    except Exception:
        return

    active_forms = set() if active_forms is None else active_forms
    nonstroke = inherited_nonstroke
    stroke = inherited_stroke
    text_render_mode = inherited_text_render_mode
    state_stack: list[tuple[tuple[str, str], tuple[str, str], int]] = []

    fill_ops = {b"f", b"F", b"f*"}
    stroke_ops = {b"S", b"s"}
    both_ops = {b"B", b"B*", b"b", b"b*"}
    text_show_ops = {b"Tj", b"TJ", b"'", b'"'}

    for operands, operator in content.operations:
        if operator == b"q":
            state_stack.append((nonstroke, stroke, text_render_mode))
            continue
        if operator == b"Q":
            if state_stack:
                nonstroke, stroke, text_render_mode = state_stack.pop()
            continue

        if operator == b"rg":
            nonstroke = ("rgb", "DeviceRGB")
            continue
        if operator == b"RG":
            stroke = ("rgb", "DeviceRGB")
            continue
        if operator == b"k":
            nonstroke = ("cmyk", "DeviceCMYK")
            continue
        if operator == b"K":
            stroke = ("cmyk", "DeviceCMYK")
            continue
        if operator == b"g":
            nonstroke = ("gray", "DeviceGray")
            continue
        if operator == b"G":
            stroke = ("gray", "DeviceGray")
            continue
        if operator == b"cs" and operands:
            nonstroke = _resolved_named_colorspace(operands[0], resources)
            continue
        if operator == b"CS" and operands:
            stroke = _resolved_named_colorspace(operands[0], resources)
            continue
        if operator == b"Tr" and operands:
            try:
                text_render_mode = int(operands[0])
            except (TypeError, ValueError):
                pass
            continue

        if operator in fill_ops:
            _record_color_usage(usage, nonstroke[0], "vector", nonstroke[1])
            continue
        if operator in stroke_ops:
            _record_color_usage(usage, stroke[0], "vector", stroke[1])
            continue
        if operator in both_ops:
            _record_color_usage(usage, nonstroke[0], "vector", nonstroke[1])
            _record_color_usage(usage, stroke[0], "vector", stroke[1])
            continue

        if operator in text_show_ops:
            if text_render_mode in {0, 2, 4, 6}:
                _record_color_usage(usage, nonstroke[0], "text", nonstroke[1])
            if text_render_mode in {1, 2, 5, 6}:
                _record_color_usage(usage, stroke[0], "text", stroke[1])
            continue

        if operator == b"sh" and operands:
            shadings = _resolve(resources.get("/Shading"))
            if isinstance(shadings, DictionaryObject):
                shading = _resolve(shadings.get(operands[0]))
                if isinstance(shading, DictionaryObject):
                    kind, label = _colorspace_info(
                        shading.get("/ColorSpace"), resources
                    )
                    _record_color_usage(usage, kind, "vector", label)
            continue

        if operator != b"Do" or not operands:
            continue

        xobjects = _resolve(resources.get("/XObject"))
        if not isinstance(xobjects, DictionaryObject):
            continue
        xobj = _resolve(xobjects.get(operands[0]))
        if not isinstance(xobj, DictionaryObject):
            continue

        subtype = str(xobj.get("/Subtype", ""))
        if subtype == "/Image":
            if bool(xobj.get("/ImageMask", False)):
                _record_color_usage(
                    usage, nonstroke[0], "image", nonstroke[1]
                )
            else:
                kind, label = _colorspace_info(xobj.get("/ColorSpace"), resources)
                _record_color_usage(usage, kind, "image", label)
            continue

        if subtype == "/Form":
            identity = id(xobj)
            if identity in active_forms:
                continue
            form_resources = _resolve(xobj.get("/Resources")) or resources
            active_forms.add(identity)
            _scan_color_usage(
                xobj,
                form_resources,
                reader,
                usage,
                inherited_nonstroke=nonstroke,
                inherited_stroke=stroke,
                inherited_text_render_mode=text_render_mode,
                active_forms=active_forms,
                depth=depth + 1,
            )
            active_forms.remove(identity)


def _color_usage_for_output(usage: dict[str, Any]) -> dict[str, Any]:
    return {
        kind: {
            **usage[kind],
            "spaces": sorted(usage["spaces"][kind]),
        }
        for kind in ("rgb", "cmyk", "gray")
    }


def _add_rgb_findings(
    findings: list[Finding],
    usage: dict[str, Any],
    page_number: int,
    *,
    has_output_intent: bool,
) -> None:
    rgb = usage["rgb"]
    total_rgb = sum(rgb.values())
    if not total_rgb:
        return

    spaces = ", ".join(sorted(usage["spaces"]["rgb"])) or "RGB"
    context = f"color spaces={spaces}; OutputIntent={'yes' if has_output_intent else 'no'}"

    labels = (
        ("image", "rgb_image_content_detected", "RGB raster image"),
        ("vector", "rgb_vector_content_detected", "RGB vector"),
        ("text", "rgb_text_content_detected", "RGB text"),
    )
    for content_type, code, label in labels:
        count = rgb[content_type]
        if count:
            findings.append(
                Finding(
                    code,
                    "warning",
                    (
                        f"Used {label} content detected "
                        f"({count} paint occurrence(s); {context})."
                    ),
                    page_number,
                )
            )

    if sum(usage["cmyk"].values()):
        findings.append(
            Finding(
                "mixed_rgb_cmyk_page",
                "warning",
                (
                    "RGB and CMYK content are both used on this page. "
                    "Final appearance depends on the color-management and RIP "
                    "conversion path; review the separation before production."
                ),
                page_number,
            )
        )


def _font_is_embedded(font_obj: Any) -> bool:
    font = _resolve(font_obj)
    if not isinstance(font, DictionaryObject):
        return True

    descriptor = font.get("/FontDescriptor")
    descriptor = _resolve(descriptor) if descriptor else None

    if descriptor and isinstance(descriptor, DictionaryObject):
        return any(k in descriptor for k in ("/FontFile", "/FontFile2", "/FontFile3"))

    descendants = font.get("/DescendantFonts")
    descendants = _resolve(descendants) if descendants else None
    if isinstance(descendants, ArrayObject):
        for child in descendants:
            child = _resolve(child)
            if isinstance(child, DictionaryObject):
                child_desc = child.get("/FontDescriptor")
                child_desc = _resolve(child_desc) if child_desc else None
                if isinstance(child_desc, DictionaryObject) and any(
                    k in child_desc for k in ("/FontFile", "/FontFile2", "/FontFile3")
                ):
                    return True

    subtype = str(font.get("/Subtype", ""))
    return subtype in {"/Type3"}


def _spot_colors_from_colorspace(obj: Any, found: set[str], seen: set[int]) -> None:
    obj = _resolve(obj)
    identity = id(obj)
    if identity in seen:
        return
    seen.add(identity)

    if isinstance(obj, ArrayObject):
        if len(obj) >= 2 and str(obj[0]) in {"/Separation", "/DeviceN"}:
            name = _resolve(obj[1])
            if isinstance(name, ArrayObject):
                found.update(str(x).lstrip("/") for x in name)
            else:
                found.add(str(name).lstrip("/"))
        for item in obj:
            _spot_colors_from_colorspace(item, found, seen)
    elif isinstance(obj, DictionaryObject):
        for value in obj.values():
            _spot_colors_from_colorspace(value, found, seen)


Matrix = tuple[float, float, float, float, float, float]
IDENTITY_MATRIX: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _concat_matrix(current: Matrix, new: Matrix) -> Matrix:
    a1, b1, c1, d1, e1, f1 = current
    a2, b2, c2, d2, e2, f2 = new
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _matrix_from_operands(operands: Any) -> Matrix | None:
    try:
        values = tuple(float(value) for value in operands)
    except (TypeError, ValueError):
        return None
    if len(values) != 6:
        return None
    return values  # type: ignore[return-value]


def _scan_image_placements(
    stream_obj: Any,
    resources_obj: Any,
    reader: PdfReader,
    page_number: int,
    min_image_dpi: float,
    findings: list[Finding],
    *,
    ctm: Matrix = IDENTITY_MATRIX,
    user_unit: float = 1.0,
    active_forms: set[int] | None = None,
    depth: int = 0,
) -> None:
    if stream_obj is None or depth > 8:
        return

    resources = _resolve(resources_obj)
    if not isinstance(resources, DictionaryObject):
        return

    try:
        content = ContentStream(stream_obj, reader)
    except Exception:
        return

    active_forms = set() if active_forms is None else active_forms
    current = ctm
    stack: list[Matrix] = []

    for operands, operator in content.operations:
        if operator == b"q":
            stack.append(current)
            continue
        if operator == b"Q":
            if stack:
                current = stack.pop()
            continue
        if operator == b"cm":
            matrix = _matrix_from_operands(operands)
            if matrix is not None:
                current = _concat_matrix(current, matrix)
            continue
        if operator != b"Do" or not operands:
            continue

        xobjects = _resolve(resources.get("/XObject"))
        if not isinstance(xobjects, DictionaryObject):
            continue

        xobj = _resolve(xobjects.get(operands[0]))
        if not isinstance(xobj, DictionaryObject):
            continue

        subtype = str(xobj.get("/Subtype", ""))
        if subtype == "/Image":
            try:
                width_px = float(xobj.get("/Width"))
                height_px = float(xobj.get("/Height"))
            except (TypeError, ValueError):
                continue

            placed_width_pt = hypot(current[0], current[1]) * user_unit
            placed_height_pt = hypot(current[2], current[3]) * user_unit
            if placed_width_pt <= 0 or placed_height_pt <= 0:
                continue

            dpi_x = width_px * 72.0 / placed_width_pt
            dpi_y = height_px * 72.0 / placed_height_pt
            effective_dpi = min(dpi_x, dpi_y)
            if effective_dpi + 1e-6 < min_image_dpi:
                findings.append(
                    Finding(
                        "image_effective_dpi_below_threshold",
                        "warning",
                        (
                            f"Image {operands[0]} effective resolution is "
                            f"{dpi_x:.1f} x {dpi_y:.1f} dpi; "
                            f"minimum is {min_image_dpi:.1f} dpi."
                        ),
                        page_number,
                    )
                )
            continue

        if subtype == "/Form":
            identity = id(xobj)
            if identity in active_forms:
                continue
            form_matrix = _matrix_from_operands(
                _resolve(xobj.get("/Matrix")) or IDENTITY_MATRIX
            ) or IDENTITY_MATRIX
            form_resources = xobj.get("/Resources") or resources
            active_forms.add(identity)
            _scan_image_placements(
                xobj,
                form_resources,
                reader,
                page_number,
                min_image_dpi,
                findings,
                ctm=_concat_matrix(current, form_matrix),
                user_unit=user_unit,
                active_forms=active_forms,
                depth=depth + 1,
            )
            active_forms.remove(identity)


def inspect_pdf(
    path: str | Path,
    min_bleed_mm: float = 3.0,
    min_image_dpi: float = 350.0,
) -> dict[str, Any]:
    pdf_path = Path(path)
    findings: list[Finding] = []
    spot_colors: set[str] = set()
    page_summaries: list[dict[str, Any]] = []

    try:
        reader = PdfReader(str(pdf_path))
    except Exception as exc:
        return {
            "file": str(pdf_path),
            "ok": False,
            "page_count": 0,
            "pages": [],
            "pdfx": {"version": None, "conformance": None},
            "output_intents": [],
            "spot_colors": [],
            "findings": [
                Finding("pdf_unreadable", "error", f"Cannot read PDF: {exc}").to_dict()
            ],
        }

    if reader.is_encrypted:
        try:
            unlocked = reader.decrypt("")
        except Exception:
            unlocked = 0
        if not unlocked:
            return {
                "file": str(pdf_path),
                "ok": False,
                "page_count": 0,
                "pages": [],
                "pdfx": {"version": None, "conformance": None},
                "output_intents": [],
                "spot_colors": [],
                "findings": [
                    Finding(
                        "pdf_encrypted",
                        "error",
                        "PDF is encrypted and cannot be preflighted without a password.",
                    ).to_dict()
                ],
            }

    pdfx = _read_pdfx_metadata(reader)
    output_intents = _read_output_intents(reader)

    if not output_intents:
        findings.append(
            Finding(
                "output_intent_missing",
                "info",
                "No catalog OutputIntent entry was found. This tool does not treat that alone as a conformance failure.",
            )
        )

    trim_sizes: list[tuple[float, float]] = []

    for index, page in enumerate(reader.pages, start=1):
        trimbox_explicit = "/TrimBox" in page
        bleedbox_explicit = "/BleedBox" in page

        if not trimbox_explicit:
            findings.append(
                Finding(
                    "trimbox_not_explicit",
                    "warning",
                    "TrimBox is not explicitly defined; a PDF fallback box is being used.",
                    index,
                )
            )

        if not bleedbox_explicit:
            findings.append(
                Finding(
                    "bleedbox_not_explicit",
                    "warning",
                    "BleedBox is not explicitly defined; a PDF fallback box is being used.",
                    index,
                )
            )

        trim = page.trimbox or page.mediabox
        bleed = page.bleedbox or page.mediabox

        tx0, ty0, tx1, ty1 = _box_mm(trim)
        bx0, by0, bx1, by1 = _box_mm(bleed)
        trim_w, trim_h = tx1 - tx0, ty1 - ty0
        trim_w_rounded, trim_h_rounded = round(trim_w, 2), round(trim_h, 2)
        trim_sizes.append((trim_w_rounded, trim_h_rounded))

        page_summary = {
            "page": index,
            "trim_width_mm": trim_w_rounded,
            "trim_height_mm": trim_h_rounded,
            "trimbox_explicit": trimbox_explicit,
            "bleedbox_explicit": bleedbox_explicit,
        }
        page_summaries.append(page_summary)

        margins = {
            "left": tx0 - bx0,
            "bottom": ty0 - by0,
            "right": bx1 - tx1,
            "top": by1 - ty1,
        }
        too_small = {k: v for k, v in margins.items() if v + 1e-6 < min_bleed_mm}
        if too_small:
            details = ", ".join(f"{k}={v:.2f} mm" for k, v in too_small.items())
            findings.append(
                Finding(
                    "bleed_below_minimum",
                    "warning",
                    f"Bleed is below {min_bleed_mm:.2f} mm on: {details}.",
                    index,
                )
            )

        resources = _resolve(page.get("/Resources"))
        _scan_image_placements(
            page.get_contents(),
            resources,
            reader,
            index,
            min_image_dpi,
            findings,
            user_unit=float(page.get("/UserUnit", 1.0)),
        )

        color_usage = _new_color_usage()
        _scan_color_usage(
            page.get_contents(),
            resources,
            reader,
            color_usage,
        )
        page_summary["color_usage"] = _color_usage_for_output(color_usage)
        _add_rgb_findings(
            findings,
            color_usage,
            index,
            has_output_intent=bool(output_intents),
        )

        if isinstance(resources, DictionaryObject):
            fonts = _resolve(resources.get("/Font")) if resources.get("/Font") else None
            if isinstance(fonts, DictionaryObject):
                for font_name, font_obj in fonts.items():
                    if not _font_is_embedded(font_obj):
                        findings.append(
                            Finding(
                                "font_not_embedded",
                                "error",
                                f"Font {font_name} does not appear to be embedded.",
                                index,
                            )
                        )

            colorspaces = resources.get("/ColorSpace")
            if colorspaces:
                _spot_colors_from_colorspace(colorspaces, spot_colors, set())

    if len(set(trim_sizes)) > 1:
        findings.append(
            Finding(
                "inconsistent_page_size",
                "warning",
                f"Multiple TrimBox sizes detected: {sorted(set(trim_sizes))}.",
            )
        )

    has_errors = any(f.severity == "error" for f in findings)
    return {
        "file": str(pdf_path),
        "ok": not has_errors,
        "page_count": len(reader.pages),
        "pages": page_summaries,
        "pdfx": pdfx,
        "output_intents": output_intents,
        "spot_colors": sorted(spot_colors),
        "findings": [f.to_dict() for f in findings],
    }
