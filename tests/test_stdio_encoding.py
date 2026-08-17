"""Regression: the CLI must not crash when stdout is ASCII (C/POSIX locale,
output redirected to a file). Reports contain CJK text."""

import os
import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_survives_ascii_stdout():
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "ascii"
    env["LANG"] = "C"
    env["LC_ALL"] = "C"
    proc = subprocess.run(
        [sys.executable, "-c", "from skilldoctor.cli import app; app()", "validate", str(FIXTURES)],
        capture_output=True,
        env=env,
        timeout=60,
    )
    assert proc.returncode in (0, 1), proc.stderr.decode("utf-8", errors="replace")
    assert b"ascii" not in proc.stderr  # no UnicodeEncodeError traceback
