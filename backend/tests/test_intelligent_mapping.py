import pytest
from app.models.entities import Question
from app.services.mapping.answer_mapper import AnswerMapper
from app.services.grading.engine import grading_engine

# Ensure embedder is loaded for semantic mapping tests
grading_engine.load_embedder()

def test_extract_detected_identifier():
    label, num, sub, body = AnswerMapper.extract_detected_identifier("Q3. Gradient descent is an iterative algorithm...")
    assert label == "Q3"
    assert num == 3
    assert sub is None
    assert "Gradient descent is an iterative" in body

    label2, num2, sub2, body2 = AnswerMapper.extract_detected_identifier("1(a) Supervised learning involves training models on labelled datasets.")
    assert label2 == "Q1(a)"
    assert num2 == 1
    assert sub2 == "a"
    assert "Supervised learning involves" in body2

    label3, num3, sub3, body3 = AnswerMapper.extract_detected_identifier("Ans 2: Overfitting happens when models learn noise.")
    assert label3 == "Q2"
    assert num3 == 2
    assert "Overfitting happens" in body3


def test_reordered_student_answers_mapping():
    """
    Test C: Reference answer key has Q1, Q2, Q3.
    Student writes answers in order: Q3, Q1, Q2.
    The mapper must correctly map:
    - First region -> Q3
    - Second region -> Q1
    - Third region -> Q2
    """
    q1 = Question(
        id=101,
        question_number=1,
        question_label="Q1",
        question_text="What is supervised learning?",
        reference_answer="Supervised learning is an approach where a model learns from labelled training data.",
        max_marks=5.0,
        essential_keywords="supervised, labelled, training data"
    )
    q2 = Question(
        id=102,
        question_number=2,
        question_label="Q2",
        question_text="Explain overfitting.",
        reference_answer="Overfitting occurs when a machine learning model fits training noise and generalizes poorly to unseen data.",
        max_marks=5.0,
        essential_keywords="overfitting, training noise, generalization"
    )
    q3 = Question(
        id=103,
        question_number=3,
        question_label="Q3",
        question_text="Explain gradient descent.",
        reference_answer="Gradient descent is an optimization algorithm that iteratively minimizes a loss function by updating parameters.",
        max_marks=5.0,
        essential_keywords="gradient descent, optimization, loss function"
    )
    questions = [q1, q2, q3]

    # Student submission answered out of order: Q3 first, then Q1, then Q2
    student_regions = [
        {
            "id": 1,
            "text": "Q3: Gradient descent is an optimization technique used to minimize model loss.",
            "crop_path": "uploads/crops/crop_1.jpg",
            "page_number": 1
        },
        {
            "id": 2,
            "text": "Q1. Supervised learning uses labelled data pairs to train predictive algorithms.",
            "crop_path": "uploads/crops/crop_2.jpg",
            "page_number": 1
        },
        {
            "id": 3,
            "text": "Q2 - Overfitting occurs when the model memorizes noise and fails on unseen testing data.",
            "crop_path": "uploads/crops/crop_3.jpg",
            "page_number": 2
        }
    ]

    results = AnswerMapper.match_regions_to_questions(student_regions, questions)
    assert len(results) == 3

    # First student answer (Q3) maps to question 103 (Q3)
    assert results[0]["assigned_question_id"] == 103
    assert results[0]["detected_label"] == "Q3"
    assert results[0]["mapping_confidence"] >= 0.85

    # Second student answer (Q1) maps to question 101 (Q1)
    assert results[1]["assigned_question_id"] == 101
    assert results[1]["detected_label"] == "Q1"
    assert results[1]["mapping_confidence"] >= 0.85

    # Third student answer (Q2) maps to question 102 (Q2)
    assert results[2]["assigned_question_id"] == 102
    assert results[2]["detected_label"] == "Q2"
    assert results[2]["mapping_confidence"] >= 0.85


def test_missing_question_identifier_semantic_mapping():
    """
    Test D: Student answer without explicit question identifier.
    Mapper matches based on content semantic compatibility.
    """
    q1 = Question(
        id=201,
        question_number=1,
        question_label="Q1",
        question_text="What is supervised learning?",
        reference_answer="Supervised learning is learning with labelled training datasets.",
        max_marks=5.0,
        essential_keywords="supervised, labelled"
    )
    q2 = Question(
        id=202,
        question_number=2,
        question_label="Q2",
        question_text="What is gradient descent?",
        reference_answer="Gradient descent minimizes the objective loss function iteratively.",
        max_marks=5.0,
        essential_keywords="gradient descent, loss function"
    )

    regions = [
        {
            "id": 10,
            "text": "This technique iteratively minimizes loss using calculated gradients.",
            "crop_path": "uploads/crops/crop_10.jpg",
            "page_number": 1
        }
    ]

    results = AnswerMapper.match_regions_to_questions(regions, [q1, q2])
    assert len(results) == 1
    # Should be mapped to Q2 (Gradient descent) based on semantics
    assert results[0]["assigned_question_id"] == 202
    assert results[0]["mapping_method"] in ["semantic", "explicit_label"]


def test_duplicate_and_ambiguity_detection():
    """
    Test E: Ambiguity and duplicate answers detection.
    """
    q1 = Question(
        id=301,
        question_number=1,
        question_label="Q1",
        question_text="What is supervised learning?",
        reference_answer="Supervised learning uses labelled data.",
        max_marks=5.0,
        essential_keywords="supervised, labelled"
    )

    # Student writes two answers claiming Q1
    regions = [
        {"id": 21, "text": "Q1. Supervised learning uses labelled training pairs.", "crop_path": "", "page_number": 1},
        {"id": 22, "text": "Q1. In supervised learning, models map inputs to targets.", "crop_path": "", "page_number": 2}
    ]

    results = AnswerMapper.match_regions_to_questions(regions, [q1])
    # Both claim Q1 -> duplicate ambiguity detected!
    assert any(r["is_ambiguous"] or r["mapping_method"] == "duplicate_detected" for r in results)
