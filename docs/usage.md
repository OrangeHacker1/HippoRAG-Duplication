# Usage Guide

> Every feature listed in `docs/STORIES.md` must have a corresponding section here.
> The TA verifies this mapping during the Documentation walkthrough.

## Submitting a query (US-01)

To ask a question:

1. Visit http://localhost:8080.
2. Type your question in the search box.
3. Click "Submit".
4. The answer appears below the search box, with citations.

Tips:
- Questions phrased as full sentences work better than keyword fragments.
- The system retrieves the top 5 most relevant documents by default. To change,
  pass `max_results` in the API request body (see `docs/SPEC.md` section 4.1).

## Empty input handling (US-02)

If you click Submit without typing anything, the UI displays
"Please enter a question" inline. No API call is made, so no quota is consumed.

## Configuration troubleshooting (US-03)

If the system shows "The model service is not configured", the
`ANTHROPIC_API_KEY` is missing or empty in `.env`. Stop the app, edit `.env`,
and run `docker compose up` again.

> Add one section per story.

## Retrieved Passages Are Visible Alongside the Answer (US-04)

This is to make sure results are being properly returned. If empty results are being returned, either the RAG was not properly populated or the LLM is having issues reaching the RAG.

## Running the evaluation pipeline (US-05)

To measure system performance against the built-in multi-hop test dataset:

1. Visit http://localhost:8080/evaluate.
2. Confirm the knowledge graph has been built first. If not, run:
```bash
   docker compose exec app python run_build_kg.py
```
3. Click "Run Evaluation". The pipeline may take up to 60 seconds to complete.
4. A results table appears showing aggregate scores for:
   Recall@1, Recall@2, Recall@5, ExactMatch, and F1.
5. Per-question results are shown below the aggregate table, including the
   retrieved passages and per-question scores.

Note: All metric values are between 0.0 and 1.0. Higher is better.

## LLM unavailable error (US-06)

If the LLM endpoint is unreachable or misconfigured, the system returns HTTP 503
with the message "The language model is currently unavailable. Please try again
later." No stack trace is exposed to the user.

To reproduce this intentionally for testing:

1. Stop the system: `docker compose down`.
2. Edit `.env` and point the LLM URL variable to an unreachable address.
3. Restart: `docker compose up`.
4. Submit any question — the error message will appear in the UI.
5. Restore the correct URL in `.env` and restart before normal use.