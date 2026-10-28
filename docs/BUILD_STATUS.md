# Grade Script — Build Status & Verification Log

**Last Updated:** October 28, 2026 (Answer Key OCR, Question-Wise Rubrics & Intelligent Mapping Milestone)

---

## 1. Environment & Hardware Verification

| Component | Status | Details |
|---|---|---|
| **Python** | ✅ Verified | Python 3.13.0 (64-bit) |
| **CUDA / GPU** | ✅ Verified | NVIDIA GeForce RTX 3050 6GB Laptop GPU (CUDA 12.4 enabled, `torch.cuda.is_available() == True`) |
| **PyTorch & Vision** | ✅ Verified | `torch==2.6.0+cu124`, `torchvision==0.21.0+cu124` |
| **Node.js & npm** | ✅ Verified | Node v24.20.0, npm 11.19.0 |
| **ML & NLP Stack** | ✅ Verified | `transformers==5.19.0`, `sentence-transformers==6.1.0`, `scikit-learn==1.6.0`, `opencv-python`, `Pillow==11.0.0` |
| **Document Tools** | ✅ Verified | `PyMuPDF==1.28.2`, `python-docx==1.2.0`, `reportlab==5.0.1` |
| **Testing** | ✅ Verified | `pytest==9.2.0` (15/15 tests passing, 100% green) |
| **Backend Framework** | ✅ Verified | `fastapi==0.143.0`, `uvicorn==0.54.0`, `pydantic==2.10.x`, `sqlalchemy==2.0.x` |
| **Frontend Framework** | ✅ Verified | React 19, Vite 8, TypeScript 6, Tailwind CSS v4, Lucide Icons, Recharts, Axios |

---

## 2. Server & Build Status

- **Backend (FastAPI / Uvicorn):** Running on `http://127.0.0.1:8000` (Status 200 on `/api/dashboard`)
- **Frontend (React / Vite):** Running on `http://127.0.0.1:5173` (Vite dev server active with API proxy to port 8000)
- **Frontend Production Build:** Verified (`npm run build` succeeds cleanly in < 1s, zero TypeScript errors)
- **Automated Test Suite:** 15/15 tests passing (`tests/test_answer_key_parser.py`, `tests/test_intelligent_mapping.py`, `tests/test_marking_scheme_and_grading.py`, `tests/test_api_integration.py`)

---

## 3. Completed Architecture & Modules

### 1. Database Schema (`backend/app/models/entities.py`):
- `Exam`: metadata, total marks, relationship to questions and submissions.
- `Question`:
  - `question_label`: Human-readable identifier (`Q1`, `1(a)`, `2.1`).
  - `question_number`: Sequential ordering integer.
  - `question_text`: Problem statement.
  - `reference_answer`: Primary expected response.
  - `max_marks`: Allocated maximum score.
  - `essential_keywords`: Comma-separated domain concepts.
  - `rubric_criteria`: JSON array of structured items `[{"criterion": "...", "marks": 2.0}]`.
  - `partial_credit_rules`: Descriptive teacher guidelines for partial credit.
  - `alternative_answers`: JSON list of alternative acceptable answers.
  - `negative_marking`: Optional penalty for incorrect answers.
- `Submission`: student roll number, original document file path, processing status, totals.
- `SubmissionPage`: rendered pages from multi-page PDFs or images.
- `AnswerRegion`:
  - `detected_question_label`: Extracted question tag (`Q1`, `Q2(a)`).
  - `mapping_confidence`: Float confidence score (0.0 to 1.0).
  - `mapping_method`: `explicit_label`, `semantic`, `duplicate_detected`, or `unmatched`.
  - `candidate_matches`: Top ranking candidate questions with match scores and rationales.
  - `is_ambiguous`: Flag set when top two candidate matches are closely contested.
  - `is_manually_mapped`: Flag set when a teacher overrides the mapping.
  - `crop_path`, `transcription`, `teacher_override_transcription`.
