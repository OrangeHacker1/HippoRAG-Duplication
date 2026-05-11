import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from myproject.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_rag():
    m = MagicMock()
    m.retrieve.return_value = [
        "Albert Einstein developed the theory of relativity.",
        "The theory of relativity revolutionized modern physics.",
    ]
    m.llm.generate.return_value = "Albert Einstein influenced physics through relativity."
    return m


@pytest.mark.user_story("US-01")
def test_us01_submit_query_returns_answer(client, mock_rag):
    """
    Given the system is running and the KG is loaded,
    When the user submits a non-empty question,
    Then the response contains a non-empty answer string.
    """
    with patch("myproject.api.app.rag", mock_rag):
        res = client.post("/api/query", json={"question": "Who influenced physics through relativity?"})

    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0


@pytest.mark.user_story("US-02")
def test_us02_retrieved_passages_visible(client, mock_rag):
    """
    Given the user has submitted a question,
    When the answer is displayed,
    Then retrieved passages are returned as a non-empty list.
    """
    with patch("myproject.api.app.rag", mock_rag):
        res = client.post("/api/query", json={"question": "Who influenced physics through relativity?"})

    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["passages"], list)
    assert len(data["passages"]) >= 1
    assert all(isinstance(p, str) and len(p) > 0 for p in data["passages"])


@pytest.mark.user_story("US-03")
def test_us03_health_check(client):
    """
    Given the system is running,
    When GET /health is called,
    Then the response is HTTP 200 with {"status": "ok"}.
    """
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


@pytest.mark.user_story("US-04")
def test_us04_evaluate_returns_metrics(client, mock_rag):
    """
    Given the KG is loaded,
    When POST /api/evaluate is called,
    Then the response contains Recall@k, ExactMatch, and F1 scores.
    """
    with patch("myproject.api.app.rag", mock_rag):
        res = client.post("/api/evaluate")

    assert res.status_code == 200
    data = res.json()
    agg = data["aggregate"]
    assert "Recall@1" in agg
    assert "Recall@2" in agg
    assert "Recall@5" in agg
    assert "ExactMatch" in agg
    assert "F1" in agg
    assert all(0.0 <= v <= 1.0 for v in agg.values())


@pytest.mark.user_story("US-05")
def test_us05_empty_query_returns_error(client):
    """
    Given the system is running,
    When the user submits an empty query,
    Then the response is HTTP 422 with message "Query must not be empty."
    """
    res = client.post("/api/query", json={"question": ""})
    assert res.status_code == 422
    assert "Query must not be empty." in res.json()["detail"]


@pytest.mark.user_story("US-06")
def test_us06_llm_unavailable_returns_503(client):
    """
    Given the LLM endpoint is unreachable,
    When the user submits a valid question,
    Then the response is HTTP 503 with a friendly error message.
    """
    import requests as req
    mock_rag = MagicMock()
    mock_rag.retrieve.side_effect = req.exceptions.ConnectTimeout()

    with patch("myproject.api.app.rag", mock_rag):
        res = client.post("/api/query", json={"question": "Who developed relativity?"})

    assert res.status_code == 503
    assert "unavailable" in res.json()["detail"].lower()
