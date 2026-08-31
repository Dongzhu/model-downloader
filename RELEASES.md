# Release workflow

This repository includes GitHub Actions to build artifacts for Ubuntu, Windows and macOS.

Required GitHub Secrets for signed releases (optional):

- WINDOWS_SIGN_CERT (PFX base64)
- MACOS_SIGN_CERT (base64)
- GPG_SIGNING_KEY (base64)
- SIGNING_PASSWORD

If you do not provide signing secrets, unsigned builds will still be attached as artifacts.

To perform a manual release:
1. Create a tag (vX.Y.Z)
2. Go to Actions -> Re-run the build (or trigger the release workflow)
3. The workflow will create a GitHub Release and attach build artifacts.