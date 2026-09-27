from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


def _text(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return escape(str(value))


def _text_list(values: Any) -> str:
    if not values:
        return "-"
    return ", ".join(escape(str(value)) for value in values)


def _finding_count(report: dict[str, Any], severity: str) -> int:
    return sum(
        1
        for finding in report.get("findings", [])
        if finding.get("severity") == severity
    )


def _report_imposition_summary(report: dict[str, Any]) -> str:
    labels: list[str] = []
    for page in report.get("pages", []):
        evidence = page.get("imposition_evidence") or {}
        signatures = evidence.get("signature_ids") or []
        sides = evidence.get("side_ids") or []
        if not signatures and not sides:
            continue
        parts: list[str] = []
        if signatures:
            parts.append("sig=" + "/".join(str(value) for value in signatures))
        if sides:
            parts.append("side=" + "/".join(str(value) for value in sides))
        labels.append(f"p{page.get('page', '?')} " + " ".join(parts))
    return "; ".join(labels) if labels else "-"


def render_html_report(report: dict[str, Any]) -> str:
    status = "PASS" if report.get("ok") else "FAIL"
    pdfx = report.get("pdfx", {})
    spot_colors = report.get("spot_colors", [])
    pages = report.get("pages", [])
    findings = report.get("findings", [])
    output_intents = report.get("output_intents", [])

    page_rows = "".join(
        "<tr>"
        f"<td>{page.get('page', '-')}</td>"
        f"<td>{page.get('trim_width_mm', 0):.2f}</td>"
        f"<td>{page.get('trim_height_mm', 0):.2f}</td>"
        f"<td>{'yes' if page.get('trimbox_explicit') else 'no'}</td>"
        f"<td>{'yes' if page.get('bleedbox_explicit') else 'no'}</td>"
        "</tr>"
        for page in pages
    )

    imposition_rows = "".join(
        "<tr>"
        f"<td>{page.get('page', '-')}</td>"
        f"<td>{evidence.get('media_width_mm', 0):.2f} × {evidence.get('media_height_mm', 0):.2f}</td>"
        f"<td>{_text(evidence.get('rotation'))}</td>"
        f"<td>{_text_list(evidence.get('signature_ids'))}</td>"
        f"<td>{_text_list(evidence.get('side_ids'))}</td>"
        f"<td>{_text_list(evidence.get('slug_text'))}</td>"
        f"<td>{_text(evidence.get('pairing_status'))}</td>"
        "</tr>"
        for page in pages
        if (evidence := page.get("imposition_evidence"))
    )

    intent_rows = "".join(
        "<tr>"
        f"<td>{_text(intent.get('subtype'))}</td>"
        f"<td>{_text(intent.get('output_condition_identifier'))}</td>"
        f"<td>{_text(intent.get('registry_name'))}</td>"
        f"<td>{_text(intent.get('info'))}</td>"
        f"<td>{'yes' if intent.get('has_destination_profile') else 'no'}</td>"
        "</tr>"
        for intent in output_intents
    )

    finding_rows = "".join(
        "<tr>"
        f"<td>{_text(finding.get('severity', '')).upper()}</td>"
        f"<td>{_text(finding.get('page'))}</td>"
        f"<td>{_text(finding.get('code'))}</td>"
        f"<td>{_text(finding.get('message'))}</td>"
        "</tr>"
        for finding in findings
    )

    if not page_rows:
        page_rows = '<tr><td colspan="5">No page data</td></tr>'
    if not imposition_rows:
        imposition_rows = '<tr><td colspan="7">No Phase 1 imposition evidence attached</td></tr>'
    if not intent_rows:
        intent_rows = '<tr><td colspan="5">No OutputIntent entries found</td></tr>'
    if not finding_rows:
        finding_rows = '<tr><td colspan="4">No findings</td></tr>'

    spots = ", ".join(escape(str(item)) for item in spot_colors) or "-"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pack-preflight report</title>
<style>
body {{ font-family: system-ui, -apple-system, sans-serif; margin: 2rem; line-height: 1.45; }}
h1, h2 {{ margin-bottom: .4rem; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: .75rem; margin: 1rem 0 2rem; }}
.card {{ border: 1px solid #bbb; border-radius: 8px; padding: .8rem 1rem; }}
table {{ border-collapse: collapse; width: 100%; margin: .75rem 0 2rem; }}
th, td {{ border: 1px solid #ccc; padding: .5rem; text-align: left; vertical-align: top; }}
th {{ background: #f2f2f2; }}
.small {{ color: #555; font-size: .92rem; }}
</style>
</head>
<body>
<h1>pack-preflight report</h1>
<p class="small">Practical screening report; not a PDF/X, ISO, GWG, or regulatory certification.</p>

<div class="summary">
  <div class="card"><strong>File</strong><br>{_text(report.get('file'))}</div>
  <div class="card"><strong>Result</strong><br>{status}</div>
  <div class="card"><strong>Pages</strong><br>{_text(report.get('page_count'))}</div>
  <div class="card"><strong>Spot colors</strong><br>{spots}</div>
</div>

<h2>PDF/X metadata</h2>
<table>
<tr><th>Version</th><th>Conformance</th></tr>
<tr><td>{_text(pdfx.get('version'))}</td><td>{_text(pdfx.get('conformance'))}</td></tr>
</table>

<h2>Output intents</h2>
<table>
<tr><th>Subtype</th><th>Condition</th><th>Registry</th><th>Info</th><th>Profile embedded</th></tr>
{intent_rows}
</table>

<h2>Pages</h2>
<table>
<tr><th>Page</th><th>Trim width (mm)</th><th>Trim height (mm)</th><th>TrimBox explicit</th><th>BleedBox explicit</th></tr>
{page_rows}
</table>

<h2>Imposition evidence — Phase 1</h2>
<p class="small">Objective evidence only. Front/back pairing is not evaluated in this phase.</p>
<table>
<tr><th>Page</th><th>Media size (mm)</th><th>Rotate</th><th>Signature/Form ID</th><th>Side ID</th><th>Outside-Trim slug text</th><th>Pairing</th></tr>
{imposition_rows}
</table>

<h2>Findings</h2>
<table>
<tr><th>Severity</th><th>Page</th><th>Code</th><th>Message</th></tr>
{finding_rows}
</table>
</body>
</html>
"""


def render_html_batch_report(reports: list[dict[str, Any]]) -> str:
    total = len(reports)
    passed = sum(1 for report in reports if report.get("ok"))
    failed = total - passed
    total_pages = sum(int(report.get("page_count", 0)) for report in reports)

    rows = "".join(
        "<tr>"
        f"<td>{'PASS' if report.get('ok') else 'FAIL'}</td>"
        f"<td>{_text(report.get('file'))}</td>"
        f"<td>{_text(report.get('page_count'))}</td>"
        f"<td>{_finding_count(report, 'error')}</td>"
        f"<td>{_finding_count(report, 'warning')}</td>"
        f"<td>{_finding_count(report, 'info')}</td>"
        f"<td>{', '.join(escape(str(item)) for item in report.get('spot_colors', [])) or '-'}</td>"
        f"<td>{escape(_report_imposition_summary(report))}</td>"
        "</tr>"
        for report in reports
    )

    if not rows:
        rows = '<tr><td colspan="8">No reports</td></tr>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pack-preflight batch report</title>
<style>
body {{ font-family: system-ui, -apple-system, sans-serif; margin: 2rem; line-height: 1.45; }}
h1, h2 {{ margin-bottom: .4rem; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: .75rem; margin: 1rem 0 2rem; }}
.card {{ border: 1px solid #bbb; border-radius: 8px; padding: .8rem 1rem; }}
table {{ border-collapse: collapse; width: 100%; margin: .75rem 0 2rem; }}
th, td {{ border: 1px solid #ccc; padding: .5rem; text-align: left; vertical-align: top; }}
th {{ background: #f2f2f2; }}
.small {{ color: #555; font-size: .92rem; }}
</style>
</head>
<body>
<h1>pack-preflight batch report</h1>
<p class="small">Practical screening dashboard; not a PDF/X, ISO, GWG, or regulatory certification.</p>

<div class="summary">
  <div class="card"><strong>Files</strong><br>{total}</div>
  <div class="card"><strong>Passed</strong><br>{passed}</div>
  <div class="card"><strong>Failed</strong><br>{failed}</div>
  <div class="card"><strong>Total pages</strong><br>{total_pages}</div>
</div>

<h2>Files</h2>
<table>
<tr>
  <th>Result</th>
  <th>File</th>
  <th>Pages</th>
  <th>Errors</th>
  <th>Warnings</th>
  <th>Info</th>
  <th>Spot colors</th>
  <th>Imposition identity evidence</th>
</tr>
{rows}
</table>
</body>
</html>
"""


def write_html_report(report: dict[str, Any], path: str | Path) -> Path:
    output_path = Path(path)
    output_path.write_text(render_html_report(report), encoding="utf-8")
    return output_path


def write_html_batch_report(
    reports: list[dict[str, Any]], path: str | Path
) -> Path:
    output_path = Path(path)
    output_path.write_text(render_html_batch_report(reports), encoding="utf-8")
    return output_path
