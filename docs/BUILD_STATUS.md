# Grade Script — Build Status & Verification Log

**Last Updated:** 2026-10-11 (Day 1 Environment & Milestone 1 Verification)

---

## 1. Environment & Hardware Verification

| Component | Status | Details |
|---|---|---|
| **Python** | ✅ Verified | Python 3.13.0 (64-bit) |
| **CUDA / GPU** | ✅ Verified | NVIDIA GeForce RTX 3050 6GB Laptop GPU (CUDA 12.4 enabled, `torch.cuda.is_available() == True`) |
| **PyTorch & Vision** | ✅ Verified | `torch==2.6.0+cu124`, `torchvision==0.21.0+cu124` |
| **Node.js & npm** | ✅ Verified | Node v24.20.0, npm 11.19.0 |
| **ML & NLP Stack** | ✅ Verified | `transformers==5.19.0`, `sentence-transformers==6.1.0`, `scikit-learn==1.6.0`, `opencv-python`, `Pillow==11.0.0` |
| **Document Tools** | ✅ Verified | `PyMuPDF==1.28.2`, `reportlab==5.0.1` |
| **Backend Framework** | ✅ Verified | `fastapi==0.143.0`, `uvicorn==0.54.0`, `pydantic==2.10.x`, `sqlalchemy==2.0.x` |
| **Frontend Framework** | ✅ Verified | React 19, Vite 8, TypeScript 6, Tailwind CSS v4, Lucide Icons, Recharts, Axios |

---

## 2. Server Status

- **Backend (FastAPI / Uvicorn):** Running on `http://127.0.0.1:8000` (Status 200 on `/api/dashboard`)
- **Frontend (React / Vite):** Running on `http://127.0.0.1:5173` (Status 200, Vite dev server active with API proxy to port 8000)

---

## 3. Completed Modules

1. **Backend Database Models (`backend/app/models/entities.py`):**
   - `Exam`: metadata, total marks, relationship to questions and submissions.
   - `Question`: question text, reference answer, max marks, essential keywords, rubrics.
   - `Submission`: student roll number, original document file path, processing status, totals.
   - `SubmissionPage`: rendered pages from multi-page PDFs or images.
   - `AnswerRegion`: cropped image slices, question mappings, OCR transcriptions, teacher corrections.
   - `EvaluationItem`: concept matching, semantic similarity, suggested vs. approved marks, rationales.

2. **Core Services:**
   - **Preprocessing (`backend/app/services/preprocessing/image_processor.py`):** PDF page rendering with PyMuPDF, CLAHE contrast enhancement, bilateral denoising with OpenCV, normalized bounding box cropper, horizontal section auto-segmenter.
   - **Handwriting OCR (`backend/app/services/handwriting/ocr_engine.py`):** Microsoft TrOCR integration with PyTorch CUDA acceleration, empty crop detector, graceful fallback.
   - **Grading Engine (`backend/app/services/grading/engine.py`):** Sentence Transformers cosine similarity, keyword/concept extractor, partial-credit multi-factor scoring.
   - **Reporting (`backend/app/services/reporting/pdf_generator.py`):** ReportLab PDF generator producing formatted student evaluation breakdown sheets.

3. **Frontend Pages & Components:**
   - **`Dashboard.tsx`:** KPI stats, examination lists, submission status overview.
   - **`CreateExam.tsx`:** Multi-question creation form with reference answers, rubrics, and keywords.
   - **`UploadSheet.tsx`:** Single-paper upload with type/size validation, page previews, and processing feedback.
   - **`EvaluationReview.tsx`:** Side-by-side view with handwritten image crops, editable TrOCR transcription, semantic score badges, teacher marks adjustment, and final approval.

---

## 4. Current Blockers

- **None.** Both servers are actively running and communicating.

---

## 5. Next Immediate Action

- Execute Day 1 acceptance test: Create an exam via the API/frontend, define questions, upload a sample document, and verify complete persistence and pipeline execution.
