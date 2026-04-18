"""Disk-cache pruning tests (C5)."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPruneDiskCache(unittest.TestCase):
    """visual_preview._prune_disk_cache must evict oldest files first."""

    def test_prune_noop_below_cap(self):
        from visual_preview import _prune_disk_cache
        with tempfile.TemporaryDirectory() as d:
            for i in range(3):
                with open(os.path.join(d, f"x_page_{i}_dpi_200.png"), "wb") as f:
                    f.write(b"x" * 1024)  # 1KB each
            _prune_disk_cache(d, max_bytes=10_000)
            self.assertEqual(len(os.listdir(d)), 3,
                             "Should not prune when under cap")

    def test_prune_evicts_oldest_first(self):
        from visual_preview import _prune_disk_cache
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for i in range(5):
                p = os.path.join(d, f"x_page_{i}_dpi_200.png")
                with open(p, "wb") as f:
                    f.write(b"x" * 1024)
                # Stagger mtimes so "oldest" is deterministic
                os.utime(p, (time.time() - (5 - i), time.time() - (5 - i)))
                paths.append(p)

            # Cap at 2.5KB → must drop until ≤2.5KB → leave 2 newest
            _prune_disk_cache(d, max_bytes=2500)
            remaining = sorted(os.listdir(d))
            self.assertEqual(remaining, ['x_page_3_dpi_200.png',
                                         'x_page_4_dpi_200.png'])

    def test_prune_ignores_non_cache_files(self):
        from visual_preview import _prune_disk_cache
        with tempfile.TemporaryDirectory() as d:
            # A user file in the cache dir must not be deleted
            with open(os.path.join(d, "do_not_delete.txt"), "w") as f:
                f.write("keep me")
            with open(os.path.join(d, "x_page_1_dpi_200.png"), "wb") as f:
                f.write(b"x" * 10_000)
            _prune_disk_cache(d, max_bytes=100)
            self.assertIn('do_not_delete.txt', os.listdir(d))
