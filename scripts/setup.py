"""One-time project check/setup (run from the project root): python scripts/setup.py"""
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
ok = True

if not (3, 10) <= sys.version_info[:2] <= (3, 12):
    print(f"WARNING: Python {sys.version_info.major}.{sys.version_info.minor} detected. Use 3.10, 3.11 or 3.12.")
    ok = False

env, example = root / "backend" / ".env", root / "backend" / ".env.example"
if not env.exists() and example.exists():
    shutil.copy(example, env)
    print("Created backend/.env from .env.example - open it and set a long random SECRET_KEY.")
for d in ("datasets", "backend/uploads"):
    (root / d).mkdir(parents=True, exist_ok=True)

for mod in ("fastapi", "sqlalchemy", "pymupdf", "sklearn", "reportlab", "pandas"):
    try:
        __import__(mod)
    except ImportError:
        print(f"MISSING Python package for '{mod}'. Activate the venv and run: pip install -r backend/requirements.txt")
        ok = False
print("Setup check passed." if ok else "Setup check found problems (see above).")
