"""Benchmark scoring separation tests."""

from __future__ import annotations

from continuum.eval.benchmark.scoring import score_answer, score_document_recall, score_rows


def test_official_answer_scoring():
    assert score_answer("The default limits are 10 MiB per file", "The default limits are 10 MiB per file")
    assert score_answer("unknown - abstain", "not found in the documents")


def test_document_recall():
    assert score_document_recall(["dsid_a", "dsid_b"], ["dsid_a"]) == 1.0
    assert score_document_recall(["dsid_x"], ["dsid_a"]) == 0.0


def test_score_rows_shape():
    questions = {
        "q1": {
            "gold_answer": "alpha",
            "expected_doc_ids": ["dsid_a"],
        }
    }
    rows = [
        {
            "question_id": "q1",
            "answer": "alpha",
            "retrieved_artifacts": ["dsid_a", "dsid_b"],
        }
    ]
    scores = score_rows(rows, questions)
    assert scores["answer_correctness"] == 1.0
    assert scores["document_recall_mean"] == 1.0
    assert scores["invalid_extra_evidence_mean"] == 1.0
