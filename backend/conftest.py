"""Put the backend root on sys.path so tests import what the app imports."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
