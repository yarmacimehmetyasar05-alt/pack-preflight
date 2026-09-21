# pack-preflight

Open-source PDF preflight checker for print and packaging workflows.

**Status:** early public beta.

The goal is to catch common production risks before a PDF reaches print or packaging production. The first release focuses on practical screening rather than formal certification.

## Maintainer background

The project is maintained by a print/prepress professional with long hands-on experience in offset printing, packaging production, and prepress workflows. pack-preflight is being developed around practical production problems encountered in real print and packaging work.

## Current checks and diagnostics

- Minimum bleed around the TrimBox
- Missing explicit TrimBox or BleedBox
- TrimBox dimensions per page
- Inconsistent page sizes
- Fonts that do not appear to be embedded
- Used RGB content identified by type (raster image, vector artwork, or text), including mixed RGB/CMYK page warnings
- Raster images below a configurable effective-resolution threshold (default: 350 dpi)
- Composite/rich-black text diagnostics with size-aware register-risk context (source/main; included in the next binary release)
- Spot-color names found in PDF color-space resources
- PDF/X-related document metadata when present
- Catalog OutputIntent entries when present
- Encrypted or unreadable PDFs
- Standalone HTML reports for sharing results
- Multi-file batch preflight from one command
- Combined HTML dashboard for batch runs
- Folder scanning, with optional recursive subfolder scanning
- Exact build identification with `--version`

## Download the beta

The current public prerelease is **v0.1.0-beta.5**.

- macOS: https://github.com/yarmacimehmetyasar05-alt/pack-preflight/releases/download/v0.1.0-beta.5/pack-preflight-macos.zip
- Windows: https://github.com/yarmacimehmetyasar05-alt/pack-preflight/releases/download/v0.1.0-beta.5/pack-preflight-windows.zip
- Linux: https://github.com/yarmacimehmetyasar05-alt/pack-preflight/releases/download/v0.1.0-beta.5/pack-preflight-linux.zip
- Release notes: https://github.com/yarmacimehmetyasar05-alt/pack-preflight/releases/tag/v0.1.0-beta.5

The standalone executables are currently unsigned and not notarized.

## Five-minute beta test

Use one non-confidential PDF whose expected prepress result you already know, confirm the build with `--version`, run the standalone beta, and compare the result with your normal workflow. Acrobat Preflight, PitStop, RIP/workflow checks, and experienced manual inspection are all useful comparisons.

If pack-preflight crashes, misses a production risk, flags a valid file incorrectly, or materially disagrees with your trusted workflow, please open a GitHub issue. There is a dedicated **Beta feedback** issue form so real-world comparisons can be reported consistently.

Tester call: https://github.com/yarmacimehmetyasar05-alt/pack-preflight/issues/27

See [docs/BETA_TESTING.md](docs/BETA_TESTING.md) for the short test procedure and privacy guidance.

## Install from source

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

Show the installed build version:

```bash
pack-preflight --version
```

Inspect one PDF:

```bash
pack-preflight artwork.pdf
```

Inspect several PDFs in one command:

```bash
pack-preflight cover.pdf insert.pdf carton.pdf
```

Scan every PDF directly inside a job folder:

```bash
pack-preflight ./customer-job
```

Include PDFs in nested subfolders:

```bash
pack-preflight ./customer-job --recursive
```

Files supplied directly and PDFs discovered in folders can be mixed in the same run. Duplicate paths are inspected only once.

Multi-file text mode prints a compact PASS/FAIL summary for each file. Multi-file JSON mode returns an array:

```bash
pack-preflight cover.pdf insert.pdf carton.pdf --json
```

Create one self-contained HTML dashboard for a whole batch or folder:

```bash
pack-preflight ./customer-job --recursive --html batch-report.html
```

The batch dashboard summarizes file status, page counts, errors, warnings, info findings, and detected spot colors.

Set a custom bleed threshold:

```bash
pack-preflight artwork.pdf --min-bleed-mm 5
```

Set a custom effective-image-resolution threshold:

```bash
pack-preflight artwork.pdf --min-image-dpi 300
```

The image check uses effective resolution based on the embedded pixel dimensions and placed size in the PDF, rather than relying on nominal image metadata alone.

RGB diagnostics inspect painted content rather than merely warning because an RGB color space exists somewhere in the resource dictionary. Findings distinguish raster images, vector artwork, and text where the PDF content stream makes that distinction available. DeviceRGB, CalRGB, and ICCBased RGB are recognized, and pages that actually use both RGB and CMYK are called out for separation review. These warnings do not predict a RIP's final conversion or claim that RGB content will necessarily print incorrectly.

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

Please do not upload confidential customer artwork unless you have permission. A minimal synthetic PDF that reproduces the problem is preferred. The project also includes a safe demo generator; see [docs/DEMO_FILES.md](docs/DEMO_FILES.md).

## PDF/X and OutputIntent note

The tool reports PDF/X-related metadata and OutputIntent information when it finds them. It does **not** validate or certify PDF/X conformance, and the absence of an OutputIntent is currently reported as informational rather than a standalone failure.

## Important limitation

This project is currently a practical screening tool. It does **not** claim PDF/X, ISO, Ghent Workgroup, food-packaging, or regulatory compliance. A PASS only means that the PDF passed the rules implemented in the installed version.

## Production knowledge model

New rules are documented as a chain from the real production problem to the PDF/job evidence, press mechanism, finishing consequence, valid exceptions, detection method, operator action, tests, and evidence provenance. See [docs/PRODUCTION_KNOWLEDGE_MODEL.md](docs/PRODUCTION_KNOWLEDGE_MODEL.md).

## Contributing

Real-world prepress edge cases are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
