#!/usr/bin/env bash
# Single entry point for every check. CI runs exactly this script.
#   ./scripts/check.sh          lint + format-check + validate + tests
# To auto-fix formatting/lint: npm run fix
set -uo pipefail

cd "$(dirname "$0")/.."

FAILED=()

run() {
  local name="$1"
  shift
  printf '\n\033[1m==> %s\033[0m\n' "$name"
  if "$@"; then
    return 0
  fi
  FAILED+=("$name")
  return 0
}

require() {
  command -v "$1" >/dev/null 2>&1 && return 0
  printf '\n\033[31mMissing tool: %s\033[0m — %s\n' "$1" "$2"
  FAILED+=("$1 not installed")
  return 1
}

if require ruff "brew install ruff (or pipx install ruff)"; then
  run "ruff lint (scripts/)" ruff check scripts
  run "ruff format check (scripts/)" ruff format --check scripts
fi

if [ -d node_modules ]; then
  run "biome (js/css/json)" npx --no-install biome ci .
  run "html-validate" npx --no-install html-validate ./*.html
else
  printf '\n\033[31mmissing node_modules\033[0m — run: npm install\n'
  FAILED+=("npm install not run")
fi

run "validate data" python3 scripts/validate.py

if compgen -G "tests/*.test.js" >/dev/null; then
  run "node tests" node --test tests/
fi

printf '\n'
if [ ${#FAILED[@]} -eq 0 ]; then
  printf '\033[32mAll checks passed.\033[0m\n'
  exit 0
fi
printf '\033[31mFAILED: %s\033[0m\n' "${FAILED[*]}"
exit 1
