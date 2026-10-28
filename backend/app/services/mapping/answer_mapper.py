import re
import json
from typing import List, Dict, Any, Optional, Tuple
import logging

from app.models.entities import Question
from app.services.grading.engine import grading_engine

logger = logging.getLogger(__name__)

class AnswerMapper:
    """
    Intelligently maps each student handwritten answer region to the correct reference question
    regardless of answer order, supporting explicit identifiers, semantic compatibility,
    subquestion awareness, and ambiguity detection.
    """

    @staticmethod
    def extract_detected_identifier(text: str) -> Tuple[Optional[str], Optional[int], Optional[str], str]:
        """
        Inspects the recognized text (especially the first few lines) for question identifiers.
        Returns:
            (normalized_label, numeric_id, subquestion_id, cleaned_body_text)
        Examples:
            "Q3. Gradient descent is an optimization..." -> ("Q3", 3, None, "Gradient descent is...")
            "1(a) Supervised learning is..." -> ("Q1(a)", 1, "a", "Supervised learning is...")
            "Ans 2: Overfitting occurs..." -> ("Q2", 2, None, "Overfitting occurs...")
        """
        if not text:
            return None, None, None, ""

        lines = text.strip().splitlines()
        first_line = lines[0].strip() if lines else ""

        # Pattern 1: Q1, Q.1, Question 1, Q1(a), Q2b, Ans 1, Ans: 1
        # Subquestion identifier must be in parens (e.g. (a), (1), (i)) or single letter right after digit
        p1 = re.match(
            r"^(?:Q(?:uestion)?|Ans(?:wer)?)\.?\s*(\d+)(?:\s*(?:\(([a-zA-Z0-9]{1,3})\)|([a-zA-Z]))(?=\s*[:\.\-]|\s|$))?\s*[:\.\-]?\s*(.*)$",
            first_line,
            re.IGNORECASE
        )
        if p1:
            q_num = int(p1.group(1))
            sub_id = p1.group(2) or p1.group(3)
            rest = p1.group(4) or ""
            norm_label = f"Q{q_num}({sub_id})" if sub_id else f"Q{q_num}"
            remaining_text = "\n".join([rest] + lines[1:]).strip()
            return norm_label, q_num, sub_id, remaining_text

        # Pattern 2: 1., 1), 1(a), 2(b) at start of text
        p2 = re.match(
            r"^(\d+)\s*(?:(?:\(([a-zA-Z0-9]{1,3})\))|([a-zA-Z])(?=\s*[:\.\-]|\s|$)|[\.\)])\s*[:\.\-]?\s*(.*)$",
            first_line
        )
        if p2:
            q_num = int(p2.group(1))
            sub_id = p2.group(2) or p2.group(3)
            rest = p2.group(4) or ""
            norm_label = f"Q{q_num}({sub_id})" if sub_id else f"Q{q_num}"
            remaining_text = "\n".join([rest] + lines[1:]).strip()
            return norm_label, q_num, sub_id, remaining_text

        return None, None, None, text

    @classmethod
    def match_regions_to_questions(
        cls,
        regions: List[Dict[str, Any]],
        questions: List[Question]
    ) -> List[Dict[str, Any]]:
        """
        Performs order-independent multi-signal matching between all student answer regions
        and reference questions.
        """
        if not questions or not regions:
            return []

        results = []
        score_matrix = []

        for r_idx, reg in enumerate(regions):
            raw_text = reg.get("text", "")
            det_label, num_id, sub_id, cleaned_text = cls.extract_detected_identifier(raw_text)

            candidates_for_reg = []

            for q_idx, q in enumerate(questions):
                score = 0.0
                reasons = []

                # Signal A: Explicit question identifier matching
                has_explicit_match = False
                if det_label:
                    norm_det = det_label.upper()
                    ref_label = (q.question_label or f"Q{q.question_number}").upper()
                    
                    if norm_det == ref_label or norm_det == f"Q{q.question_number}" or (num_id == q.question_number and not sub_id):
                        score += 0.90
                        reasons.append(f"Explicit identifier match '{det_label}'")
                        has_explicit_match = True
                    elif num_id == q.question_number and sub_id:
                        if sub_id.lower() in (q.question_label or "").lower():
                            score += 0.95
                            reasons.append(f"Subquestion identifier match '{det_label}'")
                            has_explicit_match = True
                        else:
                            score += 0.40
                            reasons.append(f"Parent question match '{q.question_number}', different subquestion")

                # Signal B: Semantic question prompt matching
                content_text = cleaned_text or raw_text
                if content_text and q.question_text:
                    sim_q = grading_engine.compute_semantic_similarity(content_text[:120], q.question_text)
                    if sim_q > 0.30:
                        score += (sim_q * 0.40)
                        reasons.append(f"Prompt semantic similarity ({sim_q:.2f})")

                # Signal C: Answer-content semantic compatibility
                if content_text and q.reference_answer:
                    sim_ans = grading_engine.compute_semantic_similarity(content_text, q.reference_answer)
                    matched_kws, _ = grading_engine.extract_and_match_concepts(
                        content_text, q.essential_keywords or "", q.reference_answer
                    )
                    kw_boost = min(0.35, len(matched_kws) * 0.12)
                    content_score = (sim_ans * 0.45) + kw_boost
                    score += content_score
                    if sim_ans > 0.30:
                        reasons.append(f"Answer semantic match ({sim_ans:.2f})")
                    if matched_kws:
                        reasons.append(f"Matched concepts ({', '.join(matched_kws[:3])})")

                final_score = min(1.0, max(0.0, score))
                reason_str = "; ".join(reasons) if reasons else "Low semantic correlation"

                candidates_for_reg.append({
                    "question_id": q.id,
                    "question_label": q.question_label or f"Q{q.question_number}",
                    "question_number": q.question_number,
                    "score": round(final_score, 3),
                    "reason": reason_str,
                    "has_explicit": has_explicit_match
                })

            candidates_for_reg.sort(key=lambda x: x["score"], reverse=True)
            score_matrix.append(candidates_for_reg)

        assigned_q_ids = set()
        mapping_decisions = [None] * len(regions)
        
        # Step 1: High-confidence explicit matches take precedence
        for r_idx in range(len(regions)):
            candidates = score_matrix[r_idx]
            top_cand = candidates[0] if candidates else None
            if top_cand and top_cand["has_explicit"] and top_cand["score"] >= 0.70:
                mapping_decisions[r_idx] = {
                    "question_id": top_cand["question_id"],
                    "confidence": top_cand["score"],
                    "method": "explicit_label",
                    "candidates": candidates,
                    "is_ambiguous": False
                }
                assigned_q_ids.add(top_cand["question_id"])

        # Step 2: Assign remaining regions using best candidate
        for r_idx in range(len(regions)):
            if mapping_decisions[r_idx] is not None:
                continue

            candidates = score_matrix[r_idx]
            if not candidates:
                continue

            unassigned_cands = [c for c in candidates if c["question_id"] not in assigned_q_ids]
            top_cand = unassigned_cands[0] if unassigned_cands else candidates[0]
            
            is_ambiguous = False
            if len(candidates) > 1:
                diff = candidates[0]["score"] - candidates[1]["score"]
                if diff < 0.10 and candidates[0]["score"] < 0.70:
                    is_ambiguous = True

            method = "semantic" if top_cand["score"] > 0.15 else "unmatched"
            assigned_id = top_cand["question_id"] if top_cand["score"] > 0.10 else None
            if assigned_id:
                assigned_q_ids.add(assigned_id)

            mapping_decisions[r_idx] = {
                "question_id": assigned_id,
                "confidence": top_cand["score"],
                "method": method if assigned_id else "unmatched",
                "candidates": candidates[:4],
                "is_ambiguous": is_ambiguous
            }

        # Step 3: Check for duplicate question assignments across regions
        q_count = {}
        for r_idx, dec in enumerate(mapping_decisions):
            if dec and dec["question_id"]:
                qid = dec["question_id"]
                q_count[qid] = q_count.get(qid, 0) + 1

        for r_idx, dec in enumerate(mapping_decisions):
            if dec and dec["question_id"] and q_count.get(dec["question_id"], 0) > 1:
                dec["is_ambiguous"] = True
                dec["method"] = "duplicate_detected"

        for r_idx, reg in enumerate(regions):
            raw_text = reg.get("text", "")
            det_label, _, _, cleaned_text = cls.extract_detected_identifier(raw_text)
            dec = mapping_decisions[r_idx]

            results.append({
                "region_id": reg.get("id"),
                "assigned_question_id": dec["question_id"] if dec else None,
                "detected_label": det_label,
                "cleaned_text": cleaned_text or raw_text,
                "mapping_confidence": dec["confidence"] if dec else 0.0,
                "mapping_method": dec["method"] if dec else "unmatched",
                "candidate_matches": dec["candidates"] if dec else [],
                "is_ambiguous": dec["is_ambiguous"] if dec else False
            })

        return results

answer_mapper = AnswerMapper()
