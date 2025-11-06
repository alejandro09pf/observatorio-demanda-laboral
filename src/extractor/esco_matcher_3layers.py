"""
ESCO Matcher with 3-Layer Strategy

Layer 1: Exact Match (SQL ILIKE) → Confidence 1.00
Layer 2: Fuzzy Match (fuzzywuzzy) → Confidence based on ratio (threshold 0.85)
Layer 3: Semantic Match (FAISS) → DISABLED (E5 model not suitable for tech vocabulary)

If all active layers fail → emergent_skill (no ESCO match)

NOTE: Layer 3 is disabled after extensive testing showed E5 multilingual embeddings
      produce absurd matches for technical vocabulary. See docs/FAISS_ANALYSIS_AND_RECOMMENDATION.md
"""

import psycopg2
from typing import List, Dict, Any, Optional, Tuple
import logging
import pickle
import numpy as np
import faiss
from pathlib import Path
from fuzzywuzzy import fuzz
from sentence_transformers import SentenceTransformer
from dataclasses import dataclass

from config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ESCOMatch:
    """Represents an ESCO skill match with detailed matching info."""
    skill_text: str  # Original extracted skill text
    matched_skill_text: str  # ESCO preferred label that matched
    esco_skill_uri: str  # ESCO URI
    confidence_score: float  # 0.0-1.0
    match_method: str  # 'exact', 'fuzzy', 'semantic'
    esco_skill_name: str  # Same as matched_skill_text (for compatibility)
    skill_type: str  # From ESCO database
    skill_group: str  # From ESCO database


