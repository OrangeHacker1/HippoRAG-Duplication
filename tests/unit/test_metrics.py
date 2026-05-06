import pytest
from eval.metrics import recall_at_k, exact_match, f1_score


@pytest.mark.unit
class TestRecallAtK:
    def test_perfect_recall(self):
        assert recall_at_k(["a", "b", "c"], ["a", "b"], k=2) == 1.0

    def test_zero_recall(self):
        assert recall_at_k(["x", "y"], ["a", "b"], k=2) == 0.0

    def test_partial_recall(self):
        assert recall_at_k(["a", "x"], ["a", "b"], k=2) == 0.5

    def test_k_larger_than_retrieved(self):
        assert recall_at_k(["a"], ["a", "b"], k=5) == 0.5

    def test_empty_gold(self):
        assert recall_at_k(["a", "b"], [], k=2) == 0.0

    def test_empty_retrieved(self):
        assert recall_at_k([], ["a"], k=5) == 0.0


@pytest.mark.unit
class TestExactMatch:
    def test_match(self):
        assert exact_match("The answer is Poland", ["Poland"]) == 1.0

    def test_no_match(self):
        assert exact_match("The answer is France", ["Poland"]) == 0.0

    def test_case_insensitive(self):
        assert exact_match("POLAND is the answer", ["poland"]) == 1.0

    def test_multiple_gold_answers(self):
        assert exact_match("Rockland County", ["Rockland County", "Rockland"]) == 1.0


@pytest.mark.unit
class TestF1Score:
    def test_perfect_f1(self):
        assert f1_score("Poland", ["Poland"]) == 1.0

    def test_zero_f1(self):
        assert f1_score("France Germany", ["Poland Russia"]) == 0.0

    def test_partial_f1(self):
        score = f1_score("Rockland County New York", ["Rockland County"])
        assert 0.0 < score <= 1.0

    def test_empty_prediction(self):
        assert f1_score("", ["Poland"]) == 0.0
