export interface Question {
  id?: number;
  question_number: number;
  question_text: string;
  reference_answer: string;
  max_marks: number;
  essential_keywords?: string;
  rubric_criteria?: string;
}

export interface Exam {
  id: number;
  title: string;
  subject: string;
  class_or_batch: string;
  total_max_marks: number;
  question_count?: number;
  submission_count?: number;
  created_at: string;
  questions?: Question[];
}

export interface AnswerRegion {
  id: number;
  page_id: number;
  question_id?: number | null;
  crop_path: string;
  bbox?: string;
  recognized_text: string;
  edited_text: string;
  confidence: number;
}

export interface SubmissionPage {
  id: number;
  submission_id: number;
  page_number: number;
  image_path: string;
  preprocessed_path?: string;
  regions: AnswerRegion[];
}

export interface EvaluationItem {
  id: number;
  submission_id: number;
  question_id: number;
  region_id?: number;
  transcribed_answer: string;
  concepts_identified: string; // JSON string
  missing_concepts: string;    // JSON string
  semantic_similarity: number;
  suggested_marks: number;
  approved_marks: number;
  max_marks: number;
  rationale: string;
  review_needed: boolean;
  is_teacher_approved: boolean;
  teacher_notes?: string;
}

export interface SubmissionDetail {
  id: number;
  exam_id: number;
  student_roll_no: string;
  file_path: string;
  original_filename: string;
  file_type: string;
  status: string;
  suggested_total: number;
  approved_total: number;
  is_approved: boolean;
  approved_at?: string;
  created_at: string;
  pages: SubmissionPage[];
  evaluations: EvaluationItem[];
}

export interface DashboardStats {
  total_exams: number;
  total_submissions: number;
  evaluations_pending: number;
  evaluations_completed: number;
  recent_exams: Exam[];
  recent_submissions: {
    id: number;
    exam_id: number;
    exam_title: string;
    student_roll_no: string;
    status: string;
    suggested_total: number;
    approved_total: number;
    is_approved: boolean;
    created_at: string;
  }[];
}