class ESCOMatcher3Layers:
    """Match skills to ESCO taxonomy using 3-layer strategy."""

    # Thresholds (optimized after extensive testing + Experimento #1)
    # Increased from 0.85 to 0.92 to eliminate absurd matches like "REST"→"restaurar dentaduras"
    FUZZY_THRESHOLD = 0.92  # Was 0.85 (2025-01-05 - Mejora 1.3)
    SEMANTIC_THRESHOLD = 0.87  # Not used when Layer 3 disabled

    # Adaptive threshold for very short strings (≤4 chars)
    # Short strings like "REST", "CI", "IT" require stricter matching
    FUZZY_THRESHOLD_SHORT = 0.95  # For strings ≤4 chars

    # Layer 3 Control Flag
    LAYER3_ENABLED = False  # DISABLED: E5 model not suitable for technical vocabulary (see FAISS_ANALYSIS_AND_RECOMMENDATION.md)

    def __init__(self):
        self.settings = get_settings()
        self.db_url = self.settings.database_url
        if self.db_url.startswith('postgresql://'):
            self.db_url = self.db_url.replace('postgresql://', 'postgres://')

        # Load FAISS index for semantic matching (Layer 3)
        self._load_faiss_index()
        logger.info("✅ ESCOMatcher3Layers initialized")

    def _load_faiss_index(self):
        """Load FAISS index and skill mapping for semantic search."""
        # Skip loading FAISS if Layer 3 is disabled
        if not self.LAYER3_ENABLED:
            logger.info("Layer 3 (semantic matching) is DISABLED - skipping FAISS index load")
            self.faiss_index = None
            self.skill_texts = None
            self.model = None
            return

        index_path = Path(__file__).parent.parent.parent / "data" / "embeddings" / "esco.faiss"
        mapping_path = Path(__file__).parent.parent.parent / "data" / "embeddings" / "esco_mapping.pkl"

        if not index_path.exists() or not mapping_path.exists():
            logger.warning("FAISS index not found. Semantic matching (Layer 3) disabled.")
            logger.warning(f"Expected paths:\n  {index_path}\n  {mapping_path}")
            self.faiss_index = None
            self.skill_texts = None
            self.model = None
            return

        try:
            # Load FAISS index
            self.faiss_index = faiss.read_index(str(index_path))

            # Load skill text mapping
            with open(mapping_path, 'rb') as f:
                self.skill_texts = pickle.load(f)

            # Load embedding model
            self.model = SentenceTransformer('intfloat/multilingual-e5-base')

            logger.info(f"✅ Loaded FAISS index with {len(self.skill_texts):,} skills")
            logger.info(f"   Semantic matching (Layer 3) enabled")

        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            self.faiss_index = None
            self.skill_texts = None
            self.model = None

    def match_skill(self, skill_text: str) -> Optional[ESCOMatch]:
        """
        Match a single skill using 3-layer strategy.

        Returns:
            ESCOMatch if any layer succeeds, None if all layers fail (emergent skill)
        """
        if not skill_text or len(skill_text.strip()) < 2:
            return None

        skill_text = skill_text.strip()

        # Layer 1: Exact Match
        match = self._layer1_exact_match(skill_text)
        if match:
            return match

        # Layer 2: Fuzzy Match
        match = self._layer2_fuzzy_match(skill_text)
        if match:
            return match

        # Layer 3: Semantic Match (FAISS) - DISABLED
        if self.LAYER3_ENABLED:
            match = self._layer3_semantic_match(skill_text)
            if match:
                return match

        # All active layers failed → emergent skill
        return None

    def batch_match_skills(self, skill_texts: List[str]) -> Dict[str, Optional[ESCOMatch]]:
        """
        Match multiple skills in batch.

        Returns:
            Dict mapping skill_text → ESCOMatch (or None if no match)
        """
        results = {}

        for skill_text in skill_texts:
            match = self.match_skill(skill_text)
            results[skill_text] = match

        return results

    def _layer1_exact_match(self, skill_text: str) -> Optional[ESCOMatch]:
        """
        Layer 1: Exact match using SQL ILIKE (case-insensitive).
        Confidence: 1.00 (perfect match)
        """
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()

                # Search in both Spanish and English labels
                cursor.execute("""
                    SELECT skill_uri, preferred_label_es, preferred_label_en, skill_type, skill_group
                    FROM esco_skills
                    WHERE is_active = TRUE
                      AND (LOWER(preferred_label_es) = LOWER(%s)
                           OR LOWER(preferred_label_en) = LOWER(%s))
                    LIMIT 1
                """, (skill_text, skill_text))

                result = cursor.fetchone()

                if result:
                    uri, label_es, label_en, skill_type, skill_group = result

                    # Use Spanish label if available, otherwise English
                    matched_label = label_es if label_es else label_en

                    return ESCOMatch(
                        skill_text=skill_text,
                        matched_skill_text=matched_label,
                        esco_skill_uri=uri,
                        confidence_score=1.00,  # Perfect match
                        match_method='exact',
                        esco_skill_name=matched_label,
                        skill_type=skill_type or 'unknown',
                        skill_group=skill_group or 'unknown'
                    )

        except Exception as e:
            logger.error(f"Layer 1 error for '{skill_text}': {e}")

        return None

    def _layer2_fuzzy_match(self, skill_text: str) -> Optional[ESCOMatch]:
        """
        Layer 2: Fuzzy match using fuzzywuzzy.
        Threshold: 0.85 (85% similarity)
        Confidence: Based on fuzz.ratio (0.85-1.00)

        Strategy:
        1. First, get candidates via SQL (skills containing any word from search term)
        2. Run fuzzy matching on candidates only (much faster)
        3. If no candidates found, search all skills (fallback)
        """
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()

                # Extract words from skill text for SQL filtering
                words = [w.strip() for w in skill_text.lower().split() if len(w.strip()) >= 2]

                # Build SQL filter for candidates
                if words:
                    # Look for skills containing ANY of the words
                    like_conditions = []
                    params = []
                    for word in words:
                        like_conditions.append("(LOWER(preferred_label_es) LIKE %s OR LOWER(preferred_label_en) LIKE %s)")
                        params.extend([f'%{word}%', f'%{word}%'])

                    where_clause = " OR ".join(like_conditions)

                    cursor.execute(f"""
                        SELECT skill_uri, preferred_label_es, preferred_label_en, skill_type, skill_group
                        FROM esco_skills
                        WHERE is_active = TRUE
                          AND ({where_clause})
                        LIMIT 1000
                    """, params)

                    candidates = cursor.fetchall()

                    # If no candidates, fall back to all skills
                    if not candidates:
                        cursor.execute("""
                            SELECT skill_uri, preferred_label_es, preferred_label_en, skill_type, skill_group
                            FROM esco_skills
                            WHERE is_active = TRUE
                        """)
                        candidates = cursor.fetchall()
                else:
                    # No words to filter, search all
                    cursor.execute("""
                        SELECT skill_uri, preferred_label_es, preferred_label_en, skill_type, skill_group
                        FROM esco_skills
                        WHERE is_active = TRUE
                    """)
                    candidates = cursor.fetchall()

                best_match = None
                best_score = 0.0
                best_match_starts_with = False  # Tiebreaker: prefer matches at start

                for uri, label_es, label_en, skill_type, skill_group in candidates:
                    # Try Spanish label
                    if label_es:
                        # Use max of ratio and partial_ratio to handle both:
                        # - Full matches (ratio)
                        # - Substring matches like "ML" in "ML (programación informática)" (partial_ratio)
                        score_ratio = fuzz.ratio(skill_text.lower(), label_es.lower()) / 100.0
                        score_partial = fuzz.partial_ratio(skill_text.lower(), label_es.lower()) / 100.0

                        # CRITICAL FIX (2025-01-05 - Mejora 1.3.1):
                        # For very short strings (≤4 chars), partial_ratio causes absurd matches:
                        #   "REST" → "RESTaurar dentaduras" (partial_ratio = 1.00)
                        #   "CI" → "CIsco Webex" (partial_ratio = 1.00)
                        #
                        # Strategy:
                        # - Skills ≤4 chars: ONLY use ratio (NO partial_ratio) - prevents substring abuse
                        # - Skills 5-6 chars: Allow partial_ratio (valid use case: "React" in "React.js")
                        # - Skills >6 chars: Only ratio (full string comparison)
                        if len(skill_text) <= 4:
                            # Very short: strict exact matching only
                            score = score_ratio
                        elif len(label_es) > len(skill_text) and len(skill_text) <= 6:
                            # Medium short: allow partial (e.g., "React" in "React Native")
                            score = max(score_ratio, score_partial)
                        else:
                            # Normal/long: ratio only
                            score = score_ratio

                        # Tiebreaker: if same score, prefer match at start of label
                        starts_with = label_es.lower().startswith(skill_text.lower())
                        if score > best_score or (score == best_score and starts_with and not best_match_starts_with):
                            best_score = score
                            best_match = (uri, label_es, skill_type, skill_group)
                            best_match_starts_with = starts_with

                    # Try English label
                    if label_en:
                        score_ratio = fuzz.ratio(skill_text.lower(), label_en.lower()) / 100.0
                        score_partial = fuzz.partial_ratio(skill_text.lower(), label_en.lower()) / 100.0

                        # Same strategy as Spanish labels (Mejora 1.3.1)
                        if len(skill_text) <= 4:
                            score = score_ratio  # Very short: NO partial_ratio
                        elif len(label_en) > len(skill_text) and len(skill_text) <= 6:
                            score = max(score_ratio, score_partial)
                        else:
                            score = score_ratio

                        starts_with = label_en.lower().startswith(skill_text.lower())
                        if score > best_score or (score == best_score and starts_with and not best_match_starts_with):
                            best_score = score
                            best_match = (uri, label_en, skill_type, skill_group)
                            best_match_starts_with = starts_with

                # Adaptive threshold: stricter for short strings (≤4 chars)
                # This prevents absurd matches like "REST"→"restaurar dentaduras" or "IT"→"italiano"
                effective_threshold = self.FUZZY_THRESHOLD_SHORT if len(skill_text) <= 4 else self.FUZZY_THRESHOLD

                if best_match and best_score >= effective_threshold:
                    uri, matched_label, skill_type, skill_group = best_match

                    return ESCOMatch(
                        skill_text=skill_text,
                        matched_skill_text=matched_label,
                        esco_skill_uri=uri,
                        confidence_score=round(best_score, 3),
                        match_method='fuzzy',
                        esco_skill_name=matched_label,
                        skill_type=skill_type or 'unknown',
                        skill_group=skill_group or 'unknown'
                    )

        except Exception as e:
            logger.error(f"Layer 2 error for '{skill_text}': {e}")

        return None

    def _validate_semantic_match(self, extracted_skill: str, matched_skill: str) -> bool:
        """
        Validate if semantic match makes sense - ONLY reject OBVIOUSLY absurd matches.

        Strategy: Reject only if BOTH conditions are true:
        1. Length difference is extreme (< 20% similarity)
        2. Domains are completely different (tech vs non-tech)

        This allows valid cross-language semantic matches while filtering nonsense.
        """
        extracted_lower = extracted_skill.lower()
        matched_lower = matched_skill.lower()

        # Extract words (minimum 2 chars)
        extracted_words = set(w for w in extracted_lower.split() if len(w) >= 2)
        matched_words = set(w for w in matched_lower.split() if len(w) >= 2)

        # Quick pass: If they share ANY common word → automatically valid
        common_words = extracted_words & matched_words
        if len(common_words) > 0:
            return True

        # Check 1: Length similarity (extreme difference = suspicious)
        len_ratio = min(len(extracted_skill), len(matched_skill)) / max(len(extracted_skill), len(matched_skill), 1)
        extreme_length_diff = len_ratio < 0.2  # Very strict: only flag if < 20% similar

        # Check 2: Tech domain check
        tech_keywords = [
            'python', 'java', 'script', 'data', 'code', 'dev', 'software', 'system',
            'cloud', 'api', 'web', 'mobile', 'database', 'server', 'network',
            'machine', 'learning', 'ai', 'ml', 'framework', 'library', 'tool',
            'devops', 'infrastructure', 'engineer'
        ]

        extracted_is_tech = any(kw in extracted_lower for kw in tech_keywords)
        matched_is_tech = any(kw in matched_lower for kw in tech_keywords)
        domain_mismatch = extracted_is_tech != matched_is_tech

        # Reject ONLY if BOTH conditions are met (extreme length diff AND domain mismatch)
        if extreme_length_diff and domain_mismatch:
            return False

        # Otherwise: trust the FAISS threshold (0.85)
        return True

    def _layer3_semantic_match(self, skill_text: str) -> Optional[ESCOMatch]:
        """
        Layer 3: Semantic match using FAISS + multilingual-e5-base embeddings.
        Threshold: 0.75 (cosine similarity)
        Confidence: Based on cosine similarity (0.75-1.00)
        """
        if not self.faiss_index or not self.model:
            return None  # FAISS not loaded

        try:
            # Generate embedding for query
            query_embedding = self.model.encode([skill_text], normalize_embeddings=True, convert_to_numpy=True)

            # Search in FAISS (k=5 for top 5 matches)
            distances, indices = self.faiss_index.search(query_embedding.astype(np.float32), k=5)

            # Best match
            best_score = float(distances[0][0])  # Cosine similarity (higher = better)
            best_idx = int(indices[0][0])

            if best_score >= self.SEMANTIC_THRESHOLD:
                # Get skill text from mapping
                matched_skill_text = self.skill_texts[best_idx]

                # Get full info from database
                with psycopg2.connect(self.db_url) as conn:
                    cursor = conn.cursor()

                    cursor.execute("""
                        SELECT skill_uri, skill_type, skill_group
                        FROM esco_skills
                        WHERE (preferred_label_es = %s OR preferred_label_en = %s)
                          AND is_active = TRUE
                        LIMIT 1
                    """, (matched_skill_text, matched_skill_text))

                    result = cursor.fetchone()

                    if result:
                        uri, skill_type, skill_group = result

                        # Validate semantic match before returning
                        if not self._validate_semantic_match(skill_text, matched_skill_text):
                            logger.debug(f"Semantic match rejected: '{skill_text}' → '{matched_skill_text}' (validation failed)")
                            return None

                        return ESCOMatch(
                            skill_text=skill_text,
                            matched_skill_text=matched_skill_text,
                            esco_skill_uri=uri,
                            confidence_score=round(best_score, 3),
                            match_method='semantic',
                            esco_skill_name=matched_skill_text,
                            skill_type=skill_type or 'unknown',
                            skill_group=skill_group or 'unknown'
                        )

        except Exception as e:
            logger.error(f"Layer 3 error for '{skill_text}': {e}")

        return None

    def get_matching_stats(self, matches: Dict[str, Optional[ESCOMatch]]) -> Dict[str, Any]:
        """Get statistics about matching results."""
        total = len(matches)
        matched = sum(1 for m in matches.values() if m is not None)
        emergent = total - matched

        # Count by method
        exact_count = sum(1 for m in matches.values() if m and m.match_method == 'exact')
        fuzzy_count = sum(1 for m in matches.values() if m and m.match_method == 'fuzzy')
        semantic_count = sum(1 for m in matches.values() if m and m.match_method == 'semantic')

        return {
            'total_skills': total,
            'matched': matched,
            'match_rate': matched / total if total > 0 else 0.0,
            'emergent_skills': emergent,
            'emergent_rate': emergent / total if total > 0 else 0.0,
            'by_method': {
                'exact': exact_count,
                'fuzzy': fuzzy_count,
                'semantic': semantic_count
            }
        }
