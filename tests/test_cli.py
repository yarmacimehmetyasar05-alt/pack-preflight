import json
from pathlib import Path

import pytest

from pack_preflight import cli


def _report(path: str, ok: bool = True) -> dict:
    return {
        "file": str(path),
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
        return _report(path, ok=Path(path).name != "bad.pdf")

    monkeypatch.setattr(cli, "inspect_pdf", fake_inspect)

    exit_code = cli.run(["good.pdf", "bad.pdf", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert [Path(item["file"]).name for item in payload] == ["good.pdf", "bad.pdf"]
    assert [item["ok"] for item in payload] == [True, False]


def test_multiple_files_text_uses_compact_summary(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "inspect_pdf", lambda path, min_bleed_mm: _report(path))

    exit_code = cli.run(["one.pdf", "two.pdf"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "PASS  one.pdf" in output
    assert "PASS  two.pdf" in output
    assert "pages=1" in output


def test_multiple_files_html_uses_batch_writer(monkeypatch, capsys, tmp_path) -> None:
    monkeypatch.setattr(cli, "inspect_pdf", lambda path, min_bleed_mm: _report(path))
    output = tmp_path / "batch.html"

    exit_code = cli.run(["one.pdf", "two.pdf", "--html", str(output)])

    assert exit_code == 0
    assert output.exists()
    html = output.read_text(encoding="utf-8")
    assert "pack-preflight batch report" in html
    assert "one.pdf" in html
    assert "two.pdf" in html
    assert "HTML report:" in capsys.readouterr().out


def test_collect_pdf_inputs_expands_directory_and_ignores_non_pdf(tmp_path) -> None:
    (tmp_path / "B.PDF").write_bytes(b"")
    (tmp_path / "a.pdf").write_bytes(b"")
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")

    paths = cli.collect_pdf_inputs([str(tmp_path)])

    assert [Path(path).name for path in paths] == ["a.pdf", "B.PDF"]


def test_collect_pdf_inputs_recursive_controls_nested_directories(tmp_path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (tmp_path / "top.pdf").write_bytes(b"")
    (nested / "inside.pdf").write_bytes(b"")

    flat = cli.collect_pdf_inputs([str(tmp_path)], recursive=False)
    recursive = cli.collect_pdf_inputs([str(tmp_path)], recursive=True)

    assert [Path(path).name for path in flat] == ["top.pdf"]
    assert sorted(Path(path).name for path in recursive) == ["inside.pdf", "top.pdf"]


def test_collect_pdf_inputs_deduplicates_direct_and_discovered_file(tmp_path) -> None:
    pdf = tmp_path / "same.pdf"
    pdf.write_bytes(b"")

    paths = cli.collect_pdf_inputs([str(tmp_path), str(pdf)])

    assert paths == [str(pdf)]


def test_empty_directory_is_a_parser_error(tmp_path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.run([str(tmp_path)])

    assert exc_info.value.code == 2
