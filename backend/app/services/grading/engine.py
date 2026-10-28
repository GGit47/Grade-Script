import re
import string
import json
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class GradingEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GradingEngine, cls).__new__(cls)
            cls._instance.embedder = None
            cls._instance._embedder_loaded = False
        return cls._instance

    def load_embedder(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        if self._embedder_loaded:
            return
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading SentenceTransformer '{model_name}'...")
            self.embedder = SentenceTransformer(model_name)
            self._embedder_loaded = True
            logger.info("SentenceTransformer loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer: {e}. Fallback grading active.")
            self._embedder_loaded = False

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.lower()
        # Remove punctuation
        text = text.translate(str.maketrans("", "", string.punctuation))
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def compute_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Calculates cosine similarity between student answer and reference answer.
        """
        norm1 = self.normalize_text(text1)
        norm2 = self.normalize_text(text2)
        if not norm1 or not norm2:
            return 0.0

        if self._embedder_loaded and self.embedder is not None:
            try:
                from sentence_transformers import util
                emb1 = self.embedder.encode(norm1, convert_to_tensor=True)
                emb2 = self.embedder.encode(norm2, convert_to_tensor=True)
                cos_sim = util.cos_sim(emb1, emb2).item()
                return max(0.0, min(1.0, float(cos_sim)))
            except Exception as e:
                logger.error(f"Semantic similarity calculation error: {e}")

        # Fallback: Jaccard similarity between word sets
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return float(len(intersection) / len(union)) if union else 0.0

    def extract_and_match_concepts(
        self, student_text: str, essential_keywords_str: str, reference_text: str
    ) -> Tuple[List[str], List[str]]:
        """
        Identifies presence and absence of essential concepts/keywords.
        """
        normalized_student = self.normalize_text(student_text)
        
        # Parse essential keywords
        keywords: List[str] = []
        if essential_keywords_str:
            for kw in essential_keywords_str.replace(";", ",").split(","):
                clean = kw.strip().lower()
                if clean:
                    keywords.append(clean)

        # If no explicit keywords given, extract key content words from reference answer
        if not keywords and reference_text:
            ref_words = self.normalize_text(reference_text).split()
            # Filter stop words
            stopwords = {"the", "is", "at", "which", "on", "a", "an", "and", "or", "to", "in", "for", "with", "as", "by", "that", "it", "of"}
            keywords = list(dict.fromkeys([w for w in ref_words if len(w) > 3 and w not in stopwords]))[:6]

        matched = []
        missing = []

        for kw in keywords:
            # Check for substring match or word match
            if kw in normalized_student:
                matched.append(kw)
            else:
                missing.append(kw)

        return matched, missing

    def evaluate_answer(
        self,
        student_text: str,
        reference_text: str,
        max_marks: float,
        essential_keywords_str: str = "",
        rubric_criteria: str = "",
        alternative_answers_str: str = "",
        negative_marking: float = 0.0,
        question_type: str = "subjective"
    ) -> Dict[str, Any]:
        """
        Evaluates answer using multi-factor transparent criteria:
        1. Blank or unreadable checks
        2. MCQ option matching for multiple-choice questions
        3. Essential concept coverage ratio (40% weight)
        4. Semantic similarity score (50% weight) - checks primary reference answer and acceptable alternatives
        5. Length/completeness heuristic (10% weight)
        6. Rubric-based partial-credit allocation if structured criteria configured
        7. Optional negative marking penalty for incorrect/unanswered questions
        """
        raw_lower = (student_text or "").lower()
        norm_student = self.normalize_text(student_text)

        # Check if question is an MCQ
        is_mcq = (question_type.lower() == "mcq") or bool(
            re.match(r"^[A-Fa-f]$", reference_text.strip())
            or re.match(r"^\([A-Fa-f]\)$", reference_text.strip())
        )

        if is_mcq:
            # Case MCQ Blank / Empty
            if (
                not norm_student
                or "[blank" in raw_lower
                or "[unreadable" in raw_lower
                or norm_student.startswith("blank")
                or norm_student.startswith("unreadable")
            ):
                ref_clean = reference_text.strip().upper()
                msg = f"Unanswered: No student answer detected for this MCQ (expected '{ref_clean}')."
                return {
                    "suggested_marks": 0.0,
                    "concepts_identified": [],
                    "missing_concepts": [f"Option {ref_clean}"],
                    "semantic_similarity": 0.0,
                    "rationale": msg,
                    "feedback": msg,
                    "review_needed": True,
                    "rubric_scores": []
                }

            # Extract student option letter
            opt_match = re.search(r"(?:^|[\s\(\[\:\.\-])([A-Fa-f])(?:[\)\]\.\s\:\-]|$)", student_text.strip())
            if not opt_match:
                words = re.findall(r"\b[A-Fa-f]\b", student_text.strip())
                student_opt = words[0].upper() if words else student_text.strip().upper()
            else:
                student_opt = opt_match.group(1).upper()

            ref_match = re.search(r"\b([A-Fa-f])\b", reference_text.strip())
            ref_opt = ref_match.group(1).upper() if ref_match else reference_text.strip().upper()

            if student_opt == ref_opt:
                msg = f"Correct MCQ option selected: {ref_opt} (matches reference '{ref_opt}')."
                return {
                    "suggested_marks": max_marks,
                    "concepts_identified": [f"Option {ref_opt}"],
                    "missing_concepts": [],
                    "semantic_similarity": 1.0,
                    "rationale": msg,
                    "feedback": msg,
                    "review_needed": False,
                    "rubric_scores": [
                        {
                            "criterion": f"Correct MCQ option ({ref_opt})",
                            "max_marks": max_marks,
                            "awarded_marks": max_marks,
                            "satisfied": True
                        }
                    ]
                }
            else:
                penalized = -abs(negative_marking) if negative_marking > 0 else 0.0
                msg = f"Incorrect MCQ option: selected '{student_opt}', does not match reference '{ref_opt}'."
                return {
                    "suggested_marks": penalized,
                    "concepts_identified": [],
                    "missing_concepts": [f"Option {ref_opt}"],
                    "semantic_similarity": 0.0,
                    "rationale": msg,
                    "feedback": msg,
                    "review_needed": False,
                    "rubric_scores": [
                        {
                            "criterion": f"Correct MCQ option ({ref_opt})",
                            "max_marks": max_marks,
                            "awarded_marks": 0.0,
                            "satisfied": False
                        }
                    ]
                }
        
        # Case 1: Empty or blank answer (Subjective)
        if (
            not norm_student
            or "[blank" in raw_lower
            or "[unreadable" in raw_lower
            or norm_student.startswith("blank")
            or norm_student.startswith("unreadable")
        ):
            kws = [kw.strip() for kw in essential_keywords_str.split(",") if kw.strip()]
            blank_msg = "No readable answer provided or answer space was left blank."
            return {
                "suggested_marks": 0.0,
                "concepts_identified": [],
                "missing_concepts": kws,
                "semantic_similarity": 0.0,
                "rationale": blank_msg,
                "feedback": blank_msg,
                "review_needed": True,
                "rubric_scores": []
            }

        # Case 2: Check similarity with reference answer AND any acceptable alternative answers
        primary_sim = self.compute_semantic_similarity(student_text, reference_text)
        best_sim = primary_sim
        matched_alt = None

        if alternative_answers_str:
            alt_list = []
            if alternative_answers_str.startswith("["):
                try:
                    alt_list = json.loads(alternative_answers_str)
                except Exception:
                    alt_list = [a.strip() for a in alternative_answers_str.split(";") if a.strip()]
            else:
                alt_list = [a.strip() for a in alternative_answers_str.split(";") if a.strip()]

            for alt in alt_list:
                if alt:
                    alt_sim = self.compute_semantic_similarity(student_text, alt)
                    if alt_sim > best_sim:
                        best_sim = alt_sim
                        matched_alt = alt

        # Case 3: Matching concepts
        matched_concepts, missing_concepts = self.extract_and_match_concepts(
            student_text, essential_keywords_str, reference_text
        )

        total_concepts = len(matched_concepts) + len(missing_concepts)
        concept_ratio = len(matched_concepts) / total_concepts if total_concepts > 0 else 0.8

        # Case 4: Length completeness check
        ref_len = len(self.normalize_text(reference_text).split())
        student_len = len(norm_student.split())
        length_ratio = min(1.0, student_len / max(1, ref_len * 0.5))

        # Case 5: Evaluate Structured Rubric Criteria
        structured_rubric = []
        if rubric_criteria:
            try:
                if rubric_criteria.strip().startswith("["):
                    structured_rubric = json.loads(rubric_criteria)
            except Exception:
                structured_rubric = []

        rubric_scores = []
        rubric_awarded_total = 0.0
        used_rubric_scoring = False

        if structured_rubric and isinstance(structured_rubric, list):
            used_rubric_scoring = True
            for r_item in structured_rubric:
                c_text = r_item.get("criterion", "")
                c_max = float(r_item.get("marks", 1.0))
                
                # Check semantic alignment of student text with this specific criterion
                c_sim = self.compute_semantic_similarity(student_text, c_text)
                
                # Also check keyword presence in student text
                c_words = [w for w in self.normalize_text(c_text).split() if len(w) > 3]
                c_word_hits = sum(1 for w in c_words if w in norm_student)
                c_word_ratio = (c_word_hits / len(c_words)) if c_words else 0.5

                c_score_ratio = (0.6 * c_sim) + (0.4 * c_word_ratio)
                satisfied = c_score_ratio >= 0.38 or best_sim >= 0.70

                if best_sim >= 0.80:
                    awarded = c_max
                elif satisfied:
                    fraction = min(1.0, c_score_ratio * 1.3)
                    awarded = round(fraction * c_max, 1)
                else:
                    awarded = 0.0

                rubric_scores.append({
                    "criterion": c_text,
                    "max_marks": c_max,
                    "awarded_marks": min(c_max, awarded),
                    "satisfied": satisfied
                })
                rubric_awarded_total += awarded

        # Determine suggested score
        if used_rubric_scoring and rubric_scores:
            raw_marks = min(max_marks, rubric_awarded_total)
        else:
            # Combined holistic score
            combined_score = (0.45 * concept_ratio) + (0.45 * best_sim) + (0.10 * length_ratio)
            combined_score = max(0.0, min(1.0, combined_score))
            raw_marks = round(combined_score * max_marks, 1)

        # Apply negative marking penalty if configured and student score is low
        if negative_marking > 0 and best_sim < 0.20 and len(matched_concepts) == 0:
            raw_marks = max(0.0, round(raw_marks - negative_marking, 1))

        # Rational and review flags
        review_needed = False
        reasons = []

        if matched_alt:
            reasons.append(f"Answer matches configured alternative reference solution (similarity: {best_sim:.2f}).")
        elif best_sim > 0.8 and concept_ratio > 0.7:
            reasons.append("Answer closely reflects the reference answer with key concepts covered.")
        elif best_sim > 0.5:
            reasons.append(f"Answer captures the central idea (similarity: {best_sim:.2f}).")
            if missing_concepts:
                reasons.append(f"Missing essential concepts: {', '.join(missing_concepts)}.")
        else:
            reasons.append(f"Low semantic alignment with reference solution (similarity: {best_sim:.2f}).")
            review_needed = True

        if raw_marks < (0.4 * max_marks) and len(norm_student.split()) > 10:
            reasons.append("Answer contains lengthy explanation with low keyword match; requires teacher check.")
            review_needed = True

        rationale = " ".join(reasons)

        return {
            "suggested_marks": min(max_marks, max(0.0, raw_marks)),
            "concepts_identified": matched_concepts,
            "missing_concepts": missing_concepts,
            "semantic_similarity": round(best_sim, 3),
            "rationale": rationale,
            "feedback": rationale,
            "review_needed": review_needed,
            "rubric_scores": rubric_scores
        }

grading_engine = GradingEngine()
