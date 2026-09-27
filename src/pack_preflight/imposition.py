from __future__ import annotations

import re
from typing import Any


MM_PER_PT = 25.4 / 72.0

_SIGNATURE_RE = re.compile(
    r"\b(?:sig(?:nature)?|form|forma|sheet)\s*[-:#]?\s*"
    r"([A-Z0-9]+(?:[-_.][A-Z0-9]+)*)\b",
    re.IGNORECASE,
)
_SIDE_PATTERNS = (
    (re.compile(r"\bfront\b", re.IGNORECASE), "front"),
    (re.compile(r"\brecto\b", re.IGNORECASE), "front"),
    (re.compile(r"\b(?:on|ön)\b", re.IGNORECASE), "front"),
    (re.compile(r"\bback\b", re.IGNORECASE), "back"),
    (re.compile(r"\bverso\b", re.IGNORECASE), "back"),
    (re.compile(r"\barka\b", re.IGNORECASE), "back"),
)
_NUMBER_RE = re.compile(r"(?<![A-Za-z])\d{1,4}(?![A-Za-z])")


def _box_points(box: Any) -> tuple[float, float, float, float]:
    return tuple(float(value) for value in box)  # type: ignore[return-value]


def _box_size_mm(box: Any, user_unit: float) -> tuple[float, float]:
    x0, y0, x1, y1 = _box_points(box)
    scale = MM_PER_PT * user_unit
    return ((x1 - x0) * scale, (y1 - y0) * scale)


def _transform_text_origin(cm: Any, tm: Any) -> tuple[float, float]:
    """Return text origin in page user-space coordinates.

    pypdf supplies the current transformation matrix (cm) and text matrix (tm)
    to visitor_text. The text origin is tm's translation transformed by cm.
    """
    try:
        x = float(tm[4])
        y = float(tm[5])
        a, b, c, d, e, f = (float(value) for value in cm)
    except (TypeError, ValueError, IndexError):
        return (0.0, 0.0)
    return (a * x + c * y + e, b * x + d * y + f)


def _outside_box(x: float, y: float, box: Any) -> bool:
    x0, y0, x1, y1 = _box_points(box)
    return x < x0 or x > x1 or y < y0 or y > y1


def _unique_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _normalize_identity_text(texts: list[str]) -> dict[str, Any]:
    signature_ids: list[str] = []
    side_ids: list[str] = []
    numeric_tokens: list[str] = []

    for text in texts:
        signature_ids.extend(match.group(1) for match in _SIGNATURE_RE.finditer(text))
        for pattern, normalized in _SIDE_PATTERNS:
            if pattern.search(text):
                side_ids.append(normalized)
        numeric_tokens.extend(_NUMBER_RE.findall(text))

    return {
        "signature_ids": _unique_preserving_order(signature_ids),
        "side_ids": _unique_preserving_order(side_ids),
        "numeric_tokens": _unique_preserving_order(numeric_tokens),
    }


def collect_page_imposition_evidence(page: Any) -> dict[str, Any]:
    """Collect objective imposed-sheet evidence without attempting pairing.

    Phase 1 deliberately does not decide which front belongs to which back. It
    records physical page evidence and extractable slug-like text so a later
    pairing layer can make decisions only when the evidence is strong enough.
    """
    user_unit = float(page.get("/UserUnit", 1.0))
    rotation = int(page.get("/Rotate", 0) or 0) % 360

    media = page.mediabox
    crop = page.cropbox or media
    trim = page.trimbox or crop

    media_width_mm, media_height_mm = _box_size_mm(media, user_unit)
    trim_width_mm, trim_height_mm = _box_size_mm(trim, user_unit)

    all_text: list[dict[str, Any]] = []
    outside_trim_text: list[str] = []

    def visitor_text(
        text: str,
        cm: Any,
        tm: Any,
        font_dict: Any,
        font_size: float,
    ) -> None:
        cleaned = " ".join(text.split())
        if not cleaned:
            return
        x, y = _transform_text_origin(cm, tm)
        outside_trim = _outside_box(x, y, trim)
        all_text.append(
            {
                "text": cleaned,
                "x": round(x, 3),
                "y": round(y, 3),
                "font_size": round(float(font_size), 3),
                "outside_trim": outside_trim,
            }
        )
        if outside_trim:
            outside_trim_text.append(cleaned)

    extraction_error: str | None = None
    try:
        page.extract_text(visitor_text=visitor_text)
    except Exception as exc:
        extraction_error = f"{type(exc).__name__}: {exc}"

    slug_text = _unique_preserving_order(outside_trim_text)
    normalized = _normalize_identity_text(slug_text)

    return {
        "media_width_mm": round(media_width_mm, 2),
        "media_height_mm": round(media_height_mm, 2),
        "trim_width_mm": round(trim_width_mm, 2),
        "trim_height_mm": round(trim_height_mm, 2),
        "rotation": rotation,
        "user_unit": user_unit,
        "extractable_text_present": bool(all_text),
        "text_extraction_error": extraction_error,
        "slug_text": slug_text,
        "signature_ids": normalized["signature_ids"],
        "side_ids": normalized["side_ids"],
        "numeric_tokens": normalized["numeric_tokens"],
        "text_fragments": all_text,
        "pairing_status": "not_evaluated",
    }
