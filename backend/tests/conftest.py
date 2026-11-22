import os
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

TEST_DATABASE = BACKEND_ROOT / "test_learning.db"
if TEST_DATABASE.exists():
    TEST_DATABASE.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE}"
