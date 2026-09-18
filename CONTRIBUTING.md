# Contributing

Thanks for helping improve **pack-preflight**.

## Good first contributions

- Add a reproducible PDF sample for a real prepress edge case.
- Improve a rule while keeping false positives low.
- Add tests for TrimBox, BleedBox, fonts, color spaces, or spot colors.
- Improve documentation or platform installation notes.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Please open an issue before proposing a large rule or architectural change. For bug fixes, include a minimal reproduction where licensing permits.

## Project scope

The project is a practical screening tool for print and packaging workflows. It is not intended to claim formal PDF/X, ISO, Ghent Workgroup, or certification compliance unless a future rule is explicitly validated against the relevant specification.
