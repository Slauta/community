from pathlib import Path
import tempfile
import pytest


@pytest.fixture
def data_dir():
    """Return Path to the project's data/ directory."""
    return Path(__file__).parent.parent / "data"


@pytest.fixture
def output_dir(tmp_path):
    """Return a temporary directory for test output."""
    return tmp_path
