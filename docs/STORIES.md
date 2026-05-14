# User Stories

> Every story below has a stable ID, a Given/When/Then statement, and numbered
> manual steps the TA can follow against the live `docker compose up` system.
> The TA scores Application Functionality (20 points) by walking these stories
> against the live UI in Phase 3 of grading.
>
> Format conventions:
>   * Story IDs are US-NN (US-01, US-02, ...). Filenames lowercase the prefix
>     and use underscores: US-01 maps to `test_us_01.py` and `us_01_expected.png`.
>   * Every story has a corresponding test in `tests/user_stories/`.
>   * Every story has a reference screenshot in `docs/assets/stories/`.
>   * Stories that exercise error paths are marked with [ERROR PATH] in the title.
>     At least 2 stories must be error path stories per the rubric.

---

## US-01: User submits a query and receives a cited answer

**As a** researcher
**I want** to submit a question and receive an answer with citations
**So that** I can trust where the information came from.

**Acceptance criteria (Given / When / Then):**

> Given the application is running and the corpus is indexed,
> When the user submits the query "What is FIPS 140-3?",
> Then the response contains a non-empty answer string and at least one citation
> with a doc_id and snippet, and the latency is under 3 seconds.

**Manual walkthrough steps:**

1. Confirm the app is running by visiting http://localhost:8080. The home page
   shows a search box and a "Submit" button.
2. Type "What is FIPS 140-3?" into the search box.
3. Click "Submit".
4. Observe the response area below the search box. It populates within 3 seconds.
5. Verify that the response contains:
   (a) an answer paragraph (non-empty),
   (b) a "Citations" subsection with at least one entry,
   (c) each citation showing a document title and a quoted snippet.
6. Compare the screen to `docs/assets/stories/us_01_expected.png`. The layout
   should match (exact text content will vary).
7. If the text box responds with 'Knowledge graph not loaded. Run python run_build_kg.py first.'
   (a) Manual: Run the command ' docker compose exec app python src/myproject/run_build_kg.py' in the terminal.
   (b) UI: Use the training tab to manually select what you want trained.

**Expected end state:** see `docs/assets/stories/us_01_expected.png`.

---

## US-02 [ERROR PATH]: Empty input shows an actionable error message

**As a** user
**I want** clear feedback when I submit an empty query
**So that** I know what to fix.

**Acceptance criteria (Given / When / Then):**

> Given the application is running,
> When the user clicks Submit without typing anything,
> Then an inline error message appears stating "Please enter a question",
> and no API call is made.

**Manual walkthrough steps:**

1. Confirm the app is running at http://localhost:8080.
2. Leave the search box empty.
3. Click "Submit".
4. Observe the error message that appears next to the search box: "Please enter a question".
5. Verify the response area below the search box is unchanged from the
   previous state (no spinner, no stack trace, no blank answer).
6. Open browser dev tools, Network tab, confirm no request was sent to /api/query.
7. Compare to `docs/assets/stories/us_02_expected.png`.

**Expected end state:** see `docs/assets/stories/us_02_expected.png`.

---

> Add stories US-04, US-05, ... here for every major feature in the spec.
> Repeat the format above. Each story must have:
>   - A stable ID
>   - Given / When / Then
>   - Numbered manual steps a human can follow without reading source code
>   - A reference screenshot in docs/assets/stories/
>   - A matching test in tests/user_stories/test_us_NN.py

---

## US-03: Train the Knowledge Graph on the Built-in Eval Corpus

**As a** developer or grader,
**I want to** build a HippoRAG knowledge graph from the bundled evaluation corpus,
**So that** the system is ready to answer questions without requiring any external dataset.

**Acceptance criteria (Given / When / Then):**

> Given the application is running and no knowledge graph has been loaded yet,
> When the user navigates to the Train page, selects the built-in eval corpus, and clicks "Build Knowledge Graph",
> Then the build log streams progress in real time, the build completes successfully, the model is listed in the saved-models table, and the KG status badge updates to show nodes and edges.

**Manual walkthrough steps:**

