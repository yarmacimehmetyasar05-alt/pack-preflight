from pathlib import Path

from pack_preflight.report import (
    render_html_batch_report,
    render_html_report,
    write_html_batch_report,
    write_html_report,
)


def _sample_report(file: str = "artwork.pdf", ok: bool = True) -> dict:
    return {
        "file": file,
        "ok": ok,
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
                "severity": "info" if ok else "error",
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


def test_render_html_batch_report_summarizes_files_and_escapes_names() -> None:
    reports = [
        _sample_report("good.pdf", ok=True),
        _sample_report("bad<name>.pdf", ok=False),
    ]

    html = render_html_batch_report(reports)

    assert "pack-preflight batch report" in html
    assert "<strong>Files</strong><br>2" in html
    assert "<strong>Passed</strong><br>1" in html
    assert "<strong>Failed</strong><br>1" in html
    assert "good.pdf" in html
    assert "bad&lt;name&gt;.pdf" in html
    assert "bad<name>.pdf" not in html
    assert "CutContour" in html


def test_write_html_batch_report(tmp_path: Path) -> None:
    output = tmp_path / "batch.html"
    written = write_html_batch_report(
        [_sample_report("one.pdf"), _sample_report("two.pdf")],
        output,
    )

    assert written == output
    assert output.exists()
    html = output.read_text(encoding="utf-8")
    assert "one.pdf" in html
    assert "two.pdf" in html
