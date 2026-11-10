#!/usr/bin/env bash
# Upload prebuilt maix_lvgl wheels to PyPI or TestPyPI.
#
# Usage:
#   scripts/publish.sh [testpypi|pypi] [wheel ...]
#
# Without wheel arguments, every dist/*.whl is uploaded.  Only wheels are
# passed to twine, so dist/maix_lvgl_release/ is never touched.
#
# Credentials:
#   export TWINE_PASSWORD=pypi-...        # API token (recommended)
#   or configure ~/.pypirc
#
# See docs/README.md for the full release checklist.
set -euo pipefail

usage() {
  cat <<'EOF'
usage: scripts/publish.sh [testpypi|pypi] [wheel ...]

  testpypi   upload to https://test.pypi.org (default)
  pypi       upload to the real PyPI

Without wheel arguments, every dist/*.whl is uploaded.

Credentials:
  export TWINE_PASSWORD=pypi-...        # API token
  or configure ~/.pypirc

Environment:
  TWINE_USERNAME   defaults to __token__
  PUBLISH_YES=1    skip the interactive confirmation for the real PyPI
EOF
}

repo="testpypi"
if [[ $# -gt 0 && ( "$1" == "testpypi" || "$1" == "pypi" ) ]]; then
  repo="$1"
  shift
fi

case "$repo" in
  testpypi) index_url="https://test.pypi.org/legacy/" ;;
  pypi)     index_url="https://upload.pypi.org/legacy/" ;;
  *) usage; exit 2 ;;
esac

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dist="$root/dist"

if ! python3 -m twine --version >/dev/null 2>&1; then
  echo "error: twine is not installed; run: python3 -m pip install twine" >&2
  exit 1
fi

wheels=()
if [[ $# -gt 0 ]]; then
  wheels=("$@")
else
  while IFS= read -r -d '' wheel; do
    wheels+=("$wheel")
  done < <(find "$dist" -maxdepth 1 -type f -name '*.whl' -print0 | sort -z)
fi

if [[ ${#wheels[@]} -eq 0 ]]; then
  echo "error: no wheels in $dist; build them first (see docs/README.md)" >&2
  exit 1
fi

for wheel in "${wheels[@]}"; do
  if [[ ! -f "$wheel" ]]; then
    echo "error: no such file: $wheel" >&2
    exit 1
  fi
  case "$(basename "$wheel")" in
    maix_lvgl-*.whl) ;;
    *) echo "error: not a maix_lvgl wheel: $wheel" >&2; exit 1 ;;
  esac
done

echo "== target: $repo ($index_url)"
echo "== files:"
for wheel in "${wheels[@]}"; do
  printf '   %-72s %8s\n' "$(basename "$wheel")" "$(du -h "$wheel" | cut -f1)"
done

echo
echo "== twine check"
python3 -m twine check "${wheels[@]}"

if [[ "$repo" == "pypi" && "${PUBLISH_YES:-0}" != "1" ]]; then
  echo
  read -r -p "Upload these files to the real PyPI? Type 'yes' to continue: " answer
  if [[ "$answer" != "yes" ]]; then
    echo "aborted"
    exit 1
  fi
fi

# twine reads TWINE_PASSWORD from the environment; never pass it on the
# command line (it would show up in the process list).
export TWINE_USERNAME="${TWINE_USERNAME:-__token__}"
echo
echo "== twine upload"
python3 -m twine upload --repository-url "$index_url" "${wheels[@]}"

echo
echo "done. verify with:"
if [[ "$repo" == "testpypi" ]]; then
  echo "  python3 -m pip install --index-url https://test.pypi.org/simple/ \\"
  echo "      --extra-index-url https://pypi.org/simple/ maix-lvgl"
else
  echo "  python3 -m pip install --force-reinstall --no-deps maix-lvgl"
fi
