"""
Skill Validator - Validates and filters extracted skills using heuristics and LLM.
Removes noise, duplicates, and invalid skills.
"""

from typing import List, Dict, Any, Optional
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class SkillValidator:
    """Validates and filters extracted skills."""

    def __init__(self, use_llm: bool = False):
        """
        Initialize validator.

        Args:
            use_llm: Whether to use LLM for validation (more accurate but slower)
        """
        self.use_llm = use_llm
        self.blacklist = self._load_blacklist()
        self.noise_patterns = self._compile_noise_patterns()

        if use_llm:
            # Lazy import to avoid circular dependencies
            from .llm_handler import LLMHandler
            from .prompts import PromptTemplates

            self.llm = LLMHandler()
            self.prompts = PromptTemplates()

    def _load_blacklist(self) -> set[str]:
        """Load blacklisted terms that should never be considered skills."""
        # Common false positives from job postings
        blacklist = {
            # Generic terms
            "experiencia", "años", "conocimiento", "habilidad", "requisito",
            "necesario", "indispensable", "deseable", "importante",

            # Personal attributes (not technical skills)
            "responsable", "proactivo", "organizado", "puntual", "honesto",
            "compromiso", "dedicación", "actitud", "disponibilidad",

            # Legal/administrative
            "edad", "género", "raza", "nacionalidad", "visa", "pasaporte",
            "contrato", "tiempo completo", "medio tiempo", "turno",

            # Generic job terms
            "oferta", "vacante", "empleo", "trabajo", "puesto", "posición",
            "empresa", "compañía", "organización", "equipo",

            # Noise words
            "etc", "ejemplo", "incluye", "como", "entre otros",

            # Too generic soft skills (need context)
            "trabajo en equipo", "comunicación", "liderazgo",

            # Technical noise
            "http", "https", "www", ".com", "@", "email",
        }
        return {term.lower() for term in blacklist}

    def _compile_noise_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for detecting noise."""
        patterns = [
            re.compile(r'^\d+\s*(años?|meses?|días?).*$', re.IGNORECASE),  # "3 años de experiencia"
            re.compile(r'^[<>≥≤]\s*\d+', re.IGNORECASE),  # "> 5 años"
            re.compile(r'^\d+\s*-\s*\d+', re.IGNORECASE),  # "3-5 años"
            re.compile(r'^(de|en|con|para)\s+', re.IGNORECASE),  # Starts with preposition
            re.compile(r'.*@.*\.(com|net|org)', re.IGNORECASE),  # Emails
            re.compile(r'^https?://', re.IGNORECASE),  # URLs
            re.compile(r'^\$\d+', re.IGNORECASE),  # Salaries
            re.compile(r'^[\W_]+$'),  # Only special characters
            re.compile(r'^.{1,2}$'),  # Too short (1-2 chars)
            re.compile(r'^.{100,}$'),  # Too long (>100 chars)
        ]
        return patterns

    def validate_skill(
        self,
        skill: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a single skill using heuristics and optionally LLM.

        Args:
            skill: Skill text to validate
            context: Optional context (job title, description)

        Returns:
            Validation result dict
        """
        skill_clean = skill.strip()

        # Quick checks first
        if not skill_clean:
            return self._invalid_result("Empty skill")

        if len(skill_clean) < 2:
            return self._invalid_result("Too short")

        if len(skill_clean) > 100:
            return self._invalid_result("Too long")

        # Check blacklist
        skill_lower = skill_clean.lower()
        if skill_lower in self.blacklist:
            return self._invalid_result("Blacklisted term")

        # Check noise patterns
        for pattern in self.noise_patterns:
            if pattern.match(skill_clean):
                return self._invalid_result(f"Matches noise pattern: {pattern.pattern}")

        # Heuristic checks passed
        heuristic_result = {
            "is_valid": True,
            "confidence": 0.7,  # Moderate confidence from heuristics alone
            "method": "heuristic",
            "reason": "Passed heuristic checks",
            "suggested_correction": None
        }

        # Use LLM for higher confidence validation if enabled
        if self.use_llm and context:
            try:
                llm_result = self._validate_with_llm(skill_clean, context)
                # Combine heuristic + LLM results
                return {
                    **llm_result,
                    "heuristic_passed": True,
                    "method": "heuristic+llm"
                }
            except Exception as e:
                logger.warning(f"LLM validation failed: {e}")
                return heuristic_result

        return heuristic_result

    def _validate_with_llm(self, skill: str, context: str) -> Dict[str, Any]:
        """Validate skill using LLM."""
        prompt = self.prompts.get_prompt(
            "validate_skill",
            skill_text=skill,
            context=context
        )

        response = self.llm.generate_json(prompt, temperature=0.1)

        if "parsed_json" in response:
            return response["parsed_json"]
        else:
            raise ValueError(f"Failed to parse LLM validation response: {response.get('error')}")

    def _invalid_result(self, reason: str) -> Dict[str, Any]:
        """Create invalid result dict."""
        return {
            "is_valid": False,
            "confidence": 0.95,
            "method": "heuristic",
            "reason": reason,
            "suggested_correction": None,
            "category": "invalid"
        }

    def validate_skills(
        self,
        skills: List[str],
        context: Optional[str] = None,
        batch_size: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Validate multiple skills.

        Args:
            skills: List of skill texts
            context: Optional context
            batch_size: Process in batches (for LLM efficiency)

        Returns:
            List of validation results
        """
        results = []

        for skill in skills:
            result = self.validate_skill(skill, context)
            result["skill"] = skill
            results.append(result)

        return results

    def filter_valid_skills(
        self,
        skills: List[Dict[str, Any]],
        min_confidence: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Filter skills to keep only valid ones.

        Args:
            skills: List of skill dicts with 'skill_text' key
            min_confidence: Minimum confidence threshold

        Returns:
            Filtered list of valid skills
        """
        valid_skills = []

        for skill_data in skills:
            skill_text = skill_data.get('skill_text', skill_data.get('skill', ''))

            validation = self.validate_skill(skill_text)

            if validation["is_valid"] and validation["confidence"] >= min_confidence:
                # Add validation info to skill data
                skill_data["validation"] = validation
                valid_skills.append(skill_data)
            else:
                logger.debug(
                    f"Filtered out skill: '{skill_text}' "
                    f"(reason: {validation['reason']})"
                )

        logger.info(
            f"Filtered {len(skills)} skills → {len(valid_skills)} valid "
            f"({len(valid_skills)/len(skills)*100:.1f}%)"
        )

        return valid_skills

    def deduplicate_skills(
        self,
        skills: List[Dict[str, Any]],
        use_llm: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate skills (case-insensitive, ignores punctuation).

        Args:
            skills: List of skill dicts
            use_llm: Use LLM for semantic deduplication (more accurate)

        Returns:
            Deduplicated list
        """
        if not skills:
            return []

        # Simple deduplication (normalize case + punctuation)
        seen = {}
        deduplicated = []

        for skill_data in skills:
            skill_text = skill_data.get('skill_text', skill_data.get('skill', ''))
            normalized = self._normalize_for_dedup(skill_text)

            if normalized not in seen:
                seen[normalized] = skill_data
                deduplicated.append(skill_data)
            else:
                # Keep the one with higher confidence if available
                existing_conf = seen[normalized].get('confidence_score', 0)
                new_conf = skill_data.get('confidence_score', 0)

                if new_conf > existing_conf:
                    # Replace with higher confidence version
                    deduplicated.remove(seen[normalized])
                    seen[normalized] = skill_data
                    deduplicated.append(skill_data)

        logger.info(f"Deduplicated {len(skills)} → {len(deduplicated)} skills")

        # TODO: Implement LLM-based semantic deduplication
        # This would catch "Python" vs "Python programming" vs "Python 3"

        return deduplicated

    def _normalize_for_dedup(self, text: str) -> str:
        """Normalize text for deduplication."""
        # Remove punctuation, lowercase, remove extra spaces
        normalized = re.sub(r'[^\w\s]', '', text.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def get_validation_statistics(
        self,
        validation_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate validation statistics."""
        total = len(validation_results)
        valid = sum(1 for r in validation_results if r.get("is_valid"))
        invalid = total - valid

        categories = {}
        for result in validation_results:
            category = result.get("category", "unknown")
            categories[category] = categories.get(category, 0) + 1

        return {
            "total": total,
            "valid": valid,
            "invalid": invalid,
            "valid_percentage": valid / total * 100 if total > 0 else 0,
            "categories": categories,
            "avg_confidence": sum(
                r.get("confidence", 0) for r in validation_results
            ) / total if total > 0 else 0
        } 