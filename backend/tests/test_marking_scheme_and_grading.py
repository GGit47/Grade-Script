import json
import pytest
from app.services.grading.engine import grading_engine

# Ensure embedder is loaded for neural similarity
grading_engine.load_embedder()

def test_rubric_based_evaluation():
    rubric = [
        {"criterion": "Accurate definition of overfitting", "marks": 2.0},
        {"criterion": "Mentioning fitting noise or memorizing training data", "marks": 2.0},
        {"criterion": "Consequence of poor generalization to unseen test data", "marks": 1.0}
    ]

    student_answer = "Overfitting happens when a model memorizes the training data and noise instead of learning patterns, resulting in poor generalization on unseen data."
    ref_answer = "Overfitting occurs when a model learns training noise and generalizes poorly to unseen data."

    res = grading_engine.evaluate_answer(
        student_text=student_answer,
        reference_text=ref_answer,
        max_marks=5.0,
        essential_keywords_str="overfitting, training data, noise, generalization",
        rubric_criteria=json.dumps(rubric)
    )

    assert res["suggested_marks"] >= 4.0
    assert len(res["rubric_scores"]) == 3
    # Check that individual criteria were evaluated
    for score_item in res["rubric_scores"]:
        assert "criterion" in score_item
        assert "awarded_marks" in score_item
        assert score_item["awarded_marks"] <= score_item["max_marks"]


def test_alternative_answers_matching():
    student_ans = "A system program that acts as an intermediary between users and computer hardware."
    primary_ref = "An operating system manages computer hardware and system resources."
    alt_answers = ["An intermediary software between user and hardware components; resource controller"]

    res = grading_engine.evaluate_answer(
        student_text=student_ans,
        reference_text=primary_ref,
        max_marks=5.0,
        essential_keywords_str="hardware, system, user",
        alternative_answers_str=json.dumps(alt_answers)
    )

    # Should match well due to alternative answer alignment
    assert res["suggested_marks"] >= 3.5
    assert res["semantic_similarity"] > 0.60


def test_empty_answer_handling():
    res = grading_engine.evaluate_answer(
        student_text="[Blank or empty answer region]",
        reference_text="Supervised learning uses labelled data.",
        max_marks=5.0,
        essential_keywords_str="supervised, labelled"
    )
    assert res["suggested_marks"] == 0.0
    assert res["review_needed"] is True
    assert "supervised" in res["missing_concepts"]


def test_negative_marking():
    res = grading_engine.evaluate_answer(
        student_text="Photosynthesis produces chlorophyll in plant cells.",
        reference_text="Gradient descent optimizes weights in deep neural networks.",
        max_marks=5.0,
        essential_keywords_str="gradient descent, optimization",
        negative_marking=1.0
    )
    # Completely irrelevant answer should receive 0 marks
    assert res["suggested_marks"] == 0.0


def test_mcq_evaluation_correct():
    res = grading_engine.evaluate_answer(
        student_text="Option B",
        reference_text="B",
        max_marks=1.0,
        question_type="mcq"
    )
    assert res["suggested_marks"] == 1.0
    assert res["review_needed"] is False
    assert "matches reference 'B'" in res["feedback"]


def test_mcq_evaluation_incorrect():
    res = grading_engine.evaluate_answer(
        student_text="C",
        reference_text="B",
        max_marks=1.0,
        negative_marking=0.25,
        question_type="mcq"
    )
    assert res["suggested_marks"] == -0.25
    assert "does not match reference 'B'" in res["feedback"]


def test_mcq_evaluation_missing_or_unclear():
    res = grading_engine.evaluate_answer(
        student_text="[Blank or empty answer region]",
        reference_text="B",
        max_marks=1.0,
        question_type="mcq"
    )
    assert res["suggested_marks"] == 0.0
    assert res["review_needed"] is True
