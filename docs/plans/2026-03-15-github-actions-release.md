# GitHub Actions Release Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automate Windows `.exe` and macOS `.app` builds via GitHub Actions, triggered by tag push, with artifacts uploaded to GitHub Releases.

**Architecture:** Single workflow with 3 jobs — parallel Windows + macOS builds, then a release job that waits for both and creates a GitHub Release with both binaries attached.

**Tech Stack:** GitHub Actions, Python 3.10, PyInstaller, existing `.spec` files

---

### Task 1: Create the GitHub Actions workflow file

**Files:**
- Create: `.github/workflows/release.yml`

**Step 1: Create the workflow file**

The workflow:
- Triggers on tag push matching `v*`
- `build-windows` job on `windows-latest`: installs Python 3.10, deps, bakes version, runs PyInstaller with `BulkPDFGenerator.spec`, uploads `.exe` as artifact
- `build-macos` job on `macos-latest`: same but uses `BulkPDFGenerator_mac.spec`, zips the `.app` bundle, uploads zip as artifact
- `release` job: waits for both builds, downloads artifacts, creates GitHub Release with auto-generated notes, attaches both binaries
- Uses `GITHUB_TOKEN` (built-in) for permissions

**Step 2: Verify the workflow file is valid YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"`
Or just visually verify — GitHub will validate on push.

**Step 3: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add GitHub Actions release workflow for Windows and macOS builds"
```

### Task 2: Update CLAUDE.md release documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update the Release Workflow section**

Replace the manual release process with the new GitHub Actions process. Keep the `release.sh` reference as a legacy fallback. Document the new trigger: `git tag vX.Y && git push origin --tags`.

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md release workflow for GitHub Actions"
```

### Task 3: Update memory

**Step 1: Update session memory**

Update the memory file to reflect that releases now use GitHub Actions, not local builds or GitLab.
