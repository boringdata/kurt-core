#!/usr/bin/env python3
"""Kurt Evaluation CLI entry point.

This module provides the CLI entry point for kurt-eval command.
It handles path resolution to find the eval module.
"""

import sys
from pathlib import Path

# Find project root (where eval/ directory is located)
# This script is in src/, so go up one level
project_root = Path(__file__).parent.parent.resolve()
eval_dir = project_root / "eval"

# Add eval directory to path so we can import from it
sys.path.insert(0, str(eval_dir))
sys.path.insert(0, str(project_root))

# Now import and run the CLI
from cli import main  # noqa: E402

if __name__ == "__main__":
    main()
