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


def test_standalone_number_identifier_extraction():
    label, num, sub, body = AnswerMapper.extract_detected_identifier("21\nA type of ML where the model is trained on labeled data.")
    assert label == "Q21"
    assert num == 21
    assert "A type of ML" in body

    label2, num2, sub2, body2 = AnswerMapper.extract_detected_identifier("22.\nOverfitting is when a model memorizes data.")
    assert label2 == "Q22"
    assert num2 == 22
    assert "Overfitting is when" in body2


def test_real_exam_out_of_order_student_answers():
    """
    Simulates Student_2 answering questions 21, 22, 25, 28, 33 out of numerical order.
    Verifies that each answer is mapped to its matching reference question.
    """
    ref_dict = {
        21: ("A type of ML where the model is trained on labeled data with known inputs and outputs.", "labeled data, inputs, outputs"),
        22: ("Overfitting; the model has memorized the training data but failed to generalize.", "overfitting, memorized, generalize"),
        23: ("A statistical process for estimating the relationships between variables.", "statistical process, relationships"),
        24: ("Data quality/missing values, overfitting/underfitting, data collection.", "data quality, missing values"),
        25: ("Healthcare/disease prediction, Finance/fraud detection, E-commerce.", "healthcare, finance, fraud detection"),
        26: ("Structured is organized in rows/columns; Semi-structured has some markers.", "structured, rows, columns"),
        27: ("Detection: Z-score, IQR. Handling: Trimming, Capping, Imputation.", "z-score, iqr, trimming, imputation"),
        28: ("The steps taken to clean and transform raw data into a format suitable for ML.", "clean, transform raw data, format"),
        29: ("K-NN is distance-based; features with larger scales will dominate.", "k-nn, distance-based, scales"),
        30: ("By grouping values into bins or intervals.", "grouping, bins, intervals"),
        31: ("The predefined number of clusters.", "clusters, groups"),
        32: ("K in K-NN, Learning Rate, Number of Estimators.", "k-nn, learning rate"),
        33: ("An optimization algorithm used to minimize the cost function.", "optimization, minimize, cost function"),
        34: ("Discussion on maximizing the margin.", "maximizing, margin"),
        35: ("It transforms data into a higher-dimensional space.", "higher-dimensional space, non-linear")
    }

    questions = [
        Question(
            id=1000 + qnum,
            question_number=qnum,
            question_label=f"Q{qnum}",
            question_type="subjective",
            question_text="[Question text unavailable]",
            reference_answer=ref[0],
            max_marks=2.0,
            essential_keywords=ref[1]
        )
        for qnum, ref in ref_dict.items()
    ]

    # Student written answers out of numerical order: 22, 21, 25, 33, 28
    student_regions = [
        {
            "id": 1,
            "text": "22\nOverfitting: when model fits training data too well and performs poorly on new test data.",
            "crop_path": "uploads/crops/crop_1.jpg",
            "page_number": 2
        },
        {
            "id": 2,
            "text": "21\nSupervised ML where algorithm trains using labeled input-output examples.",
            "crop_path": "uploads/crops/crop_2.jpg",
            "page_number": 2
        },
        {
            "id": 3,
            "text": "25\n1. Disease diagnosis in Healthcare. 2. Fraud detection in Banking and Finance.",
            "crop_path": "uploads/crops/crop_3.jpg",
            "page_number": 3
        },
        {
            "id": 4,
            "text": "33\nGradient descent optimization algorithm minimizing cost function iteratively.",
            "crop_path": "uploads/crops/crop_4.jpg",
            "page_number": 3
        },
        {
            "id": 5,
            "text": "28\nData preprocessing: cleaning, transforming, and standardizing raw dataset.",
            "crop_path": "uploads/crops/crop_5.jpg",
            "page_number": 3
        }
    ]

    mappings = AnswerMapper.match_regions_to_questions(student_regions, questions)
    assert len(mappings) == 5

    # Check that region 1 mapped to Q22
    assert mappings[0]["assigned_question_id"] == 1022
    assert mappings[0]["detected_label"] == "Q22"

    # Region 2 mapped to Q21
    assert mappings[1]["assigned_question_id"] == 1021
    assert mappings[1]["detected_label"] == "Q21"

    # Region 3 mapped to Q25
    assert mappings[2]["assigned_question_id"] == 1025
    assert mappings[2]["detected_label"] == "Q25"

    # Region 4 mapped to Q33
    assert mappings[3]["assigned_question_id"] == 1033
    assert mappings[3]["detected_label"] == "Q33"

    # Region 5 mapped to Q28
    assert mappings[4]["assigned_question_id"] == 1028
    assert mappings[4]["detected_label"] == "Q28"
