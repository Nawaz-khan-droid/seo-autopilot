"""Install pyseoanalyzer without its strict dependency pins.

pyseoanalyzer pins langchain==0.3.22, lxml==5.3.1, urllib3==2.3.0,
python-dotenv==1.1.0 — all of which have known CVEs fixed by the
project's requirements.txt. This script installs pyseoanalyzer with
--no-deps so our pinned secure versions are used instead.

Usage:
    python scripts/install_pyseoanalyzer.py
"""
from __future__ import annotations

import subprocess
import sys


def main():
    print("Installing pyseoanalyzer with --no-deps (using secure transitive deps)...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "pyseoanalyzer", "--no-deps"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("pyseoanalyzer installed (no deps).")
        print("CVE-safe versions from requirements.txt remain active:")
        subprocess.run([sys.executable, "-m", "pip", "show", "urllib3", "python-dotenv", "lxml"])
    else:
        print("Installation failed:", result.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