- `EvaluationItem`:
  - `suggested_marks`, `approved_marks`, `semantic_similarity`, `concepts_identified`, `missing_concepts`, `rationale`, `rubric_scores`.

### 2. Services:
- **Answer Key Parser (`backend/app/services/answer_key/parser.py`):**
  - Text-based ingestion: Parses `.txt`, `.docx`, and text `.pdf` files.
  - Scanned handwritten ingestion: Converts multi-page PDFs to images, runs TrOCR handwriting OCR on each page, and reconstructs structured Q&A records.
  - Preserves any unparsed text so educators never lose unparsed questions or notes.
- **Intelligent Answer Mapping (`backend/app/services/mapping/answer_mapper.py`):**
  - Order-independent global assignment (handles students answering Q3, then Q1, then Q2).
  - Multi-signal matching: Explicit question/subquestion labels (`Q3`, `1(a)`), prompt semantic similarity, and reference answer compatibility.
  - Duplicate answer detection and ambiguous match flagging.
  - Dynamic remapping with immediate regrading against newly assigned question rubrics.
- **Grading Engine (`backend/app/services/grading/engine.py`):**
  - Itemized rubric evaluation, semantic cosine similarity via Sentence Transformers (`all-MiniLM-L6-v2`), keyword presence verification, alternative acceptable answers matching, and negative marking penalty calculation.
- **Preprocessing (`backend/app/services/preprocessing/image_processor.py`):**
  - PyMuPDF 144 DPI rendering, CLAHE contrast enhancement, OpenCV bilateral filtering, dynamic answer region segmentation.
- **Handwriting OCR (`backend/app/services/handwriting/ocr_engine.py`):**
  - Microsoft TrOCR (`microsoft/trocr-base-handwritten`) running on PyTorch CUDA.
- **PDF Reporting (`backend/app/services/reporting/pdf_generator.py`):**
  - ReportLab PDF generator with question labels (`1(a)`, `Q3`) and itemized rubric score breakdowns.

### 3. Frontend Pages & Components:
- **`CreateExam.tsx`:** 4-step wizard:
  1. *Answer Key Source Selection*: Upload text file / direct paste OR upload scanned handwritten answer key.
  2. *OCR & Parsing Review*: Live editable Q&A cards with unparsed text warning panel.
  3. *Question-Wise Marking Scheme Configuration*: Configure max marks, rubric breakdown tables, alternative answers, partial-credit rules, and negative marking with live total mark validation.
  4. *Final Review & Save*: Summary of questions, rubrics, and total marks.
- **`EvaluationReview.tsx`:**
  - Intelligent Mapping banner with mapping confidence, method badges (`explicit_label`, `semantic`, `duplicate_detected`), and candidate score drawer.
  - Interactive Question Remapping dropdown allowing teachers to instantly reassign any region to another question, triggering immediate regrading.
  - Itemized rubric breakdown list showing points earned per criterion.
  - Unanswered reference questions warning cards.
  - Full inline handwriting transcription editing and mark approval workflow.
- **`Dashboard.tsx` & `UploadSheet.tsx`:** Real-time metrics, submission status, and multi-format sheet ingestion.

---

## 4. Verification & Test Summary

All 15 unit and integration tests passing:
- `test_parse_raw_text_standard` ✅
- `test_parse_subquestions_and_numbering` ✅
- `test_unparsed_text_preservation` ✅
- `test_parse_text_answer_key_api` ✅
- `test_create_exam_with_rubrics_and_validation` ✅
- `test_create_exam_rejects_duplicate_labels` ✅
- `test_dashboard_endpoint` ✅
- `test_extract_detected_identifier` ✅
- `test_reordered_student_answers_mapping` ✅
- `test_missing_question_identifier_semantic_mapping` ✅
- `test_duplicate_and_ambiguity_detection` ✅
- `test_rubric_based_evaluation` ✅
- `test_alternative_answers_matching` ✅
- `test_empty_answer_handling` ✅
- `test_negative_marking` ✅
