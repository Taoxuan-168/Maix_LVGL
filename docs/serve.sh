#!/usr/bin/env bash
# Preview the generated API documentation with teedoc.
#
#   docs/serve.sh
#   docs/serve.sh --port 8080
set -euo pipefail

docs_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$docs_dir"

if [ ! -d api ]; then
    echo "error: docs/api/ not found." >&2
    echo "Build the API documentation first:" >&2
    echo "  python3 tools/gen_api_docs.py --pyi binding/lvgl.pyi --out docs/api" >&2
    echo "If binding/lvgl.pyi is also missing, run a MaixCDK build first:" >&2
    echo "  python3 setup.py bdist_wheel --board maixcam2" >&2
    exit 1
fi

exec teedoc serve "$@"
