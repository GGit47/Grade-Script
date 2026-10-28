import os
import re
import io
import csv
import json
from typing import List, Dict, Any, Tuple, Optional
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
    Parses both text-based (structured text or CSV) and scanned handwritten answer keys into canonical Q&A records.
    """

    @staticmethod
    def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()

        if ext in [".txt", ".text", ".csv", ".tsv"]:
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
    def is_csv_format(text: str) -> bool:
        """
        Detects whether raw text follows CSV formatting (such as Question_Number,Type,Correct_Answer).
        """
        stripped_lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not stripped_lines:
            return False

        first_line = stripped_lines[0].lower()
        # Direct header signature check
        if "," in first_line and any(
            h in first_line for h in ["question_number", "question", "correct_answer", "reference_answer", "type"]
        ):
            return True

        # Check with csv reader
        try:
            reader = csv.reader(io.StringIO(text))
            valid_rows = 0
            for idx, row in enumerate(reader):
                if not row or not any(c.strip() for c in row):
                    continue
                if len(row) >= 2:
                    col0 = row[0].strip().lower()
                    if re.match(r"^q?\d+$", col0) or any(h in col0 for h in ["question", "qno", "q_no", "qnum"]):
                        valid_rows += 1
                if idx > 15:
                    break
            if valid_rows >= min(3, len(stripped_lines)):
                return True
        except Exception:
            pass

        return False

    @classmethod
    def parse_csv_text(cls, text: str) -> AnswerKeyParseResponse:
        """
        Parses CSV answer key files or text containing CSV rows:
        e.g., Question_Number,Type,Correct_Answer
        """
        reader = csv.reader(io.StringIO(text))
        all_rows = [row for row in reader if any(cell.strip() for cell in row)]

        if not all_rows:
            raise ValueError("The provided CSV answer key contains no data.")

        # Identify header row if present
        header_row = None
        col_qnum = 0
        col_type = None
        col_ans = None
        col_text = None
        col_marks = None
        col_keywords = None
        col_rubric = None

        first_row_lower = [c.strip().lower() for c in all_rows[0]]
        is_header = any(
            h in first_row_lower[0] for h in ["question", "qno", "q_no", "qnum", "q", "no", "number"]
        ) or any(
            h in cell for cell in first_row_lower for h in ["type", "correct_answer", "answer", "reference_answer"]
        )

        data_start_idx = 0
        if is_header:
            header_row = first_row_lower
            data_start_idx = 1
            for idx, name in enumerate(header_row):
                if any(k == name or k in name for k in ["question_number", "q_no", "qno", "question", "q_num", "number"]):
                    if col_qnum == 0:  # first match
                        col_qnum = idx
                elif any(k == name or k in name for k in ["question_type", "type"]):
                    col_type = idx
                elif any(k == name or k in name for k in ["correct_answer", "reference_answer", "answer", "model_answer"]):
                    col_ans = idx
                elif any(k == name or k in name for k in ["question_text", "question_prompt", "prompt"]):
                    col_text = idx
                elif any(k == name or k in name for k in ["max_marks", "marks", "mark"]):
                    col_marks = idx
                elif any(k == name or k in name for k in ["keywords", "essential_keywords"]):
                    col_keywords = idx
                elif any(k == name or k in name for k in ["rubric", "rubric_criteria", "criteria"]):
                    col_rubric = idx

        # Default fallbacks if header was missing or column wasn't explicitly named
        sample_row = all_rows[data_start_idx] if data_start_idx < len(all_rows) else all_rows[0]
        if col_ans is None:
            if len(sample_row) >= 3:
                if col_type is None:
                    col_type = 1
                col_ans = 2
            elif len(sample_row) == 2:
                col_ans = 1
            else:
                col_ans = 0

        parsed_items: List[ParsedQuestionItem] = []
        seen_qnums = set()

        mcq_aliases = {"mcq", "multiple_choice", "multiple choice", "choice", "objective"}
        subjective_aliases = {"short_answer", "short answer", "subjective", "descriptive", "long_answer", "text", "theory", "essay"}

        for row_idx in range(data_start_idx, len(all_rows)):
            row = all_rows[row_idx]
            if not row or not any(c.strip() for c in row):
                continue

            raw_qnum = row[col_qnum].strip() if col_qnum < len(row) else ""
            if not raw_qnum:
                raise ValueError(f"Missing question number at CSV line {row_idx + 1}.")

            num_match = re.search(r"\d+", raw_qnum)
            if not num_match:
                raise ValueError(f"Invalid question number '{raw_qnum}' at CSV line {row_idx + 1}.")
            q_num = int(num_match.group(0))

            if q_num in seen_qnums:
                raise ValueError(f"Duplicate question number {q_num} detected in answer key (line {row_idx + 1}).")
            seen_qnums.add(q_num)

            # Extract type
            raw_type = row[col_type].strip() if col_type is not None and col_type < len(row) else ""
            type_norm = raw_type.lower().replace("-", "_")

            # Extract answer
            raw_ans = row[col_ans].strip() if col_ans is not None and col_ans < len(row) else ""
            if not raw_ans:
                raise ValueError(f"Question #{q_num} has a missing or empty reference answer (line {row_idx + 1}).")

            # Determine canonical question type
            if any(alias == type_norm or alias in type_norm for alias in mcq_aliases):
                q_type = "mcq"
            elif any(alias == type_norm or alias in type_norm for alias in subjective_aliases):
                q_type = "subjective"
            else:
                # Infer type from answer format: single option letter A-F is MCQ
                if re.match(r"^[A-Fa-f]$", raw_ans) or re.match(r"^\([A-Fa-f]\)$", raw_ans) or re.match(r"^option\s+[A-Fa-f]$", raw_ans, re.IGNORECASE):
                    q_type = "mcq"
                else:
                    q_type = "subjective"

            # Question text
            q_text = row[col_text].strip() if col_text is not None and col_text < len(row) else ""
            if not q_text:
                q_text = "[Question text unavailable]"

            # Question label
            q_label = f"Q{q_num}"

            # Marks
            marks = None
            if col_marks is not None and col_marks < len(row) and row[col_marks].strip():
                try:
                    marks = float(row[col_marks].strip())
                    if marks <= 0:
                        raise ValueError(f"Question #{q_num} maximum marks must be greater than 0.")
                except ValueError:
                    raise ValueError(f"Invalid marks value for Question #{q_num} at line {row_idx + 1}.")

            if marks is None:
                if q_type == "mcq":
                    marks = 1.0
                elif "short" in type_norm:
                    marks = 2.0
                else:
                    marks = 5.0

            # Keywords
            explicit_keywords = row[col_keywords].strip() if col_keywords is not None and col_keywords < len(row) else ""
            if not explicit_keywords and q_type == "subjective":
                # Extract key concepts automatically from reference answer
                stopwords = {"the", "is", "at", "which", "on", "a", "an", "and", "or", "to", "in", "for", "with", "as", "by", "that", "it", "of", "from"}
                words = [w for w in re.findall(r"\b[A-Za-z]{4,}\b", raw_ans) if w.lower() not in stopwords]
                explicit_keywords = ", ".join(list(dict.fromkeys(words))[:6])

            # Rubrics
            rubric_items: List[RubricItem] = []
            if col_rubric is not None and col_rubric < len(row) and row[col_rubric].strip():
                rub_text = row[col_rubric].strip()
                for item in re.split(r"[;,]\s*", rub_text):
                    if item.strip():
                        im_search = re.search(r"(\d+(?:\.\d+)?)\s*(?:marks?|pts?|m)", item, re.IGNORECASE)
                        m_pts = float(im_search.group(1)) if im_search else round(marks / 2.0, 1)
                        clean_desc = re.sub(r"(\d+(?:\.\d+)?)\s*(?:marks?|pts?|m)\s*(?:for\s*)?", "", item, flags=re.IGNORECASE).strip()
                        rubric_items.append(RubricItem(criterion=clean_desc or item.strip(), marks=m_pts))

            if not rubric_items:
                if q_type == "mcq":
                    # Clean option letter
                    opt_match = re.search(r"\b([A-Fa-f])\b", raw_ans)
                    clean_opt = opt_match.group(1).upper() if opt_match else raw_ans.upper()
                    raw_ans = clean_opt
                    rubric_items = [RubricItem(criterion=f"Correct MCQ option ({clean_opt})", marks=marks)]
                else:
                    half = round(marks / 2.0, 1)
                    rem = round(marks - half, 1)
                    rubric_items = [
                        RubricItem(criterion="Core definition & concept accuracy", marks=half),
                        RubricItem(criterion="Key explanation points and terminology", marks=rem)
                    ]

            parsed_items.append(ParsedQuestionItem(
                question_number=q_num,
                question_label=q_label,
                question_type=q_type,
                question_text=q_text,
                reference_answer=raw_ans,
                max_marks=marks,
                essential_keywords=explicit_keywords,
                rubric_criteria=rubric_items,
                alternative_answers=[]
            ))

        if not parsed_items:
            raise ValueError("No valid questions could be detected in the provided CSV answer key.")

        return AnswerKeyParseResponse(
            questions=parsed_items,
            unparsed_text="",
            page_count=1,
            method="csv"
        )

    @classmethod
    def parse_raw_text(cls, text: str) -> AnswerKeyParseResponse:
        """
        Parses text answer keys. Automatically branches to CSV parser if CSV format detected,
        otherwise parses structured text (Format A) with rubrics, marks, and keywords.
        """
        if not text or not text.strip():
            raise ValueError("Provided answer key text is empty.")

        # Check for CSV formatting
        if cls.is_csv_format(text):
            return cls.parse_csv_text(text)

        # Parse structured text (Format A)
        lines = [line.strip() for line in text.splitlines()]

        # Regex to detect question headers at line start:
        # e.g., "Q1.", "Q1:", "Question 1:", "1.", "1(a).", "1(a)", "Q2(b):", "Part A: Q1"
        q_pattern = re.compile(
            r"^(?:(?:Part\s+[A-Za-z0-9]+\s*[:\-])\s*)?(?:Q(?:uestion)?\.?\s*(\d+[a-zA-Z]?(?:\([a-zA-Z0-9]+\))?)|\b(\d+)\s*(?:\(([a-zA-Z0-9]+)\)|[\.\)])(?:\s*[\.\)])?)\s*[:\.\-]?\s*(.*)$",
            re.IGNORECASE
        )

        # Regex to detect answer start:
        ans_pattern = re.compile(
            r"^(?:Ans(?:wer)?|Reference\s*Ans(?:wer)?|Correct\s*Ans(?:wer)?|Model\s*Ans(?:wer)?)\s*[:\.\-]\s*(.*)$",
            re.IGNORECASE
        )

        # Regex to extract explicit question type:
        type_pattern = re.compile(
            r"^(?:(?:Question\s*)?Type)\s*[:\.\-]\s*(.*)$",
            re.IGNORECASE
        )

        # Regex to extract marks:
        marks_pattern = re.compile(
            r"\[(?:Max\s*Marks?|Marks?|M)\s*[:=]?\s*(\d+(?:\.\d+)?)\]|\((\d+(?:\.\d+)?)\s*(?:marks?|m)\)",
            re.IGNORECASE
        )

        # Regex to extract keywords:
        keywords_pattern = re.compile(
            r"^(?:Keywords?|Essential\s*Concepts?|Key\s*Concepts?)\s*[:\.\-]\s*(.*)$",
            re.IGNORECASE
        )

        # Regex to extract rubric / criteria:
        rubric_pattern = re.compile(
            r"^(?:Rubric|Criteria|Marking\s*Scheme|Evaluation\s*Rubric)\s*[:\.\-]\s*(.*)$",
            re.IGNORECASE
        )

        parsed_items: List[ParsedQuestionItem] = []
        unparsed_lines: List[str] = []
        seen_qnums = set()

        current_q_num = 0
        current_label = ""
        current_type = ""
        current_q_text = ""
        current_ans_text: List[str] = []
        current_max_marks: Optional[float] = None
        current_keywords = ""
        current_rubric_items: List[RubricItem] = []
        current_alternatives: List[str] = []

        is_capturing_answer = False
        is_capturing_rubric = False

        def commit_current():
            nonlocal current_q_num, current_label, current_type, current_q_text, current_ans_text
            nonlocal current_max_marks, current_keywords, current_rubric_items, current_alternatives
            nonlocal is_capturing_answer, is_capturing_rubric

            if current_q_text.strip() or current_ans_text or current_label:
                full_ans = " ".join(current_ans_text).strip()
                num = current_q_num or (len(parsed_items) + 1)

                if num in seen_qnums:
                    raise ValueError(f"Duplicate question number {num} detected in answer key.")
                seen_qnums.add(num)

                # Determine question type
                ans_upper = full_ans.upper()
                is_single_opt = bool(re.match(r"^[A-Fa-f]$", full_ans) or re.match(r"^\([A-Fa-f]\)$", full_ans) or re.match(r"^option\s+[A-Fa-f]$", full_ans, re.IGNORECASE))

                if current_type:
                    t_norm = current_type.lower()
                    if any(m in t_norm for m in ["mcq", "multiple", "choice", "objective"]):
                        q_type = "mcq"
                    else:
                        q_type = "subjective"
                elif is_single_opt:
                    q_type = "mcq"
                else:
                    q_type = "subjective"

                # Default marks
                if current_max_marks is None:
                    final_marks = 1.0 if q_type == "mcq" else 5.0
                else:
                    final_marks = current_max_marks
                    if final_marks <= 0:
                        raise ValueError(f"Question #{num} maximum marks must be greater than 0.")

                # If answer is empty
                if not full_ans:
                    raise ValueError(f"Question #{num} ({current_label or f'Q{num}'}) has a missing or empty reference answer.")

                # Rubric
                if not current_rubric_items:
                    if q_type == "mcq":
                        opt_match = re.search(r"\b([A-Fa-f])\b", full_ans)
                        clean_opt = opt_match.group(1).upper() if opt_match else full_ans
                        full_ans = clean_opt
                        current_rubric_items = [RubricItem(criterion=f"Correct MCQ option ({clean_opt})", marks=final_marks)]
                    else:
                        half = round(final_marks / 2.0, 1)
                        rem = round(final_marks - half, 1)
                        current_rubric_items = [
                            RubricItem(criterion="Core definition & concept accuracy", marks=half),
                            RubricItem(criterion="Key explanation points and terminology", marks=rem)
                        ]

                parsed_items.append(ParsedQuestionItem(
                    question_number=num,
                    question_label=current_label or f"Q{num}",
                    question_type=q_type,
                    question_text=current_q_text.strip() or f"Question {num}",
                    reference_answer=full_ans,
                    max_marks=final_marks,
                    essential_keywords=current_keywords,
                    rubric_criteria=current_rubric_items,
                    alternative_answers=current_alternatives
                ))

            # Reset
            current_q_num = 0
            current_label = ""
            current_type = ""
            current_q_text = ""
            current_ans_text = []
            current_max_marks = None
            current_keywords = ""
            current_rubric_items = []
            current_alternatives = []
            is_capturing_answer = False
            is_capturing_rubric = False

        for line in lines:
            if not line:
                # Blank lines separate paragraphs or answers cleanly
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
            type_match = type_pattern.match(line)
            kw_match = keywords_pattern.match(line)
            rub_match = rubric_pattern.match(line)

            # Important: Ensure we do NOT treat the word "Question" inside an answer body as a new question!
            # If is_capturing_answer is True, a line like "Question 1 was about..." should not break answer
            # unless it has an explicit question header syntax: e.g. "Q2." or "Question 2:" or "2."
            is_legit_new_q = False
            if q_match:
                # If we are capturing an answer, verify line has explicit delimiter (: or .) after digit
                if is_capturing_answer:
                    # Check if line clearly begins with question tag and separator
                    if re.match(r"^(?:Part\s+[A-Za-z0-9]+|Q(?:uestion)?\.?\s*\d+\s*[:\.\-)]|\d+\s*[\.\)]\s+)", line, re.IGNORECASE):
                        is_legit_new_q = True
                    else:
                        is_legit_new_q = False
                else:
                    is_legit_new_q = True

            if is_legit_new_q and q_match:
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
                num_extract = re.search(r"\d+", raw_id)
                current_q_num = int(num_extract.group(0)) if num_extract else (len(parsed_items) + 1)

                current_q_text = rest
                is_capturing_answer = False
                is_capturing_rubric = False

            elif ans_match:
                is_capturing_answer = True
                is_capturing_rubric = False
                ans_content = ans_match.group(1).strip()
                if ans_content:
                    current_ans_text.append(ans_content)

            elif type_match:
                current_type = type_match.group(1).strip()

            elif kw_match:
                is_capturing_answer = False
                is_capturing_rubric = False
                current_keywords = kw_match.group(1).strip()

            elif rub_match:
                is_capturing_answer = False
                is_capturing_rubric = True
                rub_str = rub_match.group(1).strip()
                if rub_str:
                    for item in re.split(r"[;]\s*", rub_str):
                        if item.strip():
                            im_search = re.search(r"(\d+(?:\.\d+)?)\s*(?:marks?|pts?|m)", item, re.IGNORECASE)
                            m_pts = float(im_search.group(1)) if im_search else 1.0
                            clean_desc = re.sub(r"(\d+(?:\.\d+)?)\s*(?:marks?|pts?|m)\s*(?:for\s*)?", "", item, flags=re.IGNORECASE).strip()
                            current_rubric_items.append(RubricItem(criterion=clean_desc or item.strip(), marks=m_pts))

            elif is_capturing_rubric:
                # Continuation of rubric items
                for item in re.split(r"[;]\s*", line):
                    if item.strip():
                        im_search = re.search(r"(\d+(?:\.\d+)?)\s*(?:marks?|pts?|m)", item, re.IGNORECASE)
                        m_pts = float(im_search.group(1)) if im_search else 1.0
                        clean_desc = re.sub(r"(\d+(?:\.\d+)?)\s*(?:marks?|pts?|m)\s*(?:for\s*)?", "", item, flags=re.IGNORECASE).strip()
                        current_rubric_items.append(RubricItem(criterion=clean_desc or item.strip(), marks=m_pts))

            elif is_capturing_answer:
                current_ans_text.append(line)

            elif current_q_text:
                current_q_text += " " + line
            else:
                unparsed_lines.append(line)

        # Commit final question
        commit_current()

        if not parsed_items:
            raise ValueError("No valid questions could be detected in the provided answer key.")

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

        # Run OCR on each page
        for p_idx, p_img_path in enumerate(page_paths):
            prep_img_path = os.path.join(upload_dir, f"prep_page_{p_idx + 1}.jpg")
            preprocess_image(p_img_path, prep_img_path)

            blocks = auto_segment_answer_blocks(prep_img_path, num_questions=2)
            for b_idx, bbox in enumerate(blocks):
                crop_path = os.path.join(upload_dir, f"crop_p{p_idx + 1}_b{b_idx + 1}.jpg")
                crop_image_region(prep_img_path, crop_path, bbox)

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
                question_type="subjective",
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
                question_type="subjective",
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
