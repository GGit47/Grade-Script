import os
import pytest
from app.services.answer_key.parser import AnswerKeyParser

def test_parse_raw_text_standard():
    sample_text = """
    Q1. What is supervised learning?
    Answer: Supervised learning is a machine learning approach in which a model learns from labelled training data.
    [Max Marks: 5]
    Keywords: supervised, labelled data, training data
    Rubric: 2.5 marks for definition; 2.5 marks for labelled data mention

    Q2. Explain overfitting.
    Answer: Overfitting occurs when a model learns training-specific patterns, including noise, and generalizes poorly to unseen data.
    [Max Marks: 5]
    Keywords: training data, noise, generalization, unseen data
    Rubric: 2 marks definition; 2 marks fitting noise; 1 mark poor generalization

    Q3. Explain gradient descent.
    Answer: Gradient descent is an optimization algorithm used to minimize the loss function by iteratively updating model parameters.
    [Max Marks: 4]
    Keywords: optimization, loss function, parameters, gradient
    """
    res = AnswerKeyParser.parse_raw_text(sample_text)
    assert len(res.questions) == 3
    
    q1 = res.questions[0]
    assert q1.question_number == 1
    assert q1.question_label == "Q1"
    assert "supervised learning" in q1.question_text.lower()
    assert "labelled training data" in q1.reference_answer.lower()
    assert q1.max_marks == 5.0
    assert "labelled data" in q1.essential_keywords
    assert len(q1.rubric_criteria) >= 2

    q2 = res.questions[1]
    assert q2.question_number == 2
    assert q2.question_label == "Q2"
    assert "overfitting" in q2.question_text.lower()
    assert q2.max_marks == 5.0
    assert len(q2.rubric_criteria) >= 2

    q3 = res.questions[2]
    assert q3.question_number == 3
    assert q3.question_label == "Q3"
    assert q3.max_marks == 4.0


def test_format_a_variations_and_internal_question_word():
    """
    Tests various prefixes: Q1:, Question 2:, 3.
    Tests answers containing the word 'Question' without falsely breaking.
    Tests Answer:, Reference Answer:, Correct Answer:
    """
    sample_text = """
    Q1: Define Operating System and list two of its primary functions.
    Answer: An operating system is system software that manages computer hardware and software resources. Note: This question covers fundamental concepts.
    [Max Marks: 5]
    Keywords: system software, hardware, resource management
    Rubric: 2 marks for clear definition; 3 marks for mentioning at least two primary functions accurately.

    Question 2: What is the difference between synchronous and asynchronous transmission?
    Reference Answer: In synchronous transmission, data is transmitted in blocks or frames synchronized by a clock signal. In asynchronous transmission, data is transmitted independently with start and stop bits.
    [Max Marks: 5]
    Keywords: clock synchronization, blocks, start bits, stop bits
    Rubric: Award marks for accurately explaining both transmission methods.

    3. Explain the kernel architecture.
    Correct Answer: The kernel is the core component that manages system resources and hardware communication.
    """
    res = AnswerKeyParser.parse_raw_text(sample_text)
    assert len(res.questions) == 3
    
    assert res.questions[0].question_number == 1
    assert res.questions[0].question_label == "Q1"
    assert "operating system" in res.questions[0].reference_answer.lower()
    # Ensure 'question' inside the answer body did not truncate or break the answer
    assert "fundamental concepts" in res.questions[0].reference_answer.lower()
    assert res.questions[0].max_marks == 5.0

    assert res.questions[1].question_number == 2
    assert res.questions[1].question_label == "Q2"
    assert "synchronous transmission" in res.questions[1].reference_answer.lower()
    assert res.questions[1].max_marks == 5.0

    assert res.questions[2].question_number == 3
    assert res.questions[2].question_label == "Q3"
    assert "kernel is the core" in res.questions[2].reference_answer.lower()
    assert res.questions[2].max_marks == 5.0  # default when omitted


def test_parse_csv_answer_key_fixture():
    """
    Tests parsing the real answerkey.txt fixture containing 35 rows:
    - 20 MCQs (questions 1-20)
    - 15 Subjective questions (questions 21-35)
    - Quoted answers with internal commas, semicolons, and punctuation
    - Preserves question number, question type, and reference answers
    """
    fixture_path = os.path.join(os.path.dirname(__file__), "answerkey.txt")
    with open(fixture_path, "r", encoding="utf-8") as f:
        content = f.read()

    res = AnswerKeyParser.parse_raw_text(content)
    assert len(res.questions) == 35

    # Check MCQs 1 to 20
    for i in range(20):
        q = res.questions[i]
        assert q.question_number == i + 1
        assert q.question_type == "mcq"
        assert len(q.reference_answer.strip()) == 1
        assert q.reference_answer.strip() in ["A", "B", "C", "D"]
        assert q.max_marks == 1.0

    # Verify specific MCQ answers from fixture
    assert res.questions[0].reference_answer == "B"
    assert res.questions[1].reference_answer == "C"
    assert res.questions[2].reference_answer == "A"
    assert res.questions[19].reference_answer == "B"

    # Check Subjective questions 21 to 35
    for i in range(20, 35):
        q = res.questions[i]
        assert q.question_number == i + 1
        assert q.question_type == "subjective"
        assert len(q.reference_answer.strip()) > 5
        assert q.max_marks == 2.0
        assert "unavailable" in q.question_text.lower()

    # Verify Q21, Q22, Q26 retain commas and semicolons inside quotes intact
    q21 = res.questions[20]
    assert q21.reference_answer == "A type of ML where the model is trained on labeled data with known inputs and outputs."

    q22 = res.questions[21]
    assert q22.reference_answer == "Overfitting; the model has memorized the training data but failed to generalize."

    q26 = res.questions[25]
    assert "Structured is organized in rows/columns (SQL, Excel); Semi-structured has some markers but isn't in a grid (JSON, XML, HTML)." in q26.reference_answer


def test_duplicate_question_number_detection():
    csv_duplicate = """Question_Number,Type,Correct_Answer
1,MCQ,A
1,MCQ,B
"""
    with pytest.raises(ValueError, match="Duplicate question number 1 detected"):
        AnswerKeyParser.parse_raw_text(csv_duplicate)

    text_duplicate = """
    Q1. First question
    Answer: First answer

    Q1. Duplicate question
    Answer: Duplicate answer
    """
    with pytest.raises(ValueError, match="Duplicate question number 1 detected"):
        AnswerKeyParser.parse_raw_text(text_duplicate)


def test_missing_reference_answer_validation():
    text_missing = """
    Q1. What is an operating system?
    [Max Marks: 5]
    """
    with pytest.raises(ValueError, match="missing or empty reference answer"):
        AnswerKeyParser.parse_raw_text(text_missing)

    csv_missing = """Question_Number,Type,Correct_Answer
1,MCQ,
"""
    with pytest.raises(ValueError, match="missing or empty reference answer"):
        AnswerKeyParser.parse_raw_text(csv_missing)


def test_malformed_csv_rows():
    csv_malformed = """Question_Number,Type,Correct_Answer
invalid_row_without_enough_columns
"""
    with pytest.raises(ValueError, match="Invalid question number"):
        AnswerKeyParser.parse_raw_text(csv_malformed)


def test_empty_input_validation():
    with pytest.raises(ValueError, match="Provided answer key text is empty"):
        AnswerKeyParser.parse_raw_text("")

    with pytest.raises(ValueError, match="Provided answer key text is empty"):
        AnswerKeyParser.parse_raw_text("   \n   \t  ")
