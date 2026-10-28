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


def test_parse_subquestions_and_numbering():
    sample_text = """
    1(a). Define an Operating System.
    Ans: An operating system is software that manages computer hardware and system resources.
    [5 Marks]

    1(b). State two primary functions of an OS.
    Ans: Memory management and process scheduling.
    [5 Marks]
    """
    res = AnswerKeyParser.parse_raw_text(sample_text)
    assert len(res.questions) == 2
    assert res.questions[0].question_label == "Q1(a)"
    assert res.questions[1].question_label == "Q1(b)"
    assert "hardware" in res.questions[0].reference_answer


def test_unparsed_text_preservation():
    sample_text = """
    NOTE: All questions are compulsory. Total time: 3 hours.
    
    Q1. What is regression?
    Answer: A predictive modeling technique.
    [Max Marks: 5]
    """
    res = AnswerKeyParser.parse_raw_text(sample_text)
    assert len(res.questions) == 1
    assert "NOTE: All questions are compulsory" in res.unparsed_text
