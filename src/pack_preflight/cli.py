from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .core import inspect_pdf
from .report import write_html_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pack-preflight",
        description="Check print and packaging PDFs for common prepress risks.",
    )
    parser.add_argument(
        "pdf",
        nargs="+",
        help="Path to one or more PDFs to inspect",
    )
    parser.add_argument(
        "--min-bleed-mm",
        type=float,
        default=3.0,
        help="Minimum expected bleed on each side (default: 3.0 mm)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.add_argument(
        "--html",
        metavar="PATH",
        help="Write a standalone HTML report to PATH (single PDF only)",
    )
    return parser


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

    if args.html and len(args.pdf) != 1:
        parser.error("--html can only be used when inspecting one PDF")

    reports = [
        inspect_pdf(path, min_bleed_mm=args.min_bleed_mm)
        for path in args.pdf
    ]

    if args.html:
        output_path = write_html_report(reports[0], args.html)
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
