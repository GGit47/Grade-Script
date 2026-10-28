import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database.session import Base

class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    class_or_batch = Column(String(100), nullable=False)
    total_max_marks = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan", order_by="Question.question_number")
    submissions = relationship("Submission", back_populates="exam", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    question_number = Column(Integer, nullable=False)
    question_label = Column(String(50), default="")  # e.g. "Q1", "1(a)", "2"
    question_text = Column(Text, nullable=False)
    reference_answer = Column(Text, nullable=False)
    max_marks = Column(Float, nullable=False)
    essential_keywords = Column(Text, nullable=True)  # Comma-separated or JSON string
    rubric_criteria = Column(Text, nullable=True)      # JSON list of [{"criterion": str, "marks": float}]
    partial_credit_rules = Column(Text, nullable=True) # Description or rules
    alternative_answers = Column(Text, nullable=True)  # JSON list of alternative acceptable answers
    negative_marking = Column(Float, default=0.0)      # Optional negative marking penalty

    exam = relationship("Exam", back_populates="questions")
    evaluations = relationship("EvaluationItem", back_populates="question", cascade="all, delete-orphan")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    student_roll_no = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, jpg, png
    status = Column(String(50), default="uploaded")  # uploaded, processed, evaluated, approved
    
    # Aggregated marks
    suggested_total = Column(Float, default=0.0)
    approved_total = Column(Float, default=0.0)
    is_approved = Column(Boolean, default=False)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    exam = relationship("Exam", back_populates="submissions")
    pages = relationship("SubmissionPage", back_populates="submission", cascade="all, delete-orphan", order_by="SubmissionPage.page_number")
    evaluations = relationship("EvaluationItem", back_populates="submission", cascade="all, delete-orphan")


class SubmissionPage(Base):
    __tablename__ = "submission_pages"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    image_path = Column(String(500), nullable=False)
    preprocessed_path = Column(String(500), nullable=True)

    submission = relationship("Submission", back_populates="pages")
    regions = relationship("AnswerRegion", back_populates="page", cascade="all, delete-orphan")


class AnswerRegion(Base):
    __tablename__ = "answer_regions"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("submission_pages.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=True)
    crop_path = Column(String(500), nullable=False)
    
    # Bounding box coordinates: [ymin, xmin, ymax, xmax] relative or absolute
    bbox = Column(String(100), nullable=True)
    recognized_text = Column(Text, default="")
    edited_text = Column(Text, default="")
    confidence = Column(Float, default=0.0)

    # Intelligent Answer-to-Question Mapping attributes
    detected_question_label = Column(String(50), nullable=True)  # e.g., "Q3", "1(a)"
    mapping_confidence = Column(Float, default=0.0)
    mapping_method = Column(String(50), default="unmatched")     # explicit_label, semantic, answer_content, manual, unmatched
    candidate_matches = Column(Text, default="[]")               # JSON list of candidates with scores
    is_ambiguous = Column(Boolean, default=False)
    is_manually_mapped = Column(Boolean, default=False)

    page = relationship("SubmissionPage", back_populates="regions")
    question = relationship("Question")
    evaluation = relationship("EvaluationItem", back_populates="region", uselist=False)


class EvaluationItem(Base):
    __tablename__ = "evaluation_items"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    region_id = Column(Integer, ForeignKey("answer_regions.id"), nullable=True)

    transcribed_answer = Column(Text, default="")
    concepts_identified = Column(Text, default="")  # JSON or comma-separated
    missing_concepts = Column(Text, default="")      # JSON or comma-separated
    semantic_similarity = Column(Float, default=0.0)
    
    suggested_marks = Column(Float, default=0.0)
    approved_marks = Column(Float, default=0.0)
    max_marks = Column(Float, nullable=False)
    
    rationale = Column(Text, default="")
    review_needed = Column(Boolean, default=False)
    is_teacher_approved = Column(Boolean, default=False)
    teacher_notes = Column(Text, nullable=True)
    rubric_scores = Column(Text, default="[]")       # JSON list of evaluated rubric criteria

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    submission = relationship("Submission", back_populates="evaluations")
    question = relationship("Question", back_populates="evaluations")
    region = relationship("AnswerRegion", back_populates="evaluation")