1. Confirm the app is running at `http://localhost:8080`.
2. Navigate to `http://localhost:8080/train`.
3. In **Panel 1 (Current Knowledge Graph Status)**, confirm the badge reads "⚠ No knowledge graph loaded" (or note the currently loaded model name if one is already present).
4. In **Panel 2 (Train a New Knowledge Graph)**, confirm the **Dataset** selector defaults to "Built-in eval corpus (10 docs — scientists)". Leave it set to this value.
5. In the **"Save model as"** field, confirm the value is `latest` (or type `latest` explicitly).
6. Click **"Build Knowledge Graph"**.
7. Confirm a build log box appears below the button and begins streaming progress lines within 3 seconds. Example lines to look for:
   - `Starting KG build: dataset='eval_corpus' ...`
   - `Processing document 1/10`
   - `Extracted N triples`
   - `Encoding N unique entities...`
   - `Build complete: N nodes, N edges`
8. Wait for the log to display a line beginning with `✓` or containing "is live". This confirms the build finished successfully.
9. Scroll down to **Panel 4 (Load a Saved Knowledge Graph)**. Confirm the saved-models table now contains a row named `latest` with non-zero node and edge counts.
11. Select `load`to load the model and continue with testing.
10. Scroll back up to **Panel 1**. Click **"Refresh Status"**. Confirm the badge now reads "✓ Knowledge graph loaded" and shows a non-zero node count.
11. Navigate to `http://localhost:8080` (the Query page) and submit the question: `"Where was Marie Curie born?"`. Confirm a non-empty answer is returned.

**Expected end state:** The KG status badge shows loaded with at least 50 nodes. The Query page returns an answer that references Warsaw or Poland.

---


## US-04: Retrieved Passages Are Visible Alongside the Answer

**As a** user,
**I want to** see which source passages were used to generate the answer,
**So that** I can verify the answer is grounded in the documents.

### Acceptance Criteria

- **Given** the user has submitted a question (US-01),
- **When** the answer is displayed,
- **Then** the retrieved passages are listed below the answer, each as a separate item.

### Manual Steps

1. Complete steps 1–3.
2. Confirm that there is a KG loaded.
3. Traverse to the Query page and try a question like `Who is Albert Einstein?`.
4. Confirm a section labeled **"Retrieved Passages"** is visible on the page.
5. Confirm that the `Answer` section contains an answer.
6. Confirm each passage is displayed as a distinct list item or card. (No duplicates.)
7. Confirm at least one passage is a full sentence from the corpus (not a node name or empty string).
8. Confirm the number of passages shown is between 1 and 5 (matching `top_k` in config).

---

## US-05 [ERROR PATH]: Missing API key surfaces a clear server error

**As an** operator
**I want** to know when an upstream LLM credential is missing
**So that** I can fix configuration without reading logs.

**Acceptance criteria (Given / When / Then):**

> Given the application is running with an empty ANTHROPIC_API_KEY,
> When the user submits any non-empty query,
> Then the response shows "The model service is not configured. Contact the operator."
> and the HTTP status is 503, not 500.

**Manual walkthrough steps:**

1. Stop the running application: Ctrl-C in the docker compose terminal.
2. Edit `.env` and set `ANTHROPIC_API_KEY=` (empty).
3. Start the application: `docker compose up`.
4. Visit http://localhost:8080.
5. Type any non-empty query, e.g. "hello", and click Submit.
6. Observe the error message: "The model service is not configured. Contact the operator."
7. In dev tools Network tab, confirm the response status is 503.
8. Confirm no Python stack trace appears anywhere in the UI.
9. Compare to `docs/assets/stories/us_03_expected.png`.

**Expected end state:** see `docs/assets/stories/us_03_expected.png`.

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


---


## US-07: Run Evaluation and View Metrics

**As a** researcher,
**I want to** trigger the evaluation pipeline from the web interface,
**So that** I can see Recall@k, Exact Match, and F1 scores for the system.

### Acceptance Criteria

- **Given** the knowledge graph has been built,
- **When** the user navigates to the Evaluate page and clicks **"Run Evaluation"**,
- **Then** the system displays Recall@1, Recall@2, Recall@5, Exact Match, and F1 scores.

### Manual Steps

