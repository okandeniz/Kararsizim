#!/usr/bin/env python
"""Claude bitirmeden önce `manage.py check` çalıştırır; hata varsa bitirmesine izin vermez.

Türkçe Windows'ta varsayılan kodlama cp1254'tür. Alt süreç `PYTHONUTF8=1` ile UTF-8 yazar ve
çıktı UTF-8 olarak okunur; hata metni de UTF-8 baytlarıyla geri verilir.
"""

import json
import os
import subprocess
import sys

data = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
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
    encoding="utf-8",
    errors="replace",
    env={**os.environ, "PYTHONUTF8": "1"},
)
if result.returncode != 0:
    message = (
        "`python manage.py check` başarısız. Bitirmeden önce düzelt:\n" + result.stderr[-3000:]
    )
    sys.stderr.buffer.write(message.encode("utf-8", errors="replace"))
    sys.stderr.flush()
    sys.exit(2)
sys.exit(0)
