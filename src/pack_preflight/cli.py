from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .core import inspect_pdf
from .report import write_html_batch_report, write_html_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pack-preflight",
        description="Check print and packaging PDFs for common prepress risks.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "input",
        nargs="+",
        help="One or more PDF files or directories to inspect",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="When an input is a directory, include PDFs in nested folders",
    )
    parser.add_argument(
        "--min-bleed-mm",
        type=float,
        default=3.0,
        help="Minimum expected bleed on each side (default: 3.0 mm)",
    )
    parser.add_argument(
        "--min-image-dpi",
        type=float,
        default=350.0,
        help="Minimum effective raster image resolution (default: 350 dpi)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.add_argument(
        "--html",
        metavar="PATH",
        help="Write a standalone HTML report or batch dashboard to PATH",
    )
    return parser


def collect_pdf_inputs(inputs: list[str], recursive: bool = False) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()

    for raw in inputs:
        path = Path(raw)

        if path.is_dir():
            candidates = path.rglob("*") if recursive else path.glob("*")
            pdfs = sorted(
                (
                    candidate
                    for candidate in candidates
                    if candidate.is_file() and candidate.suffix.lower() == ".pdf"
                ),
                key=lambda candidate: str(candidate).lower(),
            )
        else:
            pdfs = [path]

        for pdf in pdfs:
            key = str(pdf.resolve(strict=False))
            if key in seen:
                continue
            seen.add(key)
            collected.append(str(pdf))

    return collected


def _print_text_report(report: dict[str, Any]) -> None:
    print(f"File: {report['file']}")
    print(f"Pages: {report['page_count']}")
    print(f"Result: {'PASS' if report['ok'] else 'FAIL'}")

    pdfx = report.get("pdfx", {})
    if pdfx.get("version") or pdfx.get("conformance"):
        print(
            "PDF/X metadata: "
            f"version={pdfx.get('version') or '-'}, "
            f"conformance={pdfx.get('conformance') or '-'}"
        )

    if report.get("output_intents"):
        for index, intent in enumerate(report["output_intents"], start=1):
            print(
                f"OutputIntent {index}: "
                f"subtype={intent.get('subtype') or '-'}, "
                "condition="
                f"{intent.get('output_condition_identifier') or '-'}, "
                f"profile={'yes' if intent.get('has_destination_profile') else 'no'}"
            )

    for page in report.get("pages", []):
        trim_status = "explicit" if page["trimbox_explicit"] else "fallback"
        bleed_status = "explicit" if page["bleedbox_explicit"] else "fallback"
        print(
            f"Page {page['page']}: "
            f"{page['trim_width_mm']:.2f} x {page['trim_height_mm']:.2f} mm "
            f"(TrimBox {trim_status}, BleedBox {bleed_status})"
        )

    if report["spot_colors"]:
        print("Spot colors: " + ", ".join(report["spot_colors"]))
    if report["findings"]:
        print("\nFindings:")
        for finding in report["findings"]:
            page = f" [page {finding['page']}]" if finding.get("page") else ""
            print(
                f"- {finding['severity'].upper()}{page} "
                f"{finding['code']}: {finding['message']}"
            )
    else:
        print("No findings in the current rule set.")


def _print_batch_summary(reports: list[dict[str, Any]]) -> None:
    for index, report in enumerate(reports):
        if index:
            print()
        status = "PASS" if report["ok"] else "FAIL"
        errors = sum(
            1 for finding in report.get("findings", [])
            if finding.get("severity") == "error"
        )
        warnings = sum(
            1 for finding in report.get("findings", [])
            if finding.get("severity") == "warning"
        )
        print(
            f"{status}  {report['file']}  "
            f"pages={report['page_count']} errors={errors} warnings={warnings}"
        )


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    pdf_paths = collect_pdf_inputs(args.input, recursive=args.recursive)
    if not pdf_paths:
        parser.error("no PDF files found in the supplied inputs")

    reports = [
        inspect_pdf(
            path,
            min_bleed_mm=args.min_bleed_mm,
            min_image_dpi=args.min_image_dpi,
        )
        for path in pdf_paths
    ]

    if args.html:
        if len(reports) == 1:
            output_path = write_html_report(reports[0], args.html)
        else:
            output_path = write_html_batch_report(reports, args.html)
        print(f"HTML report: {output_path}")

    if args.json:
        payload: dict[str, Any] | list[dict[str, Any]]
        payload = reports[0] if len(reports) == 1 else reports
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif len(reports) == 1:
        _print_text_report(reports[0])
    else:
        _print_batch_summary(reports)

    return 2 if any(not report["ok"] for report in reports) else 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
