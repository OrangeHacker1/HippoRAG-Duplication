# Usage Guide

## US-01: Submit a Query and Receive an Answer

1. Open `http://localhost:8000` in your browser.
2. Type a question into the **"Ask a question"** field.
3. Click **Submit** (or press Enter).
4. The **Answer** section appears with a generated response.

**Example input:** `Who influenced physics through relativity?`
**Expected output:** An answer referencing Albert Einstein and the theory of relativity.

---

## US-02: View Retrieved Passages

After submitting a query (US-01), scroll below the answer to the **Retrieved Passages** section. Each passage is a sentence from the corpus that the system used to generate the answer.

---

## US-03: System Health Check

To verify the system is running:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok"}
```

---

## US-04: Run Evaluation

1. Open `http://localhost:8000/evaluate` in your browser.
2. Click **Run Evaluation**.
3. Wait for the results (up to 60 seconds).
4. An aggregate table shows Recall@1, Recall@2, Recall@5, ExactMatch, and F1.
5. Per-question results appear below the table.

---

## US-05: Empty Query Error

If you submit an empty or whitespace-only question, the system displays:

> **Query must not be empty.**

No answer is generated. Correct your input and resubmit.

---

## US-06: LLM Unavailable Error

If the configured LLM endpoint is unreachable, the system displays:

> **The language model is currently unavailable. Please try again later.**

Check your `.env` configuration and verify the LLM server is running.
