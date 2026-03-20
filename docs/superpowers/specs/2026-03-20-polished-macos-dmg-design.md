# Polished macOS DMG — Design Spec

**Date:** 2026-03-20
**Status:** Approved
**Scope:** macOS release packaging improvements — DMG polish, ad-hoc signing, version injection, Gatekeeper guidance

## Problem

The macOS release was previously shipped as a plain `.zip` (now a bare `.dmg`). It lacks the visual polish users expect from a Mac app: no background image, no "drag to Applications" prompt, no volume icon, no code signing, and a hardcoded `CFBundleVersion` stuck at `2.5.0`.

Additionally, every new download re-triggers Gatekeeper warnings because the app is unsigned, and the release notes only cover the older right-click → Open workaround, missing the macOS 15+ System Settings path.

## Goals

1. Professional DMG with background image, app icon positioning, and Applications folder alias
2. Ad-hoc code signing for Gatekeeper resilience (free, no Apple Developer account)
3. Accurate `CFBundleVersion` / `CFBundleShortVersionString` injected from git tag at build time
4. Updated Gatekeeper instructions covering both classic and macOS 15+ flows
5. Proper `.icns` volume icon for the mounted DMG

## Non-Goals

- Apple Developer ID signing or notarization ($99/year — deferred)
- Changes to the Windows build pipeline
- Changes to application code (`pdf_generator.py`)
- Changes to `_generate_version.py`

## Design

### 1. DMG Background Image

A static Retina-resolution PNG (`dmg_background.png`, exactly 1200x800px for 2x clarity on modern Macs) committed to the repo root:

- Clean light background matching the litera theme (white/light grey)
- App name "Bulk PDF Generator" at top
- Visual arrow from left to right
- "Drag to Applications" text

The `--window-size 600 400` flag in `create-dmg` maps to logical points — a 1200x800 image fills this at Retina resolution. This is a one-time design asset.

### 2. Volume Icon

A proper `icon.icns` file generated locally from the existing `icon.png` and committed to the repo.

**Generation commands** (run once locally on macOS):

```bash
# Create the iconset directory with required resolutions
mkdir icon.iconset
sips -z 16 16     icon.png --out icon.iconset/icon_16x16.png
sips -z 32 32     icon.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32     icon.png --out icon.iconset/icon_32x32.png
sips -z 64 64     icon.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128   icon.png --out icon.iconset/icon_128x128.png
sips -z 256 256   icon.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256   icon.png --out icon.iconset/icon_256x256.png
sips -z 512 512   icon.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512   icon.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out icon.iconset/icon_512x512@2x.png

# Convert to .icns
iconutil -c icns icon.iconset -o icon.icns

# Clean up
rm -rf icon.iconset
```

