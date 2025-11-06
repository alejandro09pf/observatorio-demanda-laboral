"""
LLM Extraction Pipeline (Pipeline B) - Direct skill extraction using LLM.
Parallel to Pipeline A (NER+Regex+ESCO).
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import uuid
import time

from llm_processor.llm_handler import LLMHandler
from llm_processor.prompts import PromptTemplates
from extractor.esco_matcher_3layers import ESCOMatcher3Layers
from config.settings import get_settings

logger = logging.getLogger(__name__)


class LLMExtractionPipeline:
    """
    Pipeline B: Extract skills directly from job ads using LLM.

    This is a parallel extraction method to Pipeline A (NER+Regex).
    Goal: Compare which method produces better results against gold standard.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        use_structured_output: bool = False
    ):
        """
        Initialize LLM extraction pipeline.

        Args:
            model_name: LLM model to use (from model_registry)
            use_structured_output: Use structured JSON with categories
        """
        self.settings = get_settings()
        self.llm = LLMHandler(model_name=model_name)
        self.prompts = PromptTemplates()
        self.esco_matcher = ESCOMatcher3Layers()  # ESCO mapping (same as Pipeline A)
        self.use_structured_output = use_structured_output

        logger.info(f"✅ LLM Extraction Pipeline initialized")
        logger.info(f"   Model: {self.llm.model_name}")
        logger.info(f"   Backend: {self.llm.backend}")
        logger.info(f"   ESCO matching: enabled")

    def extract_skills_from_job(
        self,
        job_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract skills from a job posting using LLM.

        This is the main entry point - equivalent to Pipeline A's extract_skills_from_job().

        Args:
            job_data: Job data dict with keys: job_id, title, description, requirements, country

        Returns:
            List of extracted skills with metadata
        """
        job_id = job_data.get('job_id')
        title = job_data.get('title', '')
        description = job_data.get('description', '')
        requirements = job_data.get('requirements', '')
        country = job_data.get('country', 'CO')

        logger.info(f"🤖 [Pipeline B - LLM] Extracting skills from job: {job_id}")
        logger.info(f"   Title: {title[:60]}...")

        # Start timing
        start_time = time.time()

        # Combine job text (no truncation - use full combined_text from cleaned_jobs)
        # Models have enough context: Gemma 8K, Llama 128K, Qwen 32K, Mistral 32K
        full_description = self.prompts.format_job_description(
            title=title,
            description=description,
            requirements=requirements,
            max_length=None  # No truncation - use model's full context
        )

        logger.info(f"   Combined text: {len(full_description)} characters")

        # Extract skills with LLM
        extraction_result = self._extract_with_llm(
            job_title=title,
            job_description=full_description,
            country=country
        )

        # Extract results
        extracted_skills = extraction_result.get('skills', [])
        tokens_used = extraction_result.get('tokens_used', 0)

        # Calculate processing time
        processing_time = time.time() - start_time

        logger.info(f"   ✅ Extracted {len(extracted_skills)} skills with LLM")
        logger.info(f"   ⏱️  Processing time: {processing_time:.2f}s | Tokens: {tokens_used}")

        # Add job_id and metadata (including new fields for migration 009)
        for skill in extracted_skills:
            skill['job_id'] = job_id
            skill['extraction_method'] = f'llm_{self.llm.model_name}'
            skill['extraction_timestamp'] = datetime.now()
            skill['processing_time_seconds'] = processing_time
            skill['tokens_used'] = tokens_used

        return extracted_skills

    def _extract_with_llm(
        self,
        job_title: str,
        job_description: str,
        country: str
    ) -> Dict[str, Any]:
        """
        Call LLM to extract skills.

        Args:
            job_title: Job title
            job_description: Full job description
            country: Country code

        Returns:
            Dict with 'skills' (list) and 'tokens_used' (int)
        """
        # Choose prompt template
        if self.use_structured_output:
            template_name = "extract_skills_structured"
            prompt = self.prompts.get_prompt(
                template_name,
                job_title=job_title,
                job_description=job_description,
                country=country
            )
        else:
            template_name = "extract_skills"
            prompt = self.prompts.get_prompt(
                template_name,
                job_title=job_title,
                job_description=job_description
            )

        logger.debug(f"Prompt length: {len(prompt)} characters")

        # Call LLM with increased max_tokens to avoid truncation
        try:
            response = self.llm.generate_json(
                prompt,
                temperature=0.3,  # Low temp for deterministic extraction
                max_tokens=3072  # Increased from 1024 to handle longer responses
            )

            if "parsed_json" not in response:
                logger.error(f"Failed to parse LLM response: {response.get('error')}")
                return {"skills": [], "tokens_used": 0}

            json_data = response["parsed_json"]

            # Check if response was truncated
            finish_reason = response.get('finish_reason', 'unknown')
            tokens_used = response.get('tokens_used', 0)

            if finish_reason == 'length':
                logger.warning(f"⚠️  Response was truncated (hit max_tokens limit)")
                logger.warning(f"   Tokens used: {tokens_used}/3072")
                logger.warning(f"   Consider increasing max_tokens or using smaller model")

            # Parse response based on format
            skills = self._parse_llm_response(json_data)

            logger.info(f"   LLM returned {len(skills)} skills")
            logger.debug(f"   Tokens used: {tokens_used} | Finish: {finish_reason}")

            # Map skills to ESCO taxonomy (same as Pipeline A)
            skills = self._add_esco_mapping(skills)

            return {"skills": skills, "tokens_used": tokens_used}

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {"skills": [], "tokens_used": 0}

    def _parse_llm_response(
        self,
        json_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Parse LLM JSON response into skill list.

        Args:
            json_data: Parsed JSON from LLM

        Returns:
            List of skill dicts
        """
        skills = []

        if self.use_structured_output:
            # Structured format: {"programming_languages": [...], "frameworks": [...]}
            for category, skill_list in json_data.items():
                for skill_text in skill_list:
                    skills.append({
                        "skill_text": skill_text,
                        "skill_type": category,
                        "confidence": 0.9,  # High confidence from LLM
                        "llm_model": self.llm.model_name
                    })
        else:
            # New format: {"hard_skills": [...], "soft_skills": [...]}
            hard_skills = json_data.get("hard_skills", [])
            soft_skills = json_data.get("soft_skills", [])

            # Add hard skills
            for skill_text in hard_skills:
                skills.append({
                    "skill_text": skill_text,
                    "skill_type": "hard",
                    "confidence": 0.9,
                    "llm_model": self.llm.model_name
                })

            # Add soft skills
            for skill_text in soft_skills:
                skills.append({
                    "skill_text": skill_text,
                    "skill_type": "soft",
                    "confidence": 0.9,
                    "llm_model": self.llm.model_name
                })

        return skills

    def _add_esco_mapping(
        self,
        skills: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Map extracted skills to ESCO taxonomy using ESCOMatcher3Layers.

        Args:
            skills: List of skill dicts from LLM

        Returns:
            Same skills list with ESCO fields added
        """
        if not skills:
            return skills

        # Extract skill texts for batch matching
        skill_texts = [s["skill_text"] for s in skills]

        # Batch match to ESCO (same as Pipeline A)
        logger.info(f"   Mapping {len(skill_texts)} skills to ESCO taxonomy...")
        esco_matches = self.esco_matcher.batch_match_skills(skill_texts)

        # Add ESCO data to each skill
        esco_matched_count = 0
        emergent_count = 0

        for skill in skills:
            skill_text = skill["skill_text"]
            esco_match = esco_matches.get(skill_text)

            if esco_match:
                # ESCO match found
                skill["esco_concept_uri"] = esco_match.esco_skill_uri
                skill["esco_preferred_label"] = esco_match.matched_skill_text
                skill["esco_confidence"] = esco_match.confidence_score
                skill["esco_match_method"] = esco_match.match_method
                esco_matched_count += 1
            else:
                # Emergent skill (no ESCO match)
                skill["esco_concept_uri"] = None
                skill["esco_preferred_label"] = None
                skill["esco_confidence"] = 0.0
                skill["esco_match_method"] = "emergent"
                emergent_count += 1

        match_rate = (esco_matched_count / len(skills) * 100) if skills else 0
        logger.info(f"   ESCO matches: {esco_matched_count}/{len(skills)} ({match_rate:.1f}%)")
        logger.info(f"   Emergent skills: {emergent_count}")

        return skills

    def process_batch(
        self,
        jobs: List[Dict[str, Any]],
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Process multiple jobs through LLM extraction pipeline.

        Args:
            jobs: List of job dicts
            save_to_db: Whether to save results to database

        Returns:
            Processing statistics
        """
        logger.info(f"🚀 Starting LLM batch processing: {len(jobs)} jobs")

        total_skills = 0
        successful = 0
        failed = 0
        all_results = []

        for i, job in enumerate(jobs, 1):
            job_id = job.get('job_id')

            try:
                logger.info(f"[{i}/{len(jobs)}] Processing job: {job_id}")

                skills = self.extract_skills_from_job(job)

                if save_to_db and skills:
                    self._save_to_database(skills)

                all_results.extend(skills)
                total_skills += len(skills)
                successful += 1

                if i % 10 == 0:
                    logger.info(f"   Progress: {i}/{len(jobs)} jobs, {total_skills} skills total")

            except Exception as e:
                logger.error(f"Failed to process job {job_id}: {e}")
                failed += 1

        logger.info(f"✅ Batch processing complete:")
        logger.info(f"   Jobs processed: {successful}/{len(jobs)}")
        logger.info(f"   Total skills extracted: {total_skills}")
        logger.info(f"   Avg skills/job: {total_skills/successful if successful > 0 else 0:.1f}")

        return {
            "total_jobs": len(jobs),
            "successful": successful,
            "failed": failed,
            "total_skills": total_skills,
            "avg_skills_per_job": total_skills / successful if successful > 0 else 0,
            "results": all_results
        }

    def _save_to_database(self, skills: List[Dict[str, Any]]):
        """
        Save extracted skills to enhanced_skills table.

        Args:
            skills: List of skill dicts to save
        """
        try:
            import psycopg2
            from psycopg2.extras import execute_values

            # Get DB connection
            db_url = self.settings.database_url
            if db_url.startswith('postgresql://'):
                db_url = db_url.replace('postgresql://', 'postgres://')

            conn = psycopg2.connect(db_url)
            cur = conn.cursor()

            # Prepare data for insertion
            values = []
            for skill in skills:
                # Build llm_reasoning with ESCO match info
                llm_model = skill.get('llm_model', 'unknown')
                esco_method = skill.get('esco_match_method', 'none')
                esco_conf = skill.get('esco_confidence', 0.0)

                if esco_method == 'emergent':
                    reasoning = f"Extracted by {llm_model} | Emergent skill (no ESCO match)"
                else:
                    reasoning = f"Extracted by {llm_model} | ESCO: {esco_method} (conf: {esco_conf:.2f})"

                values.append((
                    str(uuid.uuid4()),  # enhancement_id
                    skill.get('job_id'),  # job_id
                    skill.get('skill_text'),  # original_skill_text
                    skill.get('skill_text'),  # normalized_skill (same as original for LLM)
                    skill.get('skill_type', 'hard'),  # skill_type (hard or soft)
                    skill.get('esco_concept_uri'),  # esco_concept_uri (from ESCO matcher)
                    skill.get('esco_preferred_label'),  # esco_preferred_label
                    skill.get('confidence', 0.9),  # llm_confidence
                    reasoning,  # llm_reasoning (includes ESCO match info)
                    False,  # is_duplicate
                    None,  # duplicate_of_id
                    llm_model,  # llm_model
                    skill.get('processing_time_seconds'),  # processing_time_seconds (migration 009)
                    skill.get('tokens_used'),  # tokens_used (migration 009)
                    esco_method  # esco_match_method (migration 009)
                ))

            # Insert all skills (with migration 009 metadata)
            insert_query = """
                INSERT INTO enhanced_skills (
                    enhancement_id, job_id, original_skill_text, normalized_skill,
                    skill_type, esco_concept_uri, esco_preferred_label,
                    llm_confidence, llm_reasoning, is_duplicate, duplicate_of_id, llm_model,
                    processing_time_seconds, tokens_used, esco_match_method
                ) VALUES %s
            """

            execute_values(cur, insert_query, values)
            conn.commit()

            logger.debug(f"   💾 Saved {len(skills)} skills to database")

            cur.close()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to save skills to database: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        return self.llm.get_model_info()
