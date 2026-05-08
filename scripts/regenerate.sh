#!/usr/bin/env bash
# Feeds docs/SPEC.md to Claude Opus and runs user story tests against the generated code.
# Requires: ANTHROPIC_API_KEY environment variable
set -e

SPEC="docs/SPEC.md"
PROMPT="scripts/regenerate_prompt.md"
OUTPUT_DIR="reports/regenerated"
MODEL="claude-opus-4-5-20251101"

mkdir -p "$OUTPUT_DIR"

if [ ! -f "$SPEC" ]; then
  echo "ERROR: $SPEC not found."
  exit 1
fi

if [ ! -f "$PROMPT" ]; then
  echo "ERROR: $PROMPT not found."
  exit 1
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set."
  echo "Export it before running: export ANTHROPIC_API_KEY=sk-ant-..."
  exit 1
fi

echo "Running spec regeneration test..."
echo "Model: $MODEL"
echo "Spec:  $SPEC"
echo "Output: $OUTPUT_DIR"
echo ""

python3 scripts/_regenerate_helper.py "$SPEC" "$PROMPT" "$OUTPUT_DIR" "$MODEL"

echo ""
echo "Running user story tests against regenerated code..."
.venv/bin/pytest tests/user_stories/ \
  --rootdir="$OUTPUT_DIR" \
  --junitxml=reports/regeneration_results.xml \
  -v 2>&1 || true

echo ""
if [ -f reports/regeneration_results.xml ]; then
  PASSED=$(python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('reports/regeneration_results.xml')
root = tree.getroot()
suite = root if root.tag == 'testsuite' else root.find('testsuite')
passed = int(suite.get('tests', 0)) - int(suite.get('failures', 0)) - int(suite.get('errors', 0))
print(passed)
" 2>/dev/null || echo 0)
  echo "Regeneration score: $PASSED / 6 stories passed"
  python3 -c "print(f'Score = {int(\"$PASSED\") / 6 * 25:.1f} / 25 pts')"
fi
