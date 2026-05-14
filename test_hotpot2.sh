#!/bin/bash
# Samantha's test script for hotpot2 — HippoRAG vs Dense baseline
# Usage: ./test_hotpot2.sh

LIMIT=50   # change to 500 for full overnight run

echo "=== Loading hotpot2 model ==="
curl -s -X POST http://localhost:8080/api/kg/load \
  -H "Content-Type: application/json" \
  -d '{"name": "hotpot2"}' | python3 -m json.tool

echo ""
echo "=== Running HippoRAG eval ($LIMIT questions) ==="
curl -s -X POST http://localhost:8080/api/evaluate \
  -H "Content-Type: application/json" \
  -d "{\"json_filename\": \"hotpotqa.json\", \"limit\": $LIMIT, \"checkpoint_file\": \"hotpot2_hipporag_${LIMIT}_checkpoint.json\"}" \
  > data/hotpot2_hipporag_${LIMIT}_results.json

echo ""
echo "=== HippoRAG Results ==="
python3 -c "
import json
d = json.load(open('data/hotpot2_hipporag_${LIMIT}_results.json'))
print(f'Completed: {d[\"results\"].__len__()} questions')
for k, v in d['aggregate'].items():
    print(f'  {k}: {v}')
"

echo ""
echo "=== Switching to Dense baseline mode ==="
python3 -c "
import re
with open('src/myproject/config/config.yaml', 'r') as f:
    c = f.read()
c = re.sub(r'mode: \"hipporag\"', 'mode: \"dense\"', c)
with open('src/myproject/config/config.yaml', 'w') as f:
    f.write(c)
print('Config set to dense mode.')
"

echo "Restarting server..."
kill $(ps aux | grep uvicorn | grep -v grep | awk '{print $2}') 2>/dev/null
sleep 2
.venv/bin/uvicorn myproject.api.app:app --host 0.0.0.0 --port 8080 >> /tmp/hipporag_server.log 2>&1 &
echo "Waiting for server to be ready..."
until curl -s http://localhost:8080/health > /dev/null 2>&1; do
  sleep 2
done
echo "Server ready."

echo ""
echo "=== Loading hotpot2 model (dense mode) ==="
curl -s -X POST http://localhost:8080/api/kg/load \
  -H "Content-Type: application/json" \
  -d '{"name": "hotpot2"}' | python3 -m json.tool

echo ""
echo "=== Running Dense baseline eval ($LIMIT questions) ==="
curl -s -X POST http://localhost:8080/api/evaluate \
  -H "Content-Type: application/json" \
  -d "{\"json_filename\": \"hotpotqa.json\", \"limit\": $LIMIT, \"checkpoint_file\": \"hotpot2_dense_${LIMIT}_checkpoint.json\"}" \
  > data/hotpot2_dense_${LIMIT}_results.json

echo ""
echo "=== Dense Baseline Results ==="
python3 -c "
import json
d = json.load(open('data/hotpot2_dense_${LIMIT}_results.json'))
print(f'Completed: {d[\"results\"].__len__()} questions')
for k, v in d['aggregate'].items():
    print(f'  {k}: {v}')
"

echo ""
echo "=== Restoring HippoRAG mode ==="
python3 -c "
import re
with open('src/myproject/config/config.yaml', 'r') as f:
    c = f.read()
c = re.sub(r'mode: \"dense\"', 'mode: \"hipporag\"', c)
with open('src/myproject/config/config.yaml', 'w') as f:
    f.write(c)
print('Config restored to hipporag mode.')
"

echo ""
echo "=== Comparison Summary ==="
python3 -c "
import json
h = json.load(open('data/hotpot2_hipporag_${LIMIT}_results.json'))['aggregate']
d = json.load(open('data/hotpot2_dense_${LIMIT}_results.json'))['aggregate']
print(f'{'Metric':<15} {'HippoRAG':>10} {'Dense':>10}')
print('-' * 37)
for k in h:
    print(f'{k:<15} {h[k]:>10} {d[k]:>10}')
"
echo ""
echo "Done."
