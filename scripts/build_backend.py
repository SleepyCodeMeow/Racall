"""Build on each target OS/architecture; never cross-compile Python binaries."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
subprocess.run([
    sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
    "--name", "open-notebook-api", "--paths", str(root / "apps/api"),
    "--distpath", str(root / "build/backend"), "--workpath", str(root / "build/pyinstaller"),
    "--specpath", str(root / "build"), "--collect-submodules", "keyring.backends",
    "--collect-submodules", "mcp.server", "--collect-data", "certifi",
    str(root / "apps/api/run.py"),
], cwd=root, check=True)
