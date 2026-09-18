import json

import pytest

from pack_preflight import cli


def _report(path: str, ok: bool = True) -> dict:
    return {
        "file": path,
        "ok": ok,
        "page_count": 1,
        "pages": [],
        "pdfx": {},
        "output_intents": [],
        "spot_colors": [],
        "findings": [] if ok else [
            {
                "severity": "error",
                "code": "test_failure",
                "message": "Synthetic failure",
                "page": None,
            }
        ],
    }


def test_single_file_json_preserves_object_shape(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "inspect_pdf", lambda path, min_bleed_mm: _report(path))

    exit_code = cli.run(["one.pdf", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert isinstance(payload, dict)
    assert payload["file"] == "one.pdf"


def test_multiple_files_json_returns_array_and_combined_exit_code(
    monkeypatch, capsys
) -> None:
    def fake_inspect(path: str, min_bleed_mm: float) -> dict:
        return _report(path, ok=path != "bad.pdf")

    monkeypatch.setattr(cli, "inspect_pdf", fake_inspect)

    exit_code = cli.run(["good.pdf", "bad.pdf", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert [item["file"] for item in payload] == ["good.pdf", "bad.pdf"]
    assert [item["ok"] for item in payload] == [True, False]


def test_multiple_files_text_uses_compact_summary(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "inspect_pdf", lambda path, min_bleed_mm: _report(path))

    exit_code = cli.run(["one.pdf", "two.pdf"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "PASS  one.pdf" in output
    assert "PASS  two.pdf" in output
    assert "pages=1" in output


def test_html_rejects_multiple_files() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.run(["one.pdf", "two.pdf", "--html", "report.html"])

    assert exc_info.value.code == 2
