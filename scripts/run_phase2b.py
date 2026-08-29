from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from breakfix.phase2b import run_phase2b


if __name__ == "__main__":
    result = run_phase2b(PROJECT_ROOT)
    print(result["run_id"])
