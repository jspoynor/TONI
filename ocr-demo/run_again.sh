#!/usr/bin/env bash
set -euo pipefail
DEMO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NEMO_PYTHON="${NEMO_PYTHON:-python3}"
"$NEMO_PYTHON" "$DEMO_ROOT/sample-data/developer/extract_local.py" "$DEMO_ROOT/sample-data/uploads/03_scanned_monthly.pdf" --output "$DEMO_ROOT/ocr-demo/ocr_pages.json"
