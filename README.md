# pack-preflight

Open-source PDF preflight checker for print and packaging workflows.

**Status:** early public beta.

The goal is to catch common production risks before a PDF reaches print or packaging production. The first release focuses on practical screening rather than formal certification.

## Current checks and diagnostics

- Minimum bleed around the TrimBox
- Missing explicit TrimBox or BleedBox
- TrimBox dimensions per page
- Inconsistent page sizes
- Fonts that do not appear to be embedded
- RGB color spaces in page resources
- Spot-color names found in PDF color-space resources
- PDF/X-related document metadata when present
- Catalog OutputIntent entries when present
- Encrypted or unreadable PDFs
- Standalone HTML reports for sharing results
- Multi-file batch preflight from one command
- Combined HTML dashboard for batch runs

## Download the beta

The first public prerelease is **v0.1.0-beta.1**, with standalone archives for macOS, Windows, and Linux:

https://github.com/yarmacimehmetyasar05-alt/pack-preflight/releases/tag/v0.1.0-beta.1

The standalone executables are currently unsigned and not notarized.

## Install from source

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

Inspect one PDF:

```bash
pack-preflight artwork.pdf
```

Inspect several PDFs in one command:

```bash
pack-preflight cover.pdf insert.pdf carton.pdf
```

Multi-file text mode prints a compact PASS/FAIL summary for each file. Multi-file JSON mode returns an array:

```bash
pack-preflight cover.pdf insert.pdf carton.pdf --json
```

Create one self-contained HTML dashboard for a whole batch:

```bash
pack-preflight cover.pdf insert.pdf carton.pdf --html batch-report.html
```

The batch dashboard summarizes file status, page counts, errors, warnings, info findings, and detected spot colors.

Set a custom bleed threshold:

```bash
pack-preflight artwork.pdf --min-bleed-mm 5
```

Get JSON output:

```bash
pack-preflight artwork.pdf --json
```

Write a detailed self-contained HTML report for a single PDF:

```bash
pack-preflight artwork.pdf --html preflight-report.html
```

You can combine HTML and JSON output:

```bash
pack-preflight artwork.pdf --html preflight-report.html --json
```

## Standalone beta builds

Public beta archives for macOS, Windows, and Linux are published through GitHub Releases. See [docs/STANDALONE_BUILDS.md](docs/STANDALONE_BUILDS.md).

## Beta testing

Real prepress and packaging cases are especially useful now. See [docs/BETA_TESTING.md](docs/BETA_TESTING.md) before testing customer files or opening an issue.

Please do not upload confidential customer artwork unless you have permission. A minimal synthetic PDF that reproduces the problem is preferred.

## PDF/X and OutputIntent note

The tool reports PDF/X-related metadata and OutputIntent information when it finds them. It does **not** validate or certify PDF/X conformance, and the absence of an OutputIntent is currently reported as informational rather than a standalone failure.

## Important limitation

This project is currently a practical screening tool. It does **not** claim PDF/X, ISO, Ghent Workgroup, food-packaging, or regulatory compliance. A PASS only means that the PDF passed the rules implemented in the installed version.

## Contributing

Real-world prepress edge cases are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
