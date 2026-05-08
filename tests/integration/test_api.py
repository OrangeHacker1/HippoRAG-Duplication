import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from api.app import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.integration
class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}


@pytest.mark.integration
class TestQueryEndpoint:
    def test_empty_query_returns_422(self, client):
        res = client.post("/api/query", json={"question": ""})
        assert res.status_code == 422
        assert "Query must not be empty." in res.json()["detail"]

    def test_whitespace_query_returns_422(self, client):
        res = client.post("/api/query", json={"question": "   "})
        assert res.status_code == 422
        assert "Query must not be empty." in res.json()["detail"]

    def test_valid_query_returns_answer(self, client):
        mock_rag = MagicMock()
        mock_rag.retrieve.return_value = ["Einstein developed relativity."]
        mock_rag.llm.generate.return_value = "Albert Einstein."

        with patch("api.app.rag", mock_rag):
            res = client.post("/api/query", json={"question": "Who developed relativity?"})

        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert "passages" in data
        assert "request_id" in data
        assert len(data["passages"]) > 0

    def test_llm_timeout_returns_503(self, client):
        import requests as req
        mock_rag = MagicMock()
        mock_rag.retrieve.side_effect = req.exceptions.ConnectTimeout()

        with patch("api.app.rag", mock_rag):
            res = client.post("/api/query", json={"question": "Who developed relativity?"})

        assert res.status_code == 503
        assert "unavailable" in res.json()["detail"].lower()


@pytest.mark.integration
class TestIndexPage:
    def test_index_returns_html(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]

    def test_evaluate_page_returns_html(self, client):
        res = client.get("/evaluate")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
