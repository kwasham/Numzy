from __future__ import annotations

import sys
from pathlib import Path

# Add backend folder to sys.path so `import app...` works in tests when running from backend root
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