1. Open a browser and navigate to `http://localhost:8080/evaluate`.
2. Confirm the page loads with a **"Run Evaluation"** button.
3. Click **"Run Evaluation"**.
4. Wait for the results to appear (may take up to 60 seconds).
5. Confirm a results table appears with rows for: `Recall@1`, `Recall@2`, `Recall@5`, `ExactMatch`, `F1`.
6. Confirm all values are numeric and between 0.0 and 1.0.

**Reference screenshot:** `docs/assets/stories/us_04_expected.png`

---



---

## US-08: Load HotPotQA Model

**As a** researcher,
**I want to** load the pretrained Hotpot2 model of hippoRAG for the HotPotQA dataset.
**So that** I can evaluate the system and test the improvements of HippoRAG against a base method mentioned later.    

**Acceptance criteria (Given / When / Then):**

> Given the application is running, a valid HotPotQA JSON file trained model has been placed in the `data/hotpot2/` directory,
> When the user navigates to the Train page, scrolls down to the `Load a Saved Knowledge Graph` and select `load` for the hotpot2 model.
> Then navigate back to the query page.

**Manual walkthrough steps:**

1. Confirm the app is running at `http://localhost:8080`.

3. Navigate to `http://localhost:8080/train`.

3. In **Panel 4 (Load a Saved Knowledge Graph)**, load the hotpot2 model.   

4. Confirm the success callout reads: `✓ Loaded 'hotpotqa': N nodes, N edges.` where N is greater than the node count of the `latest` (built-in) model.

5. Navigate to `http://localhost:8080` (the Query page) and submit a multi-hop question from the HotPotQA dataset. Confirm a non-empty answer is returned.

**Expected end state:** A `hotpotqa` trained model is listed in Panel 4 and is the active KG. The Query page answers questions using passages from the HotPotQA corpus.

**Reference screenshot 1:** `docs/assets/stories/us_08_expected_a.png`

**Reference screenshot 2:** `docs/assets/stories/us_09_expected_b.png`

---



## US-09: Check that the Hotpot2 model is loaded and working.

**As a** user,
**I want to** see which source passages were used to generate the answer,
**So that** I can verify the answer is grounded in the documents.

### Acceptance Criteria

- **Given** the user has submitted a question (US-01),
- **When** the answer is displayed,
- **Then** the retrieved passages are listed below the answer, each as a separate item.

### Manual Steps

1. Complete US-06.
2. Confirm that there is a KG loaded.
3. Run a query. Ask a question like `The fictional private detective that appears in "The Adventure of the Seven Clocks" what written by whom?`.
4. Confirm each passage is displayed as a distinct list item or card. (No duplicates.)
5. Confirm at least one passage is a full sentence from the corpus (not a node name or empty string).
6. Confirm the number of passages shown is between 1 and 5 (matching `top_k` in config).

**Reference screenshot:** `docs/assets/stories/us_09_expected.png`

---

## US-10: Run Evaluation Against a Custom JSON Dataset

**As a** researcher,
**I want to** upload a JSON question file and run the evaluation pipeline against it,
**So that** I can benchmark the system on standard multi-hop datasets like HotpotQA or MuSiQue.

### Acceptance Criteria

- **Given** the knowledge graph is loaded and a valid JSON eval file exists in the `data/` directory,
- **When** the user navigates to the Evaluate page, selects the file, and clicks **"Run Evaluation"**,
- **Then** the system returns per-question EM, F1, and Recall@k scores plus aggregate metrics.

### Manual Steps

1. Confirm the app is running at `http://localhost:8080`.
2. Place a valid eval JSON file (e.g. `hotpotqa.json`) in the `data/` directory.
3. Navigate to `http://localhost:8080/evaluate`.
4. In the eval file picker dropdown, select `hotpotqa.json`.
5. Optionally set a question limit (e.g. 50) to keep the run short.
6. Click **"Run Evaluation"**.
7. Confirm a progress indicator is visible while evaluation runs.
8. Confirm the results table appears with rows for `Recall@1`, `Recall@2`, `Recall@5`, `ExactMatch`, and `F1`.
9. Confirm all values are numeric and between 0.0 and 1.0.
10. Confirm a checkpoint file (e.g. `eval_checkpoint.json`) appears in `data/` during the run.

