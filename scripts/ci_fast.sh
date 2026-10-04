#!/usr/bin/env bash
# Offline checks after pinned SDK installation. Never run live adapter commands.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/check_docs.py
python3 - <<'PY'
import ast
from pathlib import Path
for file in Path('scripts').glob('*.py'):
    ast.parse(file.read_text(), filename=str(file))
print('Python syntax: OK')
PY
if compgen -G 'scripts/test_*.py' >/dev/null; then
    python3 -m unittest discover -s scripts -p 'test_*.py' -v
else
    echo 'No Python unit tests in this ref; A1 tests run only where A1 source exists.'
fi
for kpi_ci_js in scripts/*.mjs; do node --check "$kpi_ci_js"; done
node --test scripts/*.test.mjs
git diff --check
