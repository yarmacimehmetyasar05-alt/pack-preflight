# Beta testing guide

Thanks for testing **pack-preflight** with real print or packaging PDFs.

The project is still an early screening tool. It does not certify PDF/X, ISO, Ghent Workgroup, food-contact, or regulatory compliance.

## What to test

Useful beta cases include:

- PDFs with and without bleed
- Different TrimBox / BleedBox setups
- Embedded and non-embedded fonts
- RGB content in otherwise print-oriented files
- Spot colors
- PDF/X metadata and OutputIntent variations
- Multi-page PDFs with inconsistent page sizes
- Encrypted or damaged PDFs

## How to run

Install from the repository:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run a PDF:

```bash
pack-preflight artwork.pdf
```

Create a shareable HTML report:

```bash
pack-preflight artwork.pdf --html preflight-report.html
```

Create JSON output:

```bash
pack-preflight artwork.pdf --json
```

## What to report

For a useful bug report, include:

- operating system
- Python version
- pack-preflight version or commit
- the exact command you ran
- the finding you expected
- the finding you actually received
- whether Acrobat, another preflight tool, or a print workflow gave a different result

## Confidential artwork

Do **not** upload customer artwork, trademarks, personal data, unreleased packaging, or confidential production files unless you have permission.

If the issue can be reproduced, please create a minimal test PDF with dummy text and simple shapes instead. A reduced synthetic PDF is much more useful than confidential production artwork.

If you cannot share the PDF, include the terminal or JSON result and describe the relevant PDF property as precisely as possible.

## False positives matter

This project should be conservative. A rule that catches a real problem but falsely flags many valid files is not automatically useful.

Please report both:

- missed production risks
- valid files that are flagged incorrectly

Both kinds of feedback are important.
