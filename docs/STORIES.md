# User Stories

All stories are exercised against the running system started with `docker compose up`.
The UI is served at `http://localhost:8000`. The API is at `http://localhost:8000/api`.

---

## US-01: Submit a Query and Receive an Answer

**As a** user,
**I want to** type a natural language question into the web interface,
**So that** I receive a generated answer backed by retrieved passages from the knowledge graph.

### Acceptance Criteria

- **Given** the system is running and the knowledge graph has been built,
- **When** the user submits a non-empty question,
- **Then** the system returns a generated answer string and at least one retrieved passage.

### Manual Steps

1. Open a browser and navigate to `http://localhost:8000`.
2. Confirm the page loads with a text input field labeled **"Ask a question"** and a **"Submit"** button.
3. Type the following question into the input field:
   `Who influenced physics through relativity?`
4. Click **Submit**.
5. Confirm the page updates to show a section labeled **"Answer"** containing a non-empty string.
6. Confirm the page shows a section labeled **"Retrieved Passages"** containing at least one passage.
7. Confirm the answer references Einstein or relativity.

**Reference screenshot:** `docs/assets/stories/us_01_expected.png`

---

## US-02: Retrieved Passages Are Visible Alongside the Answer

**As a** user,
**I want to** see which source passages were used to generate the answer,
**So that** I can verify the answer is grounded in the documents.

### Acceptance Criteria

- **Given** the user has submitted a question (US-01),
- **When** the answer is displayed,
- **Then** the retrieved passages are listed below the answer, each as a separate item.

### Manual Steps

1. Complete steps 1–4 of US-01.
2. Confirm a section labeled **"Retrieved Passages"** is visible on the page.
3. Confirm each passage is displayed as a distinct list item or card.
4. Confirm at least one passage is a full sentence from the corpus (not a node name or empty string).
5. Confirm the number of passages shown is between 1 and 5 (matching `top_k` in config).

**Reference screenshot:** `docs/assets/stories/us_02_expected.png`

---

## US-03: System Health Check

**As a** developer or operator,
**I want to** query a `/health` endpoint,
**So that** I can verify the system is running and ready to serve requests.

### Acceptance Criteria

- **Given** the system is running via `docker compose up`,
- **When** a GET request is sent to `/health`,
- **Then** the response is HTTP 200 with body `{"status": "ok"}`.

### Manual Steps

1. Open a terminal.
2. Run: `curl -s http://localhost:8000/health`
3. Confirm the output is: `{"status":"ok"}`
4. Confirm the HTTP status code is 200 by running:
   `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health`
5. Confirm the output is `200`.

**Reference screenshot:** `docs/assets/stories/us_03_expected.png`

---

## US-04: Run Evaluation and View Metrics

**As a** researcher,
**I want to** trigger the evaluation pipeline from the web interface,
**So that** I can see Recall@k, Exact Match, and F1 scores for the system.

### Acceptance Criteria

- **Given** the knowledge graph has been built,
- **When** the user navigates to the Evaluate page and clicks **"Run Evaluation"**,
- **Then** the system displays Recall@1, Recall@2, Recall@5, Exact Match, and F1 scores.

### Manual Steps

1. Open a browser and navigate to `http://localhost:8000/evaluate`.
2. Confirm the page loads with a **"Run Evaluation"** button.
3. Click **"Run Evaluation"**.
4. Wait for the results to appear (may take up to 60 seconds).
5. Confirm a results table appears with rows for: `Recall@1`, `Recall@2`, `Recall@5`, `ExactMatch`, `F1`.
6. Confirm all values are numeric and between 0.0 and 1.0.

**Reference screenshot:** `docs/assets/stories/us_04_expected.png`

---

## US-05: Empty Query Returns a Descriptive Error (Error Path)

**As a** user,
**I want to** receive a clear error message when I submit an empty question,
**So that** I understand what went wrong and can correct my input.

### Acceptance Criteria

- **Given** the system is running,
- **When** the user submits an empty or whitespace-only query,
- **Then** the system returns HTTP 422 and displays the message: `"Query must not be empty."`.

### Manual Steps

1. Open a browser and navigate to `http://localhost:8000`.
2. Leave the question input field blank.
3. Click **Submit**.
4. Confirm an error message is displayed on the page reading: **"Query must not be empty."**
5. Confirm the page does not crash or show an unhandled exception.
6. Verify via curl:
   `curl -s -X POST http://localhost:8000/api/query -H "Content-Type: application/json" -d '{"question": ""}'`
7. Confirm the response contains `"Query must not be empty."` and HTTP status 422.

**Reference screenshot:** `docs/assets/stories/us_05_expected.png`

---

## US-06: LLM Timeout Returns a Graceful Error (Error Path)

**As a** user,
**I want to** see a friendly error message when the LLM is unreachable,
**So that** the application does not crash or expose internal stack traces.

### Acceptance Criteria

- **Given** the LLM endpoint is unreachable (e.g. wrong URL in `.env`),
- **When** the user submits a valid question,
- **Then** the system returns HTTP 503 and displays the message: `"The language model is currently unavailable. Please try again later."`.

### Manual Steps

1. Stop the running system: `docker compose down`.
2. Edit `.env` and set `TEACHER_BASE_URL` to an unreachable address (e.g. `http://localhost:9999/v1`).
3. Restart: `docker compose up -d`.
4. Open a browser and navigate to `http://localhost:8000`.
5. Type any question and click **Submit**.
6. Confirm an error message is displayed: **"The language model is currently unavailable. Please try again later."**
7. Confirm no Python stack trace is visible on the page.
8. Restore the original `TEACHER_BASE_URL` in `.env` and restart the system.

**Reference screenshot:** `docs/assets/stories/us_06_expected.png`
