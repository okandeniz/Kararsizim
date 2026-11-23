#!/usr/bin/env python
"""Claude bir .py dosyasını düzenleyince ruff ile formatlar ve lint hatalarını geri bildirir.

Bu script venv'in python'u ile çalıştırılır; ruff `python -m ruff` ile çağrılır,
böylece venv'in PATH'te olması gerekmez.

Türkçe Windows'ta varsayılan kodlama cp1254'tür; Claude Code ve ruff ise UTF-8 konuşur.
Bu yüzden girdi, alt süreç çıktısı ve hata metni açıkça UTF-8 olarak işlenir.
"""

import json
import subprocess
import sys

data = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
path = (data.get("tool_input") or {}).get("file_path", "")

if not path.endswith(".py"):
    sys.exit(0)

ruff = [sys.executable, "-m", "ruff"]


def run(*args):
    return subprocess.run(
        [*ruff, *args], check=False, capture_output=True, encoding="utf-8", errors="replace"
    )


# ruff kurulu değilse sessizce çık
if run("--version").returncode != 0:
    sys.exit(0)

run("format", path)
run("check", "--fix", path)
result = run("check", path)

if result.returncode != 0:
    message = f"ruff sorunları ({path}):\n{result.stdout}"
    sys.stderr.buffer.write(message.encode("utf-8", errors="replace"))
    sys.stderr.flush()
    sys.exit(2)  # Claude hatayı görür ve düzeltir
sys.exit(0)
