import json
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_parse_text_answer_key_api():
    payload = {
        "raw_text": """
        Q1. What is an Operating System?
        Answer: System software that manages computer hardware.
        [Max Marks: 5]
        Keywords: system software, hardware, management
        Rubric: 2.5 marks for definition; 2.5 marks for hardware management

        Q2. What is process scheduling?
        Answer: Process scheduling is the activity of the process manager that handles the removal of the running process from the CPU.
        [Max Marks: 5]
        """
    }
    response = client.post("/api/answer-keys/parse-text", data=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["questions"]) == 2
    assert data["questions"][0]["question_label"] == "Q1"
    assert data["questions"][1]["question_label"] == "Q2"


def test_create_exam_with_rubrics_and_validation():
    exam_payload = {
        "title": "Machine Learning Midterm",
        "subject": "CS401",
        "class_or_batch": "3rd Year AI-ML",
        "questions": [
            {
                "question_number": 1,
                "question_label": "Q1",
                "question_text": "Define supervised learning.",
                "reference_answer": "Learning from labelled training datasets.",
                "max_marks": 5.0,
                "essential_keywords": "supervised, labelled",
                "rubric_criteria": json.dumps([
                    {"criterion": "Definition of supervised learning", "marks": 2.5},
                    {"criterion": "Mentioning labelled data", "marks": 2.5}
                ]),
                "alternative_answers": json.dumps(["Model training with ground truth labels"])
            },
            {
                "question_number": 2,
                "question_label": "Q2",
                "question_text": "Explain overfitting.",
                "reference_answer": "Model memorizes training noise and fails to generalize.",
                "max_marks": 5.0,
                "essential_keywords": "overfitting, noise, generalization",
                "rubric_criteria": json.dumps([
                    {"criterion": "Definition", "marks": 2.5},
                    {"criterion": "Generalization failure", "marks": 2.5}
                ])
            }
        ]
    }
    res = client.post("/api/exams", json=exam_payload)
    assert res.status_code == 200
    created = res.json()
    assert created["total_max_marks"] == 10.0
    assert len(created["questions"]) == 2


def test_create_exam_rejects_duplicate_labels():
    invalid_payload = {
        "title": "Invalid Exam",
        "subject": "CS401",
        "class_or_batch": "3rd Year",
        "questions": [
            {
                "question_number": 1,
                "question_label": "Q1",
                "question_text": "First Question",
                "reference_answer": "First Answer",
                "max_marks": 5.0
            },
            {
                "question_number": 2,
                "question_label": "Q1", # Duplicate identifier!
                "question_text": "Second Question",
                "reference_answer": "Second Answer",
                "max_marks": 5.0
            }
        ]
    }
    res = client.post("/api/exams", json=invalid_payload)
    assert res.status_code == 400
    assert "Duplicate question identifier" in res.json()["detail"]


def test_dashboard_endpoint():
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "total_exams" in data
    assert "total_submissions" in data
    assert data["total_exams"] >= 1


def test_parse_csv_answer_key_via_api():
    """Verify that the /api/answer-keys/parse-text endpoint correctly parses a CSV format."""
    csv_payload = {
        "raw_text": """Question_Number,Type,Correct_Answer
1,MCQ,B
2,MCQ,C
3,Short_Answer,"A type of ML where the model is trained on labeled data."
"""
    }
    response = client.post("/api/answer-keys/parse-text", data=csv_payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["questions"]) == 3

    assert data["questions"][0]["question_label"] == "Q1"
    assert data["questions"][0]["question_type"] == "mcq"
    assert data["questions"][0]["reference_answer"] == "B"
    assert data["questions"][0]["max_marks"] == 1.0

    assert data["questions"][1]["question_type"] == "mcq"
    assert data["questions"][1]["reference_answer"] == "C"

    assert data["questions"][2]["question_label"] == "Q3"
    assert data["questions"][2]["question_type"] == "subjective"
    assert "labeled data" in data["questions"][2]["reference_answer"]


def test_create_exam_with_mcq_question_type():
    """Test creating an exam with mixed MCQ and Subjective questions, including question_type."""
    payload = {
        "title": "ML Final Exam",
        "subject": "CS401",
        "class_or_batch": "3rd Year AI",
        "questions": [
            {
                "question_number": 1,
                "question_label": "Q1",
                "question_type": "mcq",
                "question_text": "[Question text unavailable]",
                "reference_answer": "B",
                "max_marks": 1.0
            },
            {
                "question_number": 2,
                "question_label": "Q2",
                "question_type": "subjective",
                "question_text": "Explain overfitting.",
                "reference_answer": "Overfitting occurs when the model memorizes training data and fails to generalize.",
                "max_marks": 2.0,
                "essential_keywords": "overfitting, training data, generalize",
                "rubric_criteria": json.dumps([
                    {"criterion": "Definition", "marks": 1.0},
                    {"criterion": "Consequence (poor generalization)", "marks": 1.0}
                ])
            }
        ]
    }
    res = client.post("/api/exams", json=payload)
    assert res.status_code == 200
    created = res.json()
    assert created["total_max_marks"] == 3.0
    assert len(created["questions"]) == 2
    mcq_q = next(q for q in created["questions"] if q["question_number"] == 1)
    assert mcq_q["question_type"] == "mcq"
    sub_q = next(q for q in created["questions"] if q["question_number"] == 2)
    assert sub_q["question_type"] == "subjective"


def test_parse_text_rejects_invalid_input():
    """Verify that malformed answer key input returns HTTP 400 with an error detail."""
    payload = {"raw_text": "   \n   "}
    response = client.post("/api/answer-keys/parse-text", data=payload)
    assert response.status_code == 400
    assert "detail" in response.json()
