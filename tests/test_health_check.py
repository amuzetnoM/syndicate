import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.health_check import check_python_version, check_packages


def test_python_version():
    # Ensure we run in Python 3.12 for CI environments
    v_ok = check_python_version()
    assert v_ok, "Python version must be 3.12 for CI checks"


def test_required_packages():
    missing = check_packages()
    # In CI we allow some optional packages to be missing (e.g., notion client)
    # but pandas and numpy must be present
    assert "pandas" not in missing
    assert "numpy" not in missing
