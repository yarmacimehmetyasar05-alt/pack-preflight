# pack-preflight

Open-source PDF preflight checker for print and packaging workflows.

**Status:** early MVP.

The goal is to catch common production risks before a PDF reaches print or packaging production. The first release focuses on practical screening rather than formal certification.

## Current checks

- Minimum bleed around the TrimBox
- Missing explicit TrimBox or BleedBox
- TrimBox dimensions per page
- Inconsistent page sizes
- Fonts that do not appear to be embedded
- RGB color spaces in page resources
- Spot-color names found in PDF color-space resources
- Encrypted or unreadable PDFs

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

```bash
pack-preflight artwork.pdf
```

Set a custom bleed threshold:

```bash
pack-preflight artwork.pdf --min-bleed-mm 5
```

Get JSON output:

```bash
pack-preflight artwork.pdf --json
```

## Important limitation

This project is currently a practical screening tool. It does **not** claim PDF/X, ISO, Ghent Workgroup, food-packaging, or regulatory compliance. A PASS only means that the PDF passed the rules implemented in the installed version.

## Contributing

Real-world prepress edge cases are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
