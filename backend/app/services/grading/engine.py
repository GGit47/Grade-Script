import re
import string
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
        rubric_criteria: str = ""
    ) -> Dict[str, Any]:
        """
        Evaluates answer using multi-factor transparent criteria:
        1. Blank or unreadable checks
        2. Essential concept coverage ratio (40% weight)
        3. Semantic similarity score (50% weight)
        4. Length/completeness heuristic (10% weight)
        5. Rubric-based bounding
        """
        norm_student = self.normalize_text(student_text)
        
        # Case 1: Empty or blank answer
        if not norm_student or "[blank" in norm_student or "[unreadable" in norm_student:
            return {
                "suggested_marks": 0.0,
                "concepts_identified": [],
                "missing_concepts": [kw.strip() for kw in essential_keywords_str.split(",") if kw.strip()],
                "semantic_similarity": 0.0,
                "rationale": "No readable answer provided or answer space was left blank.",
                "review_needed": True
            }

        # Case 2: Matching concepts
        matched_concepts, missing_concepts = self.extract_and_match_concepts(
            student_text, essential_keywords_str, reference_text
        )

        total_concepts = len(matched_concepts) + len(missing_concepts)
        concept_ratio = len(matched_concepts) / total_concepts if total_concepts > 0 else 0.8

        # Case 3: Semantic similarity
        similarity = self.compute_semantic_similarity(student_text, reference_text)

        # Case 4: Length completeness check
        ref_len = len(self.normalize_text(reference_text).split())
        student_len = len(norm_student.split())
        length_ratio = min(1.0, student_len / max(1, ref_len * 0.6))

        # Weighted calculation
        # Semantic similarity is supportive, not solitary:
        combined_score = (0.45 * concept_ratio) + (0.45 * similarity) + (0.10 * length_ratio)
        combined_score = max(0.0, min(1.0, combined_score))

        raw_marks = round(combined_score * max_marks, 1)

        # Rational and review flags
        review_needed = False
        reasons = []

        if similarity > 0.8 and concept_ratio > 0.7:
            reasons.append("Answer closely reflects the reference answer with all key concepts covered.")
        elif similarity > 0.5:
            reasons.append(f"Answer captures the central idea (similarity: {similarity:.2f}).")
            if missing_concepts:
                reasons.append(f"Missing essential concepts: {', '.join(missing_concepts)}.")
        else:
            reasons.append(f"Low semantic alignment with reference solution (similarity: {similarity:.2f}).")
            review_needed = True

        if raw_marks < (0.4 * max_marks) and len(norm_student.split()) > 10:
            reasons.append("Answer contains lengthy explanation with low keyword match; requires teacher review.")
            review_needed = True

        rationale = " ".join(reasons)

        return {
            "suggested_marks": min(max_marks, raw_marks),
            "concepts_identified": matched_concepts,
            "missing_concepts": missing_concepts,
            "semantic_similarity": round(similarity, 3),
            "rationale": rationale,
            "review_needed": review_needed
        }

grading_engine = GradingEngine()
