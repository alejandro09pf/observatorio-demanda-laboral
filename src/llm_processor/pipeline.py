"""
LLM Extraction Pipeline (Pipeline B) - Direct skill extraction using LLM.
Parallel to Pipeline A (NER+Regex+ESCO).
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import uuid

from llm_processor.llm_handler import LLMHandler
from llm_processor.prompts import PromptTemplates
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
        self.use_structured_output = use_structured_output

        logger.info(f"✅ LLM Extraction Pipeline initialized")
        logger.info(f"   Model: {self.llm.model_name}")
        logger.info(f"   Backend: {self.llm.backend}")

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
        extracted_skills = self._extract_with_llm(
            job_title=title,
            job_description=full_description,
            country=country
        )

        logger.info(f"   ✅ Extracted {len(extracted_skills)} skills with LLM")

        # Add job_id and metadata
        for skill in extracted_skills:
            skill['job_id'] = job_id
            skill['extraction_method'] = f'llm_{self.llm.model_name}'
            skill['extraction_timestamp'] = datetime.now()

        return extracted_skills

    def _extract_with_llm(
        self,
        job_title: str,
        job_description: str,
        country: str
    ) -> List[Dict[str, Any]]:
        """
        Call LLM to extract skills.

        Args:
            job_title: Job title
            job_description: Full job description
            country: Country code

        Returns:
            List of skill dicts
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
                return []

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

            return skills

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return []

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
            # Simple format: {"skills": [...]}
            skill_list = json_data.get("skills", [])
            for skill_text in skill_list:
                skills.append({
                    "skill_text": skill_text,
                    "skill_type": "technical",  # Generic type
                    "confidence": 0.9,
                    "llm_model": self.llm.model_name
                })

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
                values.append((
                    str(uuid.uuid4()),  # enhancement_id
                    skill.get('job_id'),  # job_id
                    skill.get('skill_text'),  # original_skill_text
                    skill.get('skill_text'),  # normalized_skill (same as original for LLM)
                    skill.get('skill_type', 'technical'),  # skill_type
                    None,  # esco_concept_uri (can add ESCO matching later)
                    None,  # esco_preferred_label
                    skill.get('confidence', 0.9),  # llm_confidence
                    f"Extracted by {skill.get('llm_model')}",  # llm_reasoning
                    False,  # is_duplicate
                    None,  # duplicate_of_id
                    skill.get('llm_model')  # llm_model
                ))

            # Insert all skills
            insert_query = """
                INSERT INTO enhanced_skills (
                    enhancement_id, job_id, original_skill_text, normalized_skill,
                    skill_type, esco_concept_uri, esco_preferred_label,
                    llm_confidence, llm_reasoning, is_duplicate, duplicate_of_id, llm_model
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
