from pathlib import Path

from pack_preflight.report import render_html_report, write_html_report


def _sample_report() -> dict:
    return {
        "file": "artwork.pdf",
        "ok": True,
        "page_count": 1,
        "pages": [
            {
                "page": 1,
                "trim_width_mm": 210.0,
                "trim_height_mm": 297.0,
                "trimbox_explicit": True,
                "bleedbox_explicit": True,
            }
        ],
        "pdfx": {"version": "PDF/X-4", "conformance": "PDF/X-4"},
        "output_intents": [
            {
                "subtype": "/GTS_PDFX",
                "output_condition_identifier": "FOGRA39",
                "registry_name": "http://www.color.org",
                "info": "ISO Coated v2",
                "has_destination_profile": False,
            }
        ],
        "spot_colors": ["CutContour"],
        "findings": [
            {
                "code": "output_intent_missing?",
                "severity": "info",
                "message": "Example <unsafe> message",
                "page": None,
            }
        ],
    }


def test_render_html_report_contains_key_sections_and_escapes_html() -> None:
    html = render_html_report(_sample_report())

    assert "pack-preflight report" in html
    assert "PDF/X-4" in html
    assert "FOGRA39" in html
    assert "210.00" in html
    assert "CutContour" in html
    assert "Example &lt;unsafe&gt; message" in html
    assert "Example <unsafe> message" not in html


def test_write_html_report(tmp_path: Path) -> None:
    output = tmp_path / "report.html"
    written = write_html_report(_sample_report(), output)

    assert written == output
    assert output.exists()
    assert "artwork.pdf" in output.read_text(encoding="utf-8")
