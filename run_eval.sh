#!/bin/bash

echo "Loading hotpotqa1 model..."
curl -s -X POST http://localhost:8080/api/kg/load \
  -H "Content-Type: application/json" \
  -d '{"name": "hotpotqa1"}'

echo ""
echo "Starting HotpotQA eval (500 questions)..."
curl -s -X POST http://localhost:8080/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{"json_filename": "hotpotqa.json", "limit": 500, "checkpoint_file": "hotpotqa_500_results.json"}' \
  > data/hotpotqa_500_final.json

echo "HotpotQA done. Starting MuSiQue eval (500 questions)..."
curl -s -X POST http://localhost:8080/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{"json_filename": "musique.json", "limit": 500, "checkpoint_file": "musique_500_results.json"}' \
  > data/musique_500_final.json

echo "All done!"
