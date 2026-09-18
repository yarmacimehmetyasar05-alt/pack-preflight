from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject


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


def _resource_has_rgb(obj: Any, seen: set[int]) -> bool:
    obj = _resolve(obj)
    identity = id(obj)
    if identity in seen:
        return False
    seen.add(identity)

    if isinstance(obj, NameObject):
        return str(obj) in {"/DeviceRGB", "/CalRGB"}

    if isinstance(obj, str):
        return obj in {"/DeviceRGB", "/CalRGB"}

    if isinstance(obj, ArrayObject):
        return any(_resource_has_rgb(item, seen) for item in obj)

    if isinstance(obj, DictionaryObject):
        for key, value in obj.items():
            if str(key) == "/ColorSpace" and _resource_has_rgb(value, seen):
                return True
            if str(key) in {"/Resources", "/XObject", "/Pattern", "/Shading"}:
                if _resource_has_rgb(value, seen):
                    return True
        return False

    return False


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


def inspect_pdf(path: str | Path, min_bleed_mm: float = 3.0) -> dict[str, Any]:
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
                "page_count": len(reader.pages),
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

        page_summaries.append(
            {
                "page": index,
                "trim_width_mm": trim_w_rounded,
                "trim_height_mm": trim_h_rounded,
                "trimbox_explicit": trimbox_explicit,
                "bleedbox_explicit": bleedbox_explicit,
            }
        )

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
        if isinstance(resources, DictionaryObject):
            if _resource_has_rgb(resources, set()):
                findings.append(
                    Finding(
                        "rgb_colorspace_detected",
                        "warning",
                        "RGB color space detected in page resources.",
                        index,
                    )
                )

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
