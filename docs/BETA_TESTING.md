# Beta testing guide

Thanks for testing **pack-preflight** with real print or packaging PDFs.

The project is still an early screening tool. It does not certify PDF/X, ISO, Ghent Workgroup, food-contact, or regulatory compliance.

## Five-minute beta test

1. Download the current standalone beta from the repository's **Releases** page and unzip the archive for your operating system.
2. Confirm the build version with `pack-preflight --version` (or `pack-preflight.exe --version` on Windows). The current beta should report `0.1.0b3`.
3. Choose one non-confidential PDF whose expected prepress result you already know.
4. Run the executable on that PDF.
5. If possible, compare the result with Acrobat Preflight, PitStop, a RIP/workflow check, or your normal manual decision.
6. Open a GitHub issue if pack-preflight crashes, misses a production risk, flags a valid file incorrectly, or reports something materially different from the tool/workflow you trust.

Windows:

```text
pack-preflight.exe --version
pack-preflight.exe artwork.pdf
```

macOS or Linux:

```bash
./pack-preflight --version
./pack-preflight artwork.pdf
```

The standalone executables are currently unsigned and not notarized. Your operating system may show a security warning. Do not disable operating-system security controls globally just to run a beta build.

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
- Folders containing several production PDFs

## Batch and folder tests

Run several PDFs together:

```bash
pack-preflight cover.pdf insert.pdf carton.pdf
```

Scan PDFs directly inside a job folder:

```bash
pack-preflight ./customer-job
```

Include nested folders:

```bash
pack-preflight ./customer-job --recursive
```

Create one shareable HTML dashboard for a folder:

```bash
pack-preflight ./customer-job --recursive --html batch-report.html
```

## Install from source

Developers can install from the repository:

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
- output of `pack-preflight --version`
- the exact command you ran
- the finding you expected
- the finding you actually received
- whether Acrobat, PitStop, another preflight tool, a RIP/workflow, or manual inspection gave a different result
- a minimal synthetic reproduction PDF when possible

A report that says **"this valid file was flagged incorrectly"** is just as valuable as a missed-risk report.

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
