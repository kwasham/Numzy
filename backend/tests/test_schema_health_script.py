from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_schema_health_script_runs():
    # Run the health script with current interpreter to avoid path issues.
    script = Path(__file__).resolve().parents[1] / "scripts" / "assert_schema_health.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    assert result.returncode == 0, "Schema health script failed"
