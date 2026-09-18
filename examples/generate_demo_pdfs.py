from __future__ import annotations

import argparse

from pack_preflight.demo import generate_demo_pdfs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate non-confidential demo PDFs for pack-preflight."
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        default="pack-preflight-demo",
        help="Directory to create (default: pack-preflight-demo)",
    )
    args = parser.parse_args()

    paths = generate_demo_pdfs(args.output_dir)

    print("Created demo PDFs:")
    for label, path in paths.items():
        print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
