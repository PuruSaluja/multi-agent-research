"""Puts the backend package root on sys.path so tests can import the modules
the app itself imports (``import config``, ``from models import ...``)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
