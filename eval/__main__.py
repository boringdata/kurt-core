"""Entry point for running eval as a module: python -m eval or uv run eval"""

import sys
from pathlib import Path

# Add eval directory to path so we can import cli
eval_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(eval_dir))

from cli import main  # noqa: E402

if __name__ == "__main__":
    main()
