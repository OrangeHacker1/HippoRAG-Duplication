#!/usr/bin/env bash
# Run all automated checks the TA will run. Pass = ready to push.
set -e

PASS=0
FAIL=0

run_check() {
  local name="$1"
  shift
  echo -n "[$name] ... "
  if "$@" > /dev/null 2>&1; then
    echo "PASS"
    PASS=$((PASS + 1))
  else
    echo "FAIL"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== HippoRAG Preflight ==="
echo ""

run_check "ruff"       ruff check .
run_check "black"      black --check .
run_check "mypy"       mypy kg/ retrieval/ llm/ api/ --ignore-missing-imports
run_check "pip-audit"  pip-audit
run_check "pytest"     pytest tests/ -q
run_check ".env.example exists"    test -f .env.example
run_check "docs/SPEC.md exists"    test -f docs/SPEC.md
run_check "docs/STORIES.md exists" test -f docs/STORIES.md
run_check "grading/manifest.yaml"  test -f grading/manifest.yaml
run_check "grading/traceability.yaml" test -f grading/traceability.yaml
run_check "CONTRIBUTIONS.md"       test -f CONTRIBUTIONS.md

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [ "$FAIL" -gt 0 ]; then
  echo "Preflight FAILED. Fix the above before pushing."
  exit 1
else
  echo "Preflight PASSED."
fi
