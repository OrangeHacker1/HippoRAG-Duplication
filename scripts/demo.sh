#!/usr/bin/env bash
set -e

BASE="http://localhost:8000"

echo "=== HippoRAG Demo ==="
echo ""

echo "[1] Health check..."
curl -s "$BASE/health"
echo ""

echo "[2] Submitting query: 'What country was Marie Curie born in?'"
curl -s -X POST "$BASE/api/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What country was Marie Curie born in?"}' | python3 -m json.tool
echo ""

echo "[3] Submitting empty query (expect 422)..."
curl -s -X POST "$BASE/api/query" \
  -H "Content-Type: application/json" \
  -d '{"question": ""}' | python3 -m json.tool
echo ""

echo "[4] Running evaluation..."
curl -s -X POST "$BASE/api/evaluate" | python3 -m json.tool
echo ""

echo "=== Demo complete ==="
