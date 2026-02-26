#!/usr/bin/env bash
# ============================================================
# Bulk PDF Generator — GitLab Release Script
# ============================================================
# Usage:
#   ./release.sh v2.3
#   ./release.sh v2.3 "Optional release title"
#
# What it does:
#   1. Builds the Windows .exe via PyInstaller
#   2. Creates a GitLab Release with auto-generated release notes
#   3. Uploads the .exe and links it to the release
#   4. Updates the README download badge version
#   5. Commits and pushes the badge update
#
# Prerequisites:
#   - glab CLI authenticated (glab auth login)
#   - Python 3.10+ with requirements.txt installed
#   - PyInstaller installed (pip install pyinstaller)
#   - Run from the project root directory
# ============================================================

set -euo pipefail

# ── Args ────────────────────────────────────────────────────
TAG="${1:-}"
TITLE="${2:-Bulk PDF Generator $TAG}"

if [[ -z "$TAG" ]]; then
    echo "Usage: ./release.sh <tag> [title]"
    echo "Example: ./release.sh v2.3"
    echo "         ./release.sh v2.3 \"Bulk PDF Generator v2.3 — Date handling fixes\""
    exit 1
fi

if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+(\.[0-9]+)?$ ]]; then
    echo "ERROR: Tag must be in format vX.Y or vX.Y.Z (got: $TAG)"
    exit 1
fi

PROJECT="davearmswork%2Fbulk-pdf-extractor-and-generator"
API_BASE="https://gitlab.com/api/v4/projects/$PROJECT"
EXE_PATH="dist/Bulk PDF Generator.exe"

echo ""
echo "============================================================"
echo "  Bulk PDF Generator — Release $TAG"
echo "============================================================"
echo ""

# ── Step 1: Get GitLab token ────────────────────────────────
echo "[1/7] Retrieving GitLab token..."
TOKEN=$(glab auth status --show-token 2>&1 | grep "Token found" | sed 's/.*Token found: //')
if [[ -z "$TOKEN" ]]; then
    echo "ERROR: Could not retrieve GitLab token. Run: glab auth login"
    exit 1
fi
echo "  OK"

# ── Step 2: Bake version info ───────────────────────────────
echo "[2/7] Generating version info..."
python _generate_version.py
echo "  OK — $(cat _version.py | grep BUILD_COMMIT)"

# ── Step 3: Build the exe ───────────────────────────────────
echo "[3/7] Building executable (this takes 1–3 minutes)..."
python -m PyInstaller BulkPDFGenerator.spec --clean --noconfirm > /dev/null 2>&1

if [[ ! -f "$EXE_PATH" ]]; then
    echo "ERROR: Build failed — $EXE_PATH not found."
    echo "  Re-run without --quiet to see errors:"
    echo "  python -m PyInstaller BulkPDFGenerator.spec --clean"
    exit 1
fi

EXE_SIZE=$(du -h "$EXE_PATH" | cut -f1)
echo "  OK — $EXE_PATH ($EXE_SIZE)"

# ── Step 4: Tag and push ────────────────────────────────────
echo "[4/7] Tagging $TAG and pushing to GitLab..."
git tag "$TAG" 2>/dev/null || echo "  Tag $TAG already exists (using existing)"
git push origin main --tags 2>&1 | tail -3
echo "  OK"

# ── Step 5: Create the release ──────────────────────────────
echo "[5/7] Creating GitLab Release..."

# Generate release notes from commits since previous tag
PREV_TAG=$(git tag --sort=-creatordate | grep -v "^$TAG$" | head -1)
if [[ -n "$PREV_TAG" ]]; then
    NOTES=$(git log "$PREV_TAG..$TAG" --pretty=format:"- %s" --no-merges 2>/dev/null || echo "- Release $TAG")
    RELEASE_NOTES="## Changes since $PREV_TAG

$NOTES

---

**Download:** Grab \`Bulk.PDF.Generator.exe\` below — no Python or installation required."
else
    RELEASE_NOTES="## Release $TAG

**Download:** Grab \`Bulk.PDF.Generator.exe\` below — no Python or installation required."
fi

glab release create "$TAG" --name "$TITLE" --notes "$RELEASE_NOTES" 2>&1 | tail -2
echo "  OK"

# ── Step 6: Upload exe and link to release ──────────────────
echo "[6/7] Uploading exe to GitLab ($(echo $EXE_SIZE))..."

UPLOAD_RESPONSE=$(curl --silent --request POST \
    --header "PRIVATE-TOKEN: $TOKEN" \
    --form "file=@$EXE_PATH" \
    "$API_BASE/uploads")

# Extract the URL from the JSON response
UPLOAD_URL=$(echo "$UPLOAD_RESPONSE" | python -c "import sys,json; print(json.load(sys.stdin)['full_path'])" 2>/dev/null)

if [[ -z "$UPLOAD_URL" ]]; then
    echo "ERROR: Upload failed. Response:"
    echo "$UPLOAD_RESPONSE"
    exit 1
fi

echo "  Uploaded — linking to release..."

LINK_RESPONSE=$(curl --silent --request POST \
    --header "PRIVATE-TOKEN: $TOKEN" \
    --header "Content-Type: application/json" \
    --data "{
        \"name\": \"Bulk.PDF.Generator.exe\",
        \"url\": \"https://gitlab.com$UPLOAD_URL\",
        \"filepath\": \"/binaries/Bulk.PDF.Generator.exe\",
        \"link_type\": \"other\"
    }" \
    "$API_BASE/releases/$TAG/assets/links")

DIRECT_URL=$(echo "$LINK_RESPONSE" | python -c "import sys,json; print(json.load(sys.stdin).get('direct_asset_url',''))" 2>/dev/null)

if [[ -z "$DIRECT_URL" ]]; then
    echo "  WARNING: Could not link asset. You may need to add it manually."
    echo "  Response: $LINK_RESPONSE"
else
    echo "  OK — $DIRECT_URL"
fi

# ── Step 7: Update README badge and push ─────────────────────
echo "[7/7] Updating README download badge..."

# Update the badge version in README.md
sed -i "s|download-v[0-9]\+\.[0-9]\+\(\.[0-9]\+\)\?-|download-$TAG-|g" README.md
sed -i "s|/-/releases/v[0-9]\+\.[0-9]\+\(\.[0-9]\+\)\?)|/-/releases/$TAG)|g" README.md

if git diff --quiet README.md; then
    echo "  README already up to date"
else
    git add README.md
    git commit -m "chore: update download badge to $TAG" --quiet
    git push origin main --quiet 2>&1
    echo "  OK — badge updated and pushed"
fi

# ── Done ─────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  RELEASE $TAG COMPLETE"
echo ""
echo "  Release page:"
echo "  https://gitlab.com/davearmswork/bulk-pdf-extractor-and-generator/-/releases/$TAG"
echo ""
echo "  Direct download:"
echo "  ${DIRECT_URL:-See release page for download link}"
echo "============================================================"
echo ""
