"""Keep test temporary files within the repository, avoiding Windows temp ACL issues."""
import subprocess
import sys
import uuid
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parent = root / "test-results"
parent.mkdir(exist_ok=True)
base = (parent / ("pytest-" + uuid.uuid4().hex)).resolve()
assert base.is_relative_to(root.resolve())
raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "--basetemp", str(base), *sys.argv[1:]], cwd=root))
