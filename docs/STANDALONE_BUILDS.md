# Standalone beta builds

The normal developer installation uses Python. For print and prepress beta testers who do not want to install Python packages, the project also publishes standalone beta archives.

## Download a public beta

Open the repository's **Releases** page and choose the latest prerelease. The current public beta is tagged `v0.1.0-beta.4`.

Each release contains platform-named ZIP archives for macOS, Windows, and Linux.

After unzipping, confirm the exact build before testing:

```bash
pack-preflight --version
```

On Windows use `pack-preflight.exe --version`. Beta 4 should report `0.1.0b4`.

## Maintainer build workflow

Maintainers can also create fresh workflow artifacts:

1. Open the repository's **Actions** tab.
2. Select **beta-binaries**.
3. Choose **Run workflow**.
4. Wait for the macOS, Windows, and Linux jobs to finish.
5. Download the generated workflow artifacts.

The workflow runs the automated tests before packaging each executable and smoke-tests both `--help` and `--version` on the packaged binary.

## Important beta limitations

These executables are early beta builds.

- They are not code-signed or notarized.
- macOS or Windows may display a security warning.
- They do not certify PDF/X, ISO, Ghent Workgroup, food-contact, or regulatory compliance.
- A PASS means only that the PDF passed the rules implemented in that build.

Do not disable operating-system security controls globally just to run a beta build. If a tester is not comfortable reviewing an unsigned executable, use the Python installation method instead.

## Feedback

See [BETA_TESTING.md](BETA_TESTING.md) for what to test and how to report false positives, missed risks, and crashes.
