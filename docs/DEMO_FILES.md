# Synthetic demo PDFs

The project includes a small generator for repeatable, non-confidential beta tests.

This is useful when you want to verify that a build works before trying customer artwork, or when you need a safe reproduction case for an issue.

## Generate the files

Install the project from source, then run:

```bash
python examples/generate_demo_pdfs.py
```

By default this creates a `pack-preflight-demo` directory. You can choose another directory:

```bash
python examples/generate_demo_pdfs.py ./demo-files
```

## Generated cases

- `clean-explicit-boxes.pdf` — one page with explicit TrimBox and BleedBox and 3 mm bleed. Expected overall result: PASS.
- `zero-bleed-warning.pdf` — one page with explicit boxes but zero bleed. Expected finding: `bleed_below_minimum`.
- `mixed-page-sizes.pdf` — two pages with different TrimBox sizes. Expected finding: `inconsistent_page_size`.
- `encrypted-failure.pdf` — password-encrypted PDF. Expected overall result: FAIL with `pdf_encrypted`.

The first three may also contain informational findings such as a missing OutputIntent. Those do not make the current rule set fail the file.

## Try the whole demo folder

```bash
pack-preflight ./pack-preflight-demo --html demo-report.html
```

The encrypted demo intentionally causes a non-zero exit status because it represents a preflight failure.

These generated PDFs contain no customer artwork, trademarks, or personal information.
