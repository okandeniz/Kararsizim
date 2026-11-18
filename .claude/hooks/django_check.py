#!/usr/bin/env python
"""Claude bitirmeden önce `manage.py check` çalıştırır; hata varsa bitirmesine izin vermez."""

import json
import os
import subprocess
import sys

data = json.load(sys.stdin)
if data.get("stop_hook_active"):  # sonsuz döngüyü önle
    sys.exit(0)

project = os.environ.get("CLAUDE_PROJECT_DIR", ".")
if not os.path.exists(os.path.join(project, "manage.py")):
    sys.exit(0)  # Django projesi henüz oluşturulmadı

result = subprocess.run(
    [sys.executable, "manage.py", "check"],
    check=False,
    cwd=project,
    capture_output=True,
    text=True,
)
if result.returncode != 0:
    print(
        "`python manage.py check` başarısız. Bitirmeden önce düzelt:\n"
        + result.stderr[-3000:],
        file=sys.stderr,
    )
    sys.exit(2)
sys.exit(0)
