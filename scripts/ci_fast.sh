#!/usr/bin/env bash
# Offline checks after pinned SDK installation. Never run live adapter commands.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/check_docs.py
python3 - <<'PY'
import ast
from pathlib import Path
for file in list(Path('scripts').glob('*.py')) + list(Path('poc/native-value').rglob('*.py')) + list(Path('poc/takeover').rglob('*.py')) + list(Path('poc/shielded-design').rglob('*.py')) + list(Path('poc/groth16-comparison').rglob('*.py')) + list(Path('poc/accelerated-bn254').rglob('*.py')) + list(Path('poc/outer-proof-128m').rglob('*.py')) + list(Path('poc/proof-phase-diagnostics').rglob('*.py')):
    ast.parse(file.read_text(), filename=str(file))
print('Python syntax: OK')
PY
python3 -m unittest discover -s poc/proof-phase-diagnostics -p 'test_*.py' -v
if compgen -G 'scripts/test_*.py' >/dev/null; then
    python3 -m unittest discover -s scripts -p 'test_*.py' -v
else
    echo 'No Python unit tests in this ref; A1 tests run only where A1 source exists.'
fi
for kpi_ci_js in scripts/*.mjs; do node --check "$kpi_ci_js"; done
node --test scripts/*.test.mjs
if [[ -f poc/lane-completeness/integration/test-exact-json.mjs ]]; then
    node poc/lane-completeness/integration/test-exact-json.mjs
    python3 poc/lane-completeness/integration/check_rpc_derivatives.py
    for kpi_ci_js in poc/lane-completeness/integration/*.mjs poc/native-value/remote/*.mjs poc/takeover/remote/*.mjs; do node --check "$kpi_ci_js"; done
fi
git diff --check
if [[ -f poc/shielded-design/test_model.py ]]; then
    PYTHONPATH="$PWD/.local/shielded-design/python${PYTHONPATH:+:$PYTHONPATH}" \
        python3 -m unittest discover -s poc/shielded-design -p 'test_*.py' -v
fi
