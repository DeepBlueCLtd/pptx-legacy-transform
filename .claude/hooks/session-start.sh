#!/bin/bash
set -euo pipefail

# Only run inside Claude Code on the web; local sessions manage their own env.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"

# python-pptx is the sole runtime dep (see requirements.txt). Tests for
# extract_to_csv / introspect_pptx / mock_pptx all import it transitively,
# so the suite cannot even collect without it.
python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt
