import os
import re
import io
import json
from typing import List, Dict, Any, Tuple
from PIL import Image

try:
    import pymupdf as fitz  # PyMuPDF
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

try:
    import docx
except ImportError:
    docx = None

from app.schemas.schemas import ParsedQuestionItem, RubricItem, AnswerKeyParseResponse
from app.services.preprocessing.image_processor import (
    render_pdf_to_images, preprocess_image, crop_image_region, auto_segment_answer_blocks
)
from app.services.handwriting.ocr_engine import handwriting_service


class AnswerKeyParser:
    """
    Parses both text-based and scanned handwritten answer keys into structured Q&A records.
    """

    @staticmethod
    def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()

        if ext in [".txt", ".text"]:
            try:
                return file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return file_bytes.decode("latin-1", errors="ignore")

        elif ext == ".docx":
            if docx is not None:
                doc = docx.Document(io.BytesIO(file_bytes))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                return "\n".join(paragraphs)
            else:
                # Fallback xml extraction
                import zipfile
                import xml.etree.ElementTree as ET
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    xml_content = z.read("word/document.xml")
                    root = ET.fromstring(xml_content)
                    texts = [node.text for node in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]
                    return " ".join(texts)

        elif ext == ".pdf":
            if fitz is not None:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                pages_text = []
                for page in doc:
                    txt = page.get_text()
                    if txt.strip():
                        pages_text.append(txt)
                doc.close()
                return "\n\n".join(pages_text)
            else:
                raise RuntimeError("PyMuPDF (fitz) is required to parse PDF text.")

        else:
            raise ValueError(f"Unsupported text file type: {ext}")

    @staticmethod
    def parse_raw_text(text: str) -> AnswerKeyParseResponse:
        """
        Parses formatted text into structured questions and reference answers.
        Recognizes question numbering (Q1, 1., Question 1, 1(a), etc.),
        Answer tags (Answer:, Ans:), Max marks ([5 marks], [Max Marks: 5]),
        Keywords, and Rubric criteria.
        """
        lines = [line.strip() for line in text.splitlines()]
        
        # Regex to detect question headers:
        # e.g., "Q1.", "Question 1:", "1.", "1(a).", "1(a)", "Q2(b):", "Part A: Q1"
        q_pattern = re.compile(
            r"^(?:(?:Part\s+[A-Za-z0-9]+\s*[:\-])\s*)?(?:Q(?:uestion)?\.?\s*(\d+[a-zA-Z]?(?:\([a-zA-Z0-9]+\))?)|\b(\d+)\s*(?:\(([a-zA-Z0-9]+)\)|[\.\)])(?:\s*[\.\)])?)\s*[:\.\-]?\s*(.*)$",
            re.IGNORECASE
        )
        
        # Regex to detect answer start:
        ans_pattern = re.compile(r"^(?:Ans(?:wer)?|Reference\s*Ans(?:wer)?|Model\s*Ans(?:wer)?)\s*[:\.\-]\s*(.*)$", re.IGNORECASE)
        
        # Regex to extract marks:
        marks_pattern = re.compile(r"\[(?:Max\s*Marks?|Marks?|M)\s*[:=]?\s*(\d+(?:\.\d+)?)\]|\((\d+(?:\.\d+)?)\s*(?:marks?|m)\)", re.IGNORECASE)

        # Regex to extract keywords:
        keywords_pattern = re.compile(r"^(?:Keywords?|Essential\s*Concepts?)\s*[:\.\-]\s*(.*)$", re.IGNORECASE)

        # Regex to extract rubric / criteria:
        rubric_pattern = re.compile(r"^(?:Rubric|Criteria|Marking\s*Scheme)\s*[:\.\-]\s*(.*)$", re.IGNORECASE)

        parsed_items: List[ParsedQuestionItem] = []
        unparsed_lines: List[str] = []

        current_q_num = 0
        current_label = ""
        current_q_text = ""
        current_ans_text = []
        current_max_marks = 5.0
        current_keywords = ""
        current_rubric_items: List[RubricItem] = []
        current_alternatives: List[str] = []

        is_capturing_answer = False

        def commit_current():
            nonlocal current_q_num, current_label, current_q_text, current_ans_text, current_max_marks, current_keywords, current_rubric_items, current_alternatives, is_capturing_answer
            if current_q_text.strip() or current_ans_text:
                full_ans = " ".join(current_ans_text).strip()
                if not current_rubric_items:
                    # Generate default balanced rubric criteria
                    half = round(current_max_marks / 2.0, 1)
                    rem = round(current_max_marks - half, 1)
                    current_rubric_items = [
                        RubricItem(criterion="Core definition & concept accuracy", marks=half),
                        RubricItem(criterion="Key mechanisms, explanation, and terminology", marks=rem)
                    ]

                parsed_items.append(ParsedQuestionItem(
                    question_number=current_q_num or (len(parsed_items) + 1),
                    question_label=current_label or f"Q{len(parsed_items) + 1}",
                    question_text=current_q_text.strip() or f"Question {len(parsed_items) + 1}",
                    reference_answer=full_ans or "No reference answer provided.",
                    max_marks=current_max_marks,
                    essential_keywords=current_keywords,
                    rubric_criteria=current_rubric_items,
                    alternative_answers=current_alternatives
                ))
            # Reset
            current_label = ""
            current_q_text = ""
            current_ans_text = []
            current_max_marks = 5.0
            current_keywords = ""
            current_rubric_items = []
            current_alternatives = []
            is_capturing_answer = False

        for line in lines:
            if not line:
                continue

            # First, check for marks anywhere in the line
            m_search = marks_pattern.search(line)
            if m_search:
                m_val = m_search.group(1) or m_search.group(2)
                if m_val:
                    current_max_marks = float(m_val)
                line = marks_pattern.sub("", line).strip()
                if not line:
                    continue

            q_match = q_pattern.match(line)
            ans_match = ans_pattern.match(line)
            kw_match = keywords_pattern.match(line)
            rub_match = rubric_pattern.match(line)

            if q_match:
                commit_current()
                q_id1 = q_match.group(1)
                q_id2 = q_match.group(2)
                sub_id = q_match.group(3)
                rest = q_match.group(4) or ""

                if q_id1:
                    raw_id = q_id1
                elif q_id2 and sub_id:
                    raw_id = f"{q_id2}({sub_id})"
                elif q_id2:
                    raw_id = q_id2
                else:
                    raw_id = str(len(parsed_items) + 1)

                current_label = f"Q{raw_id}" if not raw_id.upper().startswith("Q") else raw_id
                
                # Extract numeric index
                num_extract = re.search(r"\d+", raw_id)
                current_q_num = int(num_extract.group(0)) if num_extract else len(parsed_items) + 1

                current_q_text = rest
                is_capturing_answer = False

            elif ans_match:
                is_capturing_answer = True
                ans_content = ans_match.group(1).strip()
                if ans_content:
                    current_ans_text.append(ans_content)

            elif kw_match:
                current_keywords = kw_match.group(1).strip()

            elif rub_match:
                rub_str = rub_match.group(1).strip()
                # Parse rubric like "2 marks for definition; 3 marks for example"
                for item in re.split(r"[;,]\s*", rub_str):
                    if item:
                        # Extract mark if mentioned
                        im_search = re.search(r"(\d+(?:\.\d+)?)\s*(?:marks?|pts?|m)", item, re.IGNORECASE)
                        m_pts = float(im_search.group(1)) if im_search else 1.0
                        clean_desc = re.sub(r"(\d+(?:\.\d+)?)\s*(?:marks?|pts?|m)\s*(?:for\s*)?", "", item, flags=re.IGNORECASE).strip()
                        current_rubric_items.append(RubricItem(criterion=clean_desc or item, marks=m_pts))

            elif is_capturing_answer:
                current_ans_text.append(line)

            elif current_q_text:
                # Continuation of question text
                current_q_text += " " + line
            else:
                unparsed_lines.append(line)

        # Commit final question
        commit_current()

        # If no questions were parsed, treat entire text as 1 question or unparsed
        if not parsed_items and unparsed_lines:
            combined = "\n".join(unparsed_lines)
            parsed_items.append(ParsedQuestionItem(
                question_number=1,
                question_label="Q1",
                question_text="Examination Question 1",
                reference_answer=combined,
                max_marks=5.0,
                essential_keywords="",
                rubric_criteria=[
                    RubricItem(criterion="Overall correctness & completeness", marks=5.0)
                ],
                alternative_answers=[]
            ))
            unparsed_lines = []

        return AnswerKeyParseResponse(
            questions=parsed_items,
            unparsed_text="\n".join(unparsed_lines),
            page_count=1,
            method="text"
        )

    @classmethod
    def parse_scanned_answer_key(cls, file_bytes: bytes, filename: str, output_base_dir: str) -> AnswerKeyParseResponse:
        """
        Parses multi-page scanned handwritten answer keys into structured Q&A records.
        Preserves page ordering and assigns cropped text blocks to reference questions.
        """
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pdf", ".jpg", ".jpeg", ".png"]:
            raise ValueError("Scanned answer key must be a PDF, JPG, or PNG file.")

        session_id = os.urandom(4).hex()
        upload_dir = os.path.join(output_base_dir, f"answer_key_{session_id}")
        os.makedirs(upload_dir, exist_ok=True)

        doc_path = os.path.join(upload_dir, f"source{ext}")
        with open(doc_path, "wb") as f:
            f.write(file_bytes)

        # Render pages
        if ext == ".pdf":
            page_paths = render_pdf_to_images(doc_path, upload_dir)
        else:
            page_dest = os.path.join(upload_dir, "page_1.jpg")
            with Image.open(doc_path) as im:
                im.convert("RGB").save(page_dest)
            page_paths = [page_dest]

        extracted_questions: List[ParsedQuestionItem] = []
        all_transcriptions = []

        # Run TrOCR on each page
        for p_idx, p_img_path in enumerate(page_paths):
            prep_img_path = os.path.join(upload_dir, f"prep_page_{p_idx + 1}.jpg")
            preprocess_image(p_img_path, prep_img_path)

            # Horizontal auto-segmentation (2 blocks per page default for answer key)
            blocks = auto_segment_answer_blocks(prep_img_path, num_questions=2)
            for b_idx, bbox in enumerate(blocks):
                crop_path = os.path.join(upload_dir, f"crop_p{p_idx + 1}_b{b_idx + 1}.jpg")
                crop_image_region(prep_img_path, crop_path, bbox)

                # TrOCR handwriting OCR
                ocr_text = handwriting_service.recognize_crop(crop_path)
                
                if ocr_text and not ocr_text.startswith("[Blank"):
                    all_transcriptions.append({
                        "page": p_idx + 1,
                        "crop_path": crop_path,
                        "text": ocr_text
                    })

        # Process transcriptions into Q&A
        for idx, item in enumerate(all_transcriptions):
            raw_text = item["text"]
            q_match = re.search(r"\b(?:Q(?:uestion)?\.?\s*(\d+[a-zA-Z]?)|(\d+)[\.\)])", raw_text, re.IGNORECASE)
            q_num = int(re.search(r"\d+", q_match.group(0)).group(0)) if q_match else (idx + 1)
            q_label = f"Q{q_num}"

            clean_text = raw_text
            if q_match:
                clean_text = raw_text[q_match.end():].lstrip(" :.-")

            words = [w for w in re.findall(r"\b[A-Za-z]{4,}\b", clean_text)]
            keywords = ", ".join(list(dict.fromkeys(words))[:5])

            rubric = [
                RubricItem(criterion="Accurate conceptual definition", marks=2.5),
                RubricItem(criterion="Key explanation points and examples", marks=2.5)
            ]

            extracted_questions.append(ParsedQuestionItem(
                question_number=q_num,
                question_label=q_label,
                question_text=f"Question {q_num} (Extracted from handwritten key page {item['page']})",
                reference_answer=clean_text or raw_text,
                max_marks=5.0,
                essential_keywords=keywords,
                rubric_criteria=rubric,
                alternative_answers=[],
                source_page=item["page"],
                crop_path=item["crop_path"]
            ))

        if not extracted_questions:
            extracted_questions.append(ParsedQuestionItem(
                question_number=1,
                question_label="Q1",
                question_text="Question 1 (Review scanned key)",
                reference_answer="[Handwriting extracted - please verify transcription]",
                max_marks=5.0,
                essential_keywords="",
                rubric_criteria=[RubricItem(criterion="Correctness", marks=5.0)],
                alternative_answers=[],
                source_page=1,
                crop_path=page_paths[0] if page_paths else None
            ))

        return AnswerKeyParseResponse(
            questions=extracted_questions,
            unparsed_text="",
            page_count=len(page_paths),
            method="scanned_handwritten"
        )
