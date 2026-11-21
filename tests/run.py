#!/usr/bin/env python3
"""Run the plugin's self-tests, then the skills check.

    python tests/run.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py", top_level_dir=str(HERE))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    sys.path.insert(0, str(HERE))
    import check_skills
    checked = check_skills.main([])
    return 0 if result.wasSuccessful() and checked == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
