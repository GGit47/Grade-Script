import os
import json
import uuid
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database.session import get_db
from app.models.entities import Exam, Question, Submission, SubmissionPage, AnswerRegion, EvaluationItem
from app.schemas.schemas import (
    ExamCreate, ExamResponse, ExamSummary,
    SubmissionDetailResponse, SubmissionSummary, DashboardStats,
    RegionUpdate, RegionRemapRequest, EvaluationItemUpdate,
    AnswerKeyParseResponse
)
from app.services.preprocessing.image_processor import (
    render_pdf_to_images, preprocess_image, crop_image_region, auto_segment_answer_blocks
)
from app.services.handwriting.ocr_engine import handwriting_service
from app.services.grading.engine import grading_engine
from app.services.reporting.pdf_generator import generate_pdf_report
from app.services.answer_key.parser import AnswerKeyParser
from app.services.mapping.answer_mapper import answer_mapper

router = APIRouter()

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
DOCS_DIR = os.path.join(UPLOAD_DIR, "docs")
CROPS_DIR = os.path.join(UPLOAD_DIR, "crops")
REPORTS_DIR = os.path.join(UPLOAD_DIR, "reports")
KEYS_DIR = os.path.join(UPLOAD_DIR, "answer_keys")

for d in [DOCS_DIR, CROPS_DIR, REPORTS_DIR, KEYS_DIR]:
    os.makedirs(d, exist_ok=True)


# --- Dashboard Stats ---
@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_exams = db.query(Exam).count()
    total_submissions = db.query(Submission).count()
    evaluations_pending = db.query(Submission).filter(Submission.is_approved == False).count()
    evaluations_completed = db.query(Submission).filter(Submission.is_approved == True).count()

    recent_exams = db.query(Exam).order_by(desc(Exam.created_at)).limit(5).all()
    recent_submissions = db.query(Submission).order_by(desc(Submission.created_at)).limit(5).all()

    exam_summaries = [
        ExamSummary(
            id=e.id,
            title=e.title,
            subject=e.subject,
            class_or_batch=e.class_or_batch,
            total_max_marks=e.total_max_marks,
            question_count=len(e.questions),
            submission_count=len(e.submissions),
            created_at=e.created_at
        ) for e in recent_exams
    ]

    sub_summaries = [
        SubmissionSummary(
            id=s.id,
            exam_id=s.exam_id,
            exam_title=s.exam.title if s.exam else "Unknown",
            student_roll_no=s.student_roll_no,
            status=s.status,
            suggested_total=s.suggested_total,
            approved_total=s.approved_total,
            is_approved=s.is_approved,
            created_at=s.created_at
        ) for s in recent_submissions
    ]

    return DashboardStats(
        total_exams=total_exams,
        total_submissions=total_submissions,
        evaluations_pending=evaluations_pending,
        evaluations_completed=evaluations_completed,
        recent_exams=exam_summaries,
        recent_submissions=sub_summaries
    )


# --- Answer Key Ingestion Endpoints (Feature A) ---
@router.post("/answer-keys/parse-text", response_model=AnswerKeyParseResponse)
async def parse_text_answer_key(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None)
):
    """
    Parses a text-based answer key either from direct text entry or from uploaded .txt, .docx, or .pdf files.
    """
    text_content = ""
    if file and file.filename:
        content = await file.read()
        try:
            text_content = AnswerKeyParser.extract_text_from_file(content, file.filename)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to extract text from file: {str(e)}")
    elif raw_text:
        text_content = raw_text
    else:
        raise HTTPException(status_code=400, detail="Please provide either a text file (.txt, .docx, .pdf) or direct text entry.")

    if not text_content.strip():
        raise HTTPException(status_code=400, detail="Provided answer key text is empty.")

    try:
        return AnswerKeyParser.parse_raw_text(text_content)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/answer-keys/parse-scanned", response_model=AnswerKeyParseResponse)
