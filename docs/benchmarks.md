# Benchmarks

## Hardware

| Component | Specification |
|---|---|
| OS | Ubuntu 22.04 / WSL2 |
| CPU | x86_64 |
| RAM | 8 GB |
| LLM | Remote endpoint (latency varies) |

## Methodology

Load test run with [Locust](https://locust.io) against `docker compose up` system.

- **Duration:** 60 seconds
- **Users:** 10 concurrent
- **Spawn rate:** 2 users/second
- **Endpoint:** `POST /api/query`

Run with:
```bash
make loadtest
```

Raw results saved to `reports/benchmarks.json`.

## Headline Numbers

| Metric | Value |
|---|---|
| Target RPS | ≥ 10 requests/second |
| Target error rate | < 5% |
| `/health` p99 latency | < 50ms |
| `/api/query` p99 latency | Depends on LLM endpoint |

Note: `/api/query` latency is dominated by the external LLM endpoint. The application itself adds minimal overhead.
