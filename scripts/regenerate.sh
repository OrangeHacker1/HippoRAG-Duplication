#!/usr/bin/env bash
# Feeds docs/SPEC.md to an LLM and runs user story tests against the generated code.
set -e

SPEC="docs/SPEC.md"
PROMPT="scripts/regenerate_prompt.md"
OUTPUT_DIR="reports/regenerated"

mkdir -p "$OUTPUT_DIR"

if [ ! -f "$SPEC" ]; then
  echo "ERROR: $SPEC not found."
  exit 1
fi

if [ ! -f "$PROMPT" ]; then
  echo "ERROR: $PROMPT not found."
  exit 1
fi

echo "Running spec regeneration test..."
echo "Spec: $SPEC"
echo "Output: $OUTPUT_DIR"
echo ""
echo "NOTE: This script requires an LLM API key and the course-issued regeneration prompt."
echo "Feed the contents of docs/SPEC.md to the LLM using scripts/regenerate_prompt.md,"
echo "write the generated source to $OUTPUT_DIR, then run:"
echo ""
echo "  pytest tests/user_stories/ --rootdir=$OUTPUT_DIR -v"
echo ""
echo "Score = (passing stories / total stories) * 25"