async def parse_scanned_answer_key(file: UploadFile = File(...)):
    """
    Accepts scanned handwritten answer keys (PDF/JPG/PNG), applies image preprocessing
    and TrOCR handwriting recognition across all pages, and structures extracted Q&A.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Scanned answer key must be a PDF, JPG, or PNG document.")

    content = await file.read()
    try:
        return AnswerKeyParser.parse_scanned_answer_key(content, file.filename, KEYS_DIR)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process scanned answer key: {str(e)}")


# --- Exam Endpoints ---
@router.post("/exams", response_model=ExamResponse)
def create_exam(exam_in: ExamCreate, db: Session = Depends(get_db)):
    if not exam_in.questions:
        raise HTTPException(status_code=400, detail="An examination must contain at least one question.")

    # Validate duplicate question numbers / labels
    seen_labels = set()
    total_marks = 0.0

    for q in exam_in.questions:
        if q.max_marks <= 0:
            raise HTTPException(status_code=400, detail=f"Question #{q.question_number} must have maximum marks greater than 0.")
        
        lbl = (q.question_label or f"Q{q.question_number}").strip().upper()
        if lbl in seen_labels:
            raise HTTPException(status_code=400, detail=f"Duplicate question identifier detected: '{lbl}'.")
        seen_labels.add(lbl)

        # Validate rubric criteria sum if structured
        if q.rubric_criteria:
            try:
                rub_items = json.loads(q.rubric_criteria) if q.rubric_criteria.startswith("[") else []
                if isinstance(rub_items, list) and rub_items:
                    rub_sum = sum(float(item.get("marks", 0)) for item in rub_items)
                    if rub_sum > (q.max_marks + 0.01):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Sum of rubric criteria marks ({rub_sum}) exceeds max marks ({q.max_marks}) for {lbl}."
                        )
            except json.JSONDecodeError:
                pass

        total_marks += q.max_marks

    exam = Exam(
        title=exam_in.title,
        subject=exam_in.subject,
        class_or_batch=exam_in.class_or_batch,
        total_max_marks=round(total_marks, 2)
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    for q_data in exam_in.questions:
        q = Question(
            exam_id=exam.id,
            question_number=q_data.question_number,
            question_label=q_data.question_label or f"Q{q_data.question_number}",
            question_type=q_data.question_type or "subjective",
            question_text=q_data.question_text,
            reference_answer=q_data.reference_answer,
            max_marks=q_data.max_marks,
            essential_keywords=q_data.essential_keywords,
            rubric_criteria=q_data.rubric_criteria,
            partial_credit_rules=q_data.partial_credit_rules,
            alternative_answers=q_data.alternative_answers,
            negative_marking=q_data.negative_marking or 0.0
        )
        db.add(q)
    db.commit()
    db.refresh(exam)
    return exam


@router.get("/exams", response_model=List[ExamSummary])
def list_exams(db: Session = Depends(get_db)):
    exams = db.query(Exam).order_by(desc(Exam.created_at)).all()
    return [
        ExamSummary(
            id=e.id,
            title=e.title,
            subject=e.subject,
            class_or_batch=e.class_or_batch,
            total_max_marks=e.total_max_marks,
            question_count=len(e.questions),
            submission_count=len(e.submissions),
            created_at=e.created_at
        ) for e in exams
    ]


@router.get("/exams/{exam_id}", response_model=ExamResponse)
def get_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


# --- Submissions & Intelligent Answer-to-Question Mapping (Feature C) ---
@router.post("/submissions/upload", response_model=SubmissionDetailResponse)
async def upload_submission(
    exam_id: int = Form(...),
    student_roll_no: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF, JPG, and PNG are allowed.")

    file_uuid = str(uuid.uuid4())[:8]
    safe_name = f"{student_roll_no}_{file_uuid}{ext}"
    saved_doc_path = os.path.join(DOCS_DIR, safe_name)

    content = await file.read()
    with open(saved_doc_path, "wb") as f:
        f.write(content)

    submission = Submission(
        exam_id=exam.id,
        student_roll_no=student_roll_no,
        file_path=saved_doc_path,
        original_filename=file.filename,
        file_type=ext.replace(".", ""),
        status="uploaded"
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Process Pages
    pages_output_dir = os.path.join(UPLOAD_DIR, "pages", str(submission.id))
    os.makedirs(pages_output_dir, exist_ok=True)

    if ext == ".pdf":
        page_paths = render_pdf_to_images(saved_doc_path, pages_output_dir)
    else:
        dest = os.path.join(pages_output_dir, f"page_1{ext}")
        with open(dest, "wb") as f:
            f.write(content)
        page_paths = [dest]

    # Preprocess and segment answer regions across pages
    questions = sorted(exam.questions, key=lambda q: q.question_number)
    num_q = max(1, len(questions))

    created_regions = []
    regions_matching_payload = []

    for p_idx, p_path in enumerate(page_paths):
        prep_path = os.path.join(pages_output_dir, f"prep_page_{p_idx + 1}.jpg")
        preprocess_image(p_path, prep_path)

        page_record = SubmissionPage(
            submission_id=submission.id,
            page_number=p_idx + 1,
            image_path=p_path,
            preprocessed_path=prep_path
        )
        db.add(page_record)
        db.commit()
        db.refresh(page_record)

        # Segment regions
        per_page_q = max(2, min(8, round(num_q / max(1, len(page_paths)))))
        bboxes = auto_segment_answer_blocks(prep_path, num_questions=per_page_q)
        for r_idx, bbox in enumerate(bboxes):
            crop_filename = f"crop_s{submission.id}_p{page_record.id}_r{r_idx+1}.jpg"
            crop_path = os.path.join(CROPS_DIR, crop_filename)
            crop_image_region(prep_path, crop_path, bbox)

            # Recognize handwriting with TrOCR
            text = handwriting_service.recognize_crop(crop_path)

            region = AnswerRegion(
                page_id=page_record.id,
                crop_path=crop_path,
                bbox=json.dumps(bbox),
                recognized_text=text,
                edited_text=text,
                confidence=0.85 if text else 0.0
            )
            db.add(region)
            db.commit()
            db.refresh(region)

            created_regions.append(region)
            regions_matching_payload.append({
                "id": region.id,
                "text": text,
                "crop_path": crop_path,
                "page_number": p_idx + 1
            })

    # Run Intelligent Answer-to-Question Mapping (order-independent, multi-signal)
    mapping_results = answer_mapper.match_regions_to_questions(regions_matching_payload, questions)
    
    # Track which questions were matched to at least one student answer
    matched_q_ids = set()

    for idx, m_res in enumerate(mapping_results):
        reg = created_regions[idx]
        assigned_qid = m_res["assigned_question_id"]
        reg.question_id = assigned_qid
        reg.detected_question_label = m_res["detected_label"]
        reg.mapping_confidence = m_res["mapping_confidence"]
        reg.mapping_method = m_res["mapping_method"]
        reg.candidate_matches = json.dumps(m_res["candidate_matches"])
        reg.is_ambiguous = m_res["is_ambiguous"]

        if assigned_qid:
            matched_q_ids.add(assigned_qid)
            assigned_q = next((q for q in questions if q.id == assigned_qid), None)
            if assigned_q:
                # Grade answer using rubric criteria & alternative answers
                eval_res = grading_engine.evaluate_answer(
                    student_text=reg.edited_text or reg.recognized_text,
                    reference_text=assigned_q.reference_answer,
                    max_marks=assigned_q.max_marks,
                    essential_keywords_str=assigned_q.essential_keywords or "",
                    rubric_criteria=assigned_q.rubric_criteria or "",
                    alternative_answers_str=assigned_q.alternative_answers or "",
                    negative_marking=assigned_q.negative_marking or 0.0,
                    question_type=assigned_q.question_type or "subjective"
                )
                eval_item = EvaluationItem(
                    submission_id=submission.id,
                    question_id=assigned_q.id,
                    region_id=reg.id,
                    transcribed_answer=reg.edited_text or reg.recognized_text,
                    concepts_identified=json.dumps(eval_res["concepts_identified"]),
                    missing_concepts=json.dumps(eval_res["missing_concepts"]),
                    semantic_similarity=eval_res["semantic_similarity"],
                    suggested_marks=eval_res["suggested_marks"],
                    approved_marks=eval_res["suggested_marks"],
                    max_marks=assigned_q.max_marks,
                    rationale=eval_res["rationale"],
                    review_needed=eval_res["review_needed"] or reg.is_ambiguous,
                    rubric_scores=json.dumps(eval_res.get("rubric_scores", []))
                )
                db.add(eval_item)

    # Handle Unanswered Reference Questions
    for q in questions:
        if q.id not in matched_q_ids:
            unanswered_eval = EvaluationItem(
                submission_id=submission.id,
                question_id=q.id,
                region_id=None,
                transcribed_answer="",
                concepts_identified="[]",
                missing_concepts=json.dumps([kw.strip() for kw in (q.essential_keywords or "").split(",") if kw.strip()]),
                semantic_similarity=0.0,
                suggested_marks=0.0,
                approved_marks=0.0,
                max_marks=q.max_marks,
                rationale="Unanswered: No student answer detected for this question.",
                review_needed=True,
                rubric_scores="[]"
            )
            db.add(unanswered_eval)

    # Recalculate totals
    db.commit()
    eval_items = db.query(EvaluationItem).filter(EvaluationItem.submission_id == submission.id).all()
    sug_total = sum(item.suggested_marks for item in eval_items)
    app_total = sum(item.approved_marks for item in eval_items)
    submission.suggested_total = round(sug_total, 2)
    submission.approved_total = round(app_total, 2)
    submission.status = "evaluated"
    db.commit()
    db.refresh(submission)

    return submission


@router.get("/submissions/{sub_id}", response_model=SubmissionDetailResponse)
def get_submission(sub_id: int, db: Session = Depends(get_db)):
    submission = db.query(Submission).filter(Submission.id == sub_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


# --- Manual Re-Mapping Endpoint (Feature C) ---
@router.put("/regions/{region_id}/remap")
def remap_region(region_id: int, remap_data: RegionRemapRequest, db: Session = Depends(get_db)):
    """
    Allows the teacher to manually reassign an answer region to a different reference question,
    triggering immediate re-evaluation using the new question's reference answer and rubric.
    """
    region = db.query(AnswerRegion).filter(AnswerRegion.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Answer region not found")

    sub = region.page.submission
    old_qid = region.question_id
    new_qid = remap_data.question_id

    region.question_id = new_qid
    region.is_manually_mapped = True
    region.mapping_method = "manual"
    region.is_ambiguous = False
    region.mapping_confidence = 1.0

    if remap_data.edited_text is not None:
        region.edited_text = remap_data.edited_text

    db.commit()

    # Re-evaluate or update evaluation item
    eval_item = db.query(EvaluationItem).filter(EvaluationItem.region_id == region.id).first()

    if new_qid:
        new_q = db.query(Question).filter(Question.id == new_qid).first()
        if new_q:
            eval_res = grading_engine.evaluate_answer(
                student_text=region.edited_text or region.recognized_text,
                reference_text=new_q.reference_answer,
                max_marks=new_q.max_marks,
                essential_keywords_str=new_q.essential_keywords or "",
                rubric_criteria=new_q.rubric_criteria or "",
                alternative_answers_str=new_q.alternative_answers or "",
                negative_marking=new_q.negative_marking or 0.0,
                question_type=new_q.question_type or "subjective"
            )

            if not eval_item:
                eval_item = EvaluationItem(
                    submission_id=sub.id,
                    question_id=new_q.id,
                    region_id=region.id
                )
                db.add(eval_item)

            eval_item.question_id = new_q.id
            eval_item.transcribed_answer = region.edited_text or region.recognized_text
            eval_item.concepts_identified = json.dumps(eval_res["concepts_identified"])
            eval_item.missing_concepts = json.dumps(eval_res["missing_concepts"])
            eval_item.semantic_similarity = eval_res["semantic_similarity"]
            eval_item.suggested_marks = eval_res["suggested_marks"]
            eval_item.max_marks = new_q.max_marks
            eval_item.approved_marks = eval_res["suggested_marks"]
            eval_item.rationale = f"[Teacher Remapped to {new_q.question_label or f'Q{new_q.question_number}'}] " + eval_res["rationale"]
            eval_item.review_needed = False
            eval_item.rubric_scores = json.dumps(eval_res.get("rubric_scores", []))
            db.commit()
    else:
        # Unmapped: delete or reset evaluation item
        if eval_item:
            db.delete(eval_item)
            db.commit()

    # Recalculate submission totals
    all_evals = db.query(EvaluationItem).filter(EvaluationItem.submission_id == sub.id).all()
    sub.suggested_total = round(sum(e.suggested_marks for e in all_evals), 2)
    sub.approved_total = round(sum(e.approved_marks for e in all_evals), 2)
    db.commit()

    return {"message": "Region remapped and re-evaluated successfully", "region_id": region.id}


@router.put("/regions/{region_id}")
def update_region(region_id: int, update_data: RegionUpdate, db: Session = Depends(get_db)):
    region = db.query(AnswerRegion).filter(AnswerRegion.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Answer region not found")

    if update_data.question_id is not None:
        region.question_id = update_data.question_id
        region.is_manually_mapped = True
    if update_data.edited_text is not None:
        region.edited_text = update_data.edited_text

    db.commit()
    db.refresh(region)

    # Re-evaluate linked evaluation item
    eval_item = db.query(EvaluationItem).filter(EvaluationItem.region_id == region.id).first()
    if eval_item and region.question:
        q = region.question
        eval_res = grading_engine.evaluate_answer(
            student_text=region.edited_text,
            reference_text=q.reference_answer,
            max_marks=q.max_marks,
            essential_keywords_str=q.essential_keywords or "",
            rubric_criteria=q.rubric_criteria or "",
            alternative_answers_str=q.alternative_answers or "",
            negative_marking=q.negative_marking or 0.0
        )
        eval_item.transcribed_answer = region.edited_text
        eval_item.concepts_identified = json.dumps(eval_res["concepts_identified"])
        eval_item.missing_concepts = json.dumps(eval_res["missing_concepts"])
        eval_item.semantic_similarity = eval_res["semantic_similarity"]
        eval_item.suggested_marks = eval_res["suggested_marks"]
        if not eval_item.is_teacher_approved:
            eval_item.approved_marks = eval_res["suggested_marks"]
        eval_item.rationale = eval_res["rationale"]
        eval_item.review_needed = eval_res["review_needed"]
        eval_item.rubric_scores = json.dumps(eval_res.get("rubric_scores", []))
        db.commit()

        # Update totals
        sub = eval_item.submission
        all_evals = db.query(EvaluationItem).filter(EvaluationItem.submission_id == sub.id).all()
        sub.suggested_total = round(sum(e.suggested_marks for e in all_evals), 2)
        sub.approved_total = round(sum(e.approved_marks for e in all_evals), 2)
        db.commit()

    return {"message": "Region updated successfully", "region_id": region.id}


@router.put("/evaluations/{eval_id}")
def update_evaluation(eval_id: int, eval_update: EvaluationItemUpdate, db: Session = Depends(get_db)):
    eval_item = db.query(EvaluationItem).filter(EvaluationItem.id == eval_id).first()
    if not eval_item:
        raise HTTPException(status_code=404, detail="Evaluation item not found")

    # Enforce marks boundaries
    approved = max(0.0, min(eval_item.max_marks, eval_update.approved_marks))
    eval_item.approved_marks = approved
    eval_item.teacher_notes = eval_update.teacher_notes
    eval_item.is_teacher_approved = eval_update.is_teacher_approved

    db.commit()

    # Recalculate submission total
    sub = eval_item.submission
    all_evals = db.query(EvaluationItem).filter(EvaluationItem.submission_id == sub.id).all()
    sub.approved_total = round(sum(e.approved_marks for e in all_evals), 2)
    db.commit()

    return {"message": "Evaluation updated", "approved_marks": approved}


@router.post("/submissions/{sub_id}/finalize")
def finalize_submission(sub_id: int, db: Session = Depends(get_db)):
    sub = db.query(Submission).filter(Submission.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    sub.is_approved = True
    sub.status = "approved"
    sub.approved_at = datetime.datetime.utcnow()
    db.commit()

    return {"message": "Submission approved and finalized", "approved_total": sub.approved_total}


@router.get("/submissions/{sub_id}/report")
def download_submission_report(sub_id: int, db: Session = Depends(get_db)):
    sub = db.query(Submission).filter(Submission.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    report_pdf_name = f"Report_{sub.student_roll_no}_{sub.id}.pdf"
    report_pdf_path = os.path.join(REPORTS_DIR, report_pdf_name)

    # Structure data for report
    eval_items_data = []
    for item in sub.evaluations:
        r_scores = []
        if item.rubric_scores:
            try:
                r_scores = json.loads(item.rubric_scores)
            except Exception:
                r_scores = []

        eval_items_data.append({
            "question_number": item.question.question_number,
            "question_label": item.question.question_label or f"Q{item.question.question_number}",
            "question_text": item.question.question_text,
            "reference_answer": item.question.reference_answer,
            "transcribed_answer": item.transcribed_answer,
            "rationale": item.rationale,
            "suggested_marks": item.suggested_marks,
            "approved_marks": item.approved_marks,
            "max_marks": item.max_marks,
            "rubric_scores": r_scores
        })

    # Sort items by question number
    eval_items_data.sort(key=lambda x: x["question_number"])

    submission_dict = {
        "exam_title": sub.exam.title,
        "subject": sub.exam.subject,
        "student_roll_no": sub.student_roll_no,
        "approved_total": sub.approved_total,
        "total_max_marks": sub.exam.total_max_marks,
        "items": eval_items_data
    }

    generate_pdf_report(submission_dict, report_pdf_path)

    return FileResponse(
        report_pdf_path,
        media_type="application/pdf",
        filename=report_pdf_name
    )
