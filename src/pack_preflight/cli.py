from __future__ import annotations

import argparse
import json
import sys

from .core import inspect_pdf


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pack-preflight",
        description="Check print and packaging PDFs for common prepress risks.",
    )
    parser.add_argument("pdf", help="Path to the PDF to inspect")
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
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = inspect_pdf(args.pdf, min_bleed_mm=args.min_bleed_mm)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"File: {report['file']}")
        print(f"Pages: {report['page_count']}")
        print(f"Result: {'PASS' if report['ok'] else 'FAIL'}")

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

    if not report["ok"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
