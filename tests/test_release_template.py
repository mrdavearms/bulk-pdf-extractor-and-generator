"""Guard: the release page's teacher-facing install instructions must survive.

The Windows / macOS download links and security-warning guidance ("Run
anyway", "Open Anyway", first-launch steps) live in the release workflow's
body template (.github/workflows/release.yml), NOT in per-release notes — so
every release includes them automatically.

If that block is ever accidentally edited away, this test fails in CI (the
Tests workflow runs on every push to main/test) BEFORE a release goes out,
so teachers never get a release page without install help.
"""
import unittest
from pathlib import Path

RELEASE_YML = Path(__file__).parent.parent / ".github" / "workflows" / "release.yml"

# Phrases that must appear in the release body template. Kept to stable,
# meaningful substrings so wording tweaks don't break the test, but removing
# a whole section does.
REQUIRED_PHRASES = [
    "## ⬇️ Download",                 # download section header
    "Bulk.PDF.Generator.exe",         # Windows binary link
    "Bulk.PDF.Generator.macOS.dmg",   # macOS binary link
    "Windows protected your PC",      # Windows SmartScreen guidance
    "Run anyway",                     # Windows: how to proceed
    "Privacy & Security",             # macOS Gatekeeper guidance (15+)
    "Open Anyway",                    # macOS: how to proceed (15+)
    "Right-click",                    # macOS: first launch (14 and earlier)
]


class TestReleaseInstallInstructions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.text = RELEASE_YML.read_text(encoding="utf-8")

    def test_release_workflow_exists(self):
        self.assertTrue(RELEASE_YML.is_file(),
                        f"Release workflow not found at {RELEASE_YML}")

    def test_install_instructions_present(self):
        missing = [p for p in REQUIRED_PHRASES if p not in self.text]
        self.assertEqual(
            missing, [],
            "release.yml is missing teacher-facing install instructions: "
            f"{missing}. These MUST stay in the workflow body template so every "
            "release page tells teachers how to get past the Windows/macOS "
            "security warnings. Do not delete them.",
        )


if __name__ == "__main__":
    unittest.main()
