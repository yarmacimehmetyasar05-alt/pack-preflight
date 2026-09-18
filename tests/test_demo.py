from pack_preflight.core import inspect_pdf
from pack_preflight.demo import generate_demo_pdfs


def _codes(report: dict) -> set[str]:
    return {finding["code"] for finding in report.get("findings", [])}


def test_generated_demo_pdfs_have_expected_preflight_outcomes(tmp_path) -> None:
    paths = generate_demo_pdfs(tmp_path)

    clean = inspect_pdf(paths["clean"])
    zero_bleed = inspect_pdf(paths["zero_bleed"])
    mixed = inspect_pdf(paths["mixed_sizes"])
    encrypted = inspect_pdf(paths["encrypted"])

    assert clean["ok"] is True
    assert "bleed_below_minimum" not in _codes(clean)
    assert "inconsistent_page_size" not in _codes(clean)

    assert zero_bleed["ok"] is True
    assert "bleed_below_minimum" in _codes(zero_bleed)

    assert mixed["ok"] is True
    assert "inconsistent_page_size" in _codes(mixed)

    assert encrypted["ok"] is False
    assert "pdf_encrypted" in _codes(encrypted)
