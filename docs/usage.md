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

## Train the Knowledge Graph on the Built-in Eval Corpus (US-03)

This is to show that the project has the ability to run the train functions. Due to time constraints, the default data is designed to create a smaller HippoRAG model. It is also possible to run a json training file, but it will likely take hours to finish training due to the large sizes.
Make sure thst the log box properly returns trained values. If the model has issues reaching the LLM through the api key, then there will be issues.


## Retrieved Passages Are Visible Alongside the Answer (US-04)

This is to make sure results are being properly returned. If empty results are being returned, either the RAG was not properly populated or the LLM is having issues reaching the RAG.

## [ERROR PATH]: Missing API key surfaces a clear server error (US-05)

This is to make sure there are no castestrophic failures when there is a missing api key.

## LLM Timeout Returns a Graceful Error (Error Path) (US-06)

If the LLM endpoint is unreachable or misconfigured, the system returns HTTP 503
with the message "The language model is currently unavailable. Please try again
later." No stack trace is exposed to the user.

To reproduce this intentionally for testing:

1. Stop the system: `docker compose down`.
2. Edit `.env` and point the LLM URL variable to an unreachable address.
3. Restart: `docker compose up`.
4. Submit any question — the error message will appear in the UI.
5. Restore the correct URL in `.env` and restart before normal use.

## Run Evaluation and View Metrics (US-07)

After running the tests to ensure that the LLM is working, run the base evaluation method on the base model. This is to show that results can be recieved.

1. Navigate to the Evaluate page.
2. Run evaluate.
3. Observe the restuls.

## Load HotPotQA Model (US-08)

Since time is tight, there will be a presaved model that has been trained on HotPotQA.

## Check that the Hotpot2 model is loaded and working. (US-09)

This is designed to show that the loaded HotPot2 model can be used for queries.

## Run Evaluation Against a Custom JSON Dataset (US-10)

This will be used to get the ressults for the HotPotQA testing model. The results will vary, since the HotPot2 model only has 1000 docs. If time permits, it is possible to run theb json trainer, but it would take over 20 to 40 hours as it takes about 8 hours to finish.
Questions will take time; therefore, we have limited the amount of questions to 10. If there is more time for testing, then you can run more questions.