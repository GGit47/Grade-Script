from pydantic import BaseModel, Field
from typing import List, Optional
import datetime

# --- Question Schemas ---
class QuestionCreate(BaseModel):
    question_number: int
    question_text: str
    reference_answer: str
    max_marks: float
    essential_keywords: Optional[str] = None
    rubric_criteria: Optional[str] = None

class QuestionResponse(BaseModel):
    id: int
    exam_id: int
    question_number: int
    question_text: str
    reference_answer: str
    max_marks: float
    essential_keywords: Optional[str] = None
    rubric_criteria: Optional[str] = None

    class Config:
        from_attributes = True

# --- Exam Schemas ---
class ExamCreate(BaseModel):
    title: str
    subject: str
    class_or_batch: str
    questions: List[QuestionCreate] = []

class ExamResponse(BaseModel):
    id: int
    title: str
    subject: str
    class_or_batch: str
    total_max_marks: float
    created_at: datetime.datetime
    questions: List[QuestionResponse] = []

    class Config:
        from_attributes = True

class ExamSummary(BaseModel):
    id: int
    title: str
    subject: str
    class_or_batch: str
    total_max_marks: float
    question_count: int
    submission_count: int
    created_at: datetime.datetime

# --- Submission Schemas ---
class SubmissionCreate(BaseModel):
    exam_id: int
    student_roll_no: str

class RegionCreate(BaseModel):
    page_id: int
    question_id: Optional[int] = None
    bbox: Optional[str] = None # "[ymin, xmin, ymax, xmax]"

class RegionUpdate(BaseModel):
    question_id: Optional[int] = None
    edited_text: Optional[str] = None

class RegionResponse(BaseModel):
    id: int
    page_id: int
    question_id: Optional[int]
    crop_path: str
    bbox: Optional[str]
    recognized_text: str
    edited_text: str
    confidence: float

    class Config:
        from_attributes = True

class PageResponse(BaseModel):
    id: int
    submission_id: int
    page_number: int
    image_path: str
    preprocessed_path: Optional[str] = None
    regions: List[RegionResponse] = []

    class Config:
        from_attributes = True

class EvaluationItemUpdate(BaseModel):
    approved_marks: float
    teacher_notes: Optional[str] = None
    is_teacher_approved: bool = True

class EvaluationItemResponse(BaseModel):
    id: int
    submission_id: int
    question_id: int
    region_id: Optional[int]
    transcribed_answer: str
    concepts_identified: str
    missing_concepts: str
    semantic_similarity: float
    suggested_marks: float
    approved_marks: float
    max_marks: float
    rationale: str
    review_needed: bool
    is_teacher_approved: bool
    teacher_notes: Optional[str]

    class Config:
        from_attributes = True

class SubmissionDetailResponse(BaseModel):
    id: int
    exam_id: int
    student_roll_no: str
    file_path: str
    original_filename: str
    file_type: str
    status: str
    suggested_total: float
    approved_total: float
    is_approved: bool
    approved_at: Optional[datetime.datetime]
    created_at: datetime.datetime
    pages: List[PageResponse] = []
    evaluations: List[EvaluationItemResponse] = []

    class Config:
        from_attributes = True

class SubmissionSummary(BaseModel):
    id: int
    exam_id: int
    exam_title: str
    student_roll_no: str
    status: str
    suggested_total: float
    approved_total: float
    is_approved: bool
    created_at: datetime.datetime

# --- Dashboard Stats ---
class DashboardStats(BaseModel):
    total_exams: int
    total_submissions: int
    evaluations_pending: int
    evaluations_completed: int
    recent_exams: List[ExamSummary]
    recent_submissions: List[SubmissionSummary]