Usage:
- Committed to repo alongside `icon.png` and `icon.ico`
- Used by `create-dmg --volicon` for the mounted DMG volume icon
- Referenced by `BulkPDFGenerator_mac.spec` instead of `icon.png` (replaces PyInstaller's auto-conversion with an explicit `.icns`)

### 3. DMG Creation with `create-dmg`

Replace the current `hdiutil create` workflow step with the open-source `create-dmg` tool:

```bash
brew install create-dmg

set +e
create-dmg \
  --volname "Bulk PDF Generator" \
  --volicon "icon.icns" \
  --background "dmg_background.png" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 80 \
  --icon "Bulk PDF Generator.app" 150 200 \
  --app-drop-link 450 200 \
  --no-internet-enable \
  "dist/Bulk.PDF.Generator.macOS.dmg" \
  "dist/Bulk PDF Generator.app"
EXIT_CODE=$?
set -e
if [ $EXIT_CODE -ne 0 ] && [ $EXIT_CODE -ne 2 ]; then
  echo "create-dmg failed with exit code $EXIT_CODE"
  exit $EXIT_CODE
fi
```

Key details:
- `--app-drop-link` creates the Applications folder alias positioned on the right
- `--icon` positions the app on the left
- `--no-internet-enable` skips the deprecated internet-enable flag
- Exit code 2 means a cosmetic issue (e.g. volume icon couldn't be set) — treated as non-fatal. Any other non-zero exit code fails the build.

### 4. Ad-hoc Code Signing

A new workflow step after PyInstaller build and before DMG creation:

```bash
codesign --force --deep --sign - "dist/Bulk PDF Generator.app"
```

- `--force` replaces any partial signatures from PyInstaller
- `--deep` signs nested frameworks and libraries
- `--sign -` is the ad-hoc identity (free, no certificate needed)

**Caveat:** `--deep` is deprecated by Apple for production signing because it applies a flat signature without respecting individual entitlements. For ad-hoc signing where entitlements don't matter, this is a pragmatic shortcut. If the project ever moves to Developer ID signing, `--deep` must be replaced with inside-out signing of each framework/dylib individually.

**Gatekeeper effect:**
- First install: user still gets the Gatekeeper prompt (unavoidable without paid Developer ID)
- Subsequent versions from the same CI signing approach are less likely to re-trigger aggressive warnings
- Eliminates "damaged" or "can't verify developer" errors that unsigned apps sometimes get

### 5. Version Injection into Info.plist

A new workflow step after "Bake version info" and before "Build .app":

```bash
TAG="${GITHUB_REF_NAME#v}"          # v2.7.3 → 2.7.3
SHORT="${TAG%.*}"                    # 2.7.3 → 2.7
# Guard against two-segment tags (v2.8 → TAG=2.8, SHORT=2)
if [[ "$SHORT" == *"."* ]]; then : ; else SHORT="$TAG"; fi
sed -i '' "s/'CFBundleVersion': '[^']*'/'CFBundleVersion': '$TAG'/" BulkPDFGenerator_mac.spec
sed -i '' "s/'CFBundleShortVersionString': '[^']*'/'CFBundleShortVersionString': '$SHORT'/" BulkPDFGenerator_mac.spec
```

- Uses `[^']*` in sed patterns to prevent greedy matching past the closing quote
- Handles two-segment tags gracefully (e.g. `v2.8` → both values set to `2.8`)
- Only modifies the spec in CI — committed file keeps placeholder values
- No changes to `_generate_version.py`

### 6. Updated Gatekeeper Instructions

The release body in the workflow will be updated to cover both flows:

- **macOS 14 and earlier:** Right-click the app → Open → Open (in the dialog)
- **macOS 15+:** System Settings → Privacy & Security → scroll to "Open Anyway" → click Open

### 7. Cleanup

- Delete the `dmg_staging/` directory (leftover from manual experimentation — `create-dmg` handles staging internally)
- Add `dmg_staging/` to `.gitignore` to prevent future accidental commits

## Files Changed

| File | Change |
|------|--------|
| `dmg_background.png` | **New** — Retina background image (1200x800) for DMG |
| `icon.icns` | **New** — proper macOS icon set generated from `icon.png` |
| `.github/workflows/release.yml` | Install `create-dmg`, ad-hoc signing step, version injection step, updated DMG creation, updated release body |
| `BulkPDFGenerator_mac.spec` | Reference `icon.icns` instead of `icon.png` |
| `.gitignore` | Add `dmg_staging/` |
| `CLAUDE.md` | Update references to reflect new DMG pipeline |

## Files NOT Changed

| File | Reason |
|------|--------|
| `pdf_generator.py` | No app code changes needed |
| `_generate_version.py` | Version injection handled in workflow, not here |
| `BulkPDFGenerator.spec` | Windows build unchanged |
| `README.md` | Already updated to reference `.dmg` |

## Files Deleted

| File | Reason |
|------|--------|
| `dmg_staging/` | Leftover from manual experimentation; `create-dmg` handles staging |

## Risks

- `create-dmg` exit code 2 on volume icon failure — mitigated by allowing exit code 2 as a pass (shell construct detailed in section 3)
- `brew install create-dmg` adds ~10s to macOS CI build — negligible
- Ad-hoc signing is not equivalent to Developer ID — users still get first-run prompt. This is documented in release notes.
- `--deep` codesigning is deprecated for production use — acceptable for ad-hoc, documented as a future migration item if Developer ID is adopted

## Verification

After implementation, re-tag `v2.7.3` to verify the full pipeline produces a polished, signed DMG with correct version metadata.
