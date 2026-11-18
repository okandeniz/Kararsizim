#!/usr/bin/env python
"""Claude bir .py dosyasını düzenleyince ruff ile formatlar ve lint hatalarını geri bildirir.

Bu script venv'in python'u ile çalıştırılır; ruff `python -m ruff` ile çağrılır,
böylece venv'in PATH'te olması gerekmez.
"""

import json
import subprocess
import sys

data = json.load(sys.stdin)
path = (data.get("tool_input") or {}).get("file_path", "")

if not path.endswith(".py"):
    sys.exit(0)

ruff = [sys.executable, "-m", "ruff"]

# ruff kurulu değilse sessizce çık
probe = subprocess.run([*ruff, "--version"], check=False, capture_output=True)
if probe.returncode != 0:
    sys.exit(0)

subprocess.run([*ruff, "format", path], check=False, capture_output=True)
subprocess.run([*ruff, "check", "--fix", path], check=False, capture_output=True)
result = subprocess.run([*ruff, "check", path], check=False, capture_output=True, text=True)

if result.returncode != 0:
    print(f"ruff sorunları ({path}):\n{result.stdout}", file=sys.stderr)
    sys.exit(2)  # Claude hatayı görür ve düzeltir
sys.exit(0)
