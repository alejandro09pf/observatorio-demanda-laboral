from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass
from datetime import datetime
import psycopg2
from .ner_extractor import NERExtractor, NERSkill
from .regex_patterns import RegexExtractor, RegexSkill
from .esco_matcher_3layers import ESCOMatcher3Layers as ESCOMatcher, ESCOMatch
from config.settings import get_settings

logger = logging.getLogger(__name__)

@dataclass
class ExtractedSkillResult:
    """Final result of skill extraction with ESCO mapping."""
    skill_text: str
    extraction_method: str
    original_confidence: float
    esco_match: Optional[ESCOMatch]
    final_confidence: float
    skill_type: str
    context: str
    context_position: tuple
    extraction_timestamp: datetime

class ExtractionPipeline:
    """Orchestrates skill extraction using multiple methods."""
    
    def __init__(self):
        logger.info("Initializing Extraction Pipeline...")
        
        # Initialize extractors
        self.ner_extractor = NERExtractor()
        self.regex_extractor = RegexExtractor()
        self.esco_matcher = ESCOMatcher()
        
        # Get database connection
        self.settings = get_settings()
        self.db_url = self.settings.database_url
        if self.db_url.startswith('postgresql://'):
            self.db_url = self.db_url.replace('postgresql://', 'postgres://')
        
        logger.info("✅ Extraction Pipeline initialized successfully")
    
    def extract_skills_from_job(self, job_data: Dict[str, Any]) -> List[ExtractedSkillResult]:
        """Extract skills from a job posting using all methods."""
        job_id = job_data.get('job_id')

        # Use combined_text from cleaned_jobs if available, otherwise fallback to raw text
        combined_text = job_data.get('combined_text')
        if combined_text:
            full_text = combined_text
            logger.info(f"🔍 Starting skill extraction for job: {job_id}")
            logger.info(f"   Using cleaned combined_text ({len(full_text)} characters)")
        else:
            # Fallback: manually combine raw fields
            title = job_data.get('title', '')
            description = job_data.get('description', '')
            requirements = job_data.get('requirements', '')

            logger.info(f"🔍 Starting skill extraction for job: {job_id}")
            logger.info(f"   Title: {title[:50]}...")
            logger.info(f"   Description length: {len(description)} characters")
            logger.info(f"   Requirements length: {len(requirements)} characters")

            full_text = f"{title}\n{description}\n{requirements}".strip()
            logger.warning(f"⚠️  No cleaned_text found for job {job_id}, using raw text")
        
        # Step 1: Extract skills with regex
        logger.info("📋 Step 1: Regex-based skill extraction...")
        regex_skills = self.regex_extractor.extract_skills(full_text)
        logger.info(f"   Found {len(regex_skills)} skills with regex")
        
        # Step 2: Extract skills with NER
        logger.info("🧠 Step 2: NER-based skill extraction...")
        ner_skills = self.ner_extractor.extract_skills(full_text)
        logger.info(f"   Found {len(ner_skills)} skills with NER")
        
        # Step 3: Combine and deduplicate skills
        logger.info("🔄 Step 3: Combining and deduplicating skills...")
        all_skills = self._combine_skills(regex_skills, ner_skills)
        logger.info(f"   Combined into {len(all_skills)} unique skills")
        
        # Step 4: Map skills to ESCO
        logger.info("🗺️ Step 4: Mapping skills to ESCO taxonomy...")
        skill_texts = [skill.skill_text for skill in all_skills]
        esco_matches = self.esco_matcher.batch_match_skills(skill_texts)
        
        # Step 5: Create final results
        logger.info("✨ Step 5: Creating final extraction results...")
        results = []
        for skill in all_skills:
            esco_match = esco_matches.get(skill.skill_text)
            
            # Calculate final confidence
            final_confidence = self._calculate_final_confidence(
                skill.confidence, 
                esco_match.confidence_score if esco_match else 0.0
            )
            
            result = ExtractedSkillResult(
                skill_text=skill.skill_text,
                extraction_method=skill.extraction_method,
                original_confidence=skill.confidence,
                esco_match=esco_match,
                final_confidence=final_confidence,
                skill_type='hard',  # Pipeline A extracts only hard/technical skills
                context=skill.context,
                context_position=skill.position,
                extraction_timestamp=datetime.now()
            )
            results.append(result)
        
        logger.info(f"🎯 Extraction completed: {len(results)} skills extracted and mapped")
        return results
    
    def process_batch(self, batch_size: int = 10) -> Dict[str, Any]:
        """Process a batch of jobs for skill extraction."""
        import time
        import statistics

        logger.info(f"🚀 Starting batch processing (batch size: {batch_size})")

        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()

                # Get extraction-ready jobs (usable + cleaned + pending)
                # This view filters for is_usable=TRUE automatically, excluding junk jobs
                cursor.execute("""
                    SELECT job_id, title_cleaned, description_cleaned,
                           requirements_cleaned, combined_text, portal, country,
                           combined_word_count
                    FROM extraction_ready_jobs
                    ORDER BY scraped_at ASC
                    LIMIT %s
                """, (batch_size,))

                pending_jobs = cursor.fetchall()
                logger.info(f"📊 Found {len(pending_jobs)} extraction-ready jobs (cleaned, usable, pending)")

                if not pending_jobs:
                    logger.info("No pending jobs found")
                    return {'processed': 0, 'success': 0, 'errors': 0}

                # Initialize timing metrics
                batch_start_time = time.time()
                job_times = []

                # Process each job
                results = {
                    'processed': len(pending_jobs),
                    'success': 0,
                    'errors': 0,
                    'total_skills': 0,
                    'esco_matches': 0,
                    'job_details': []
                }

                for idx, job_data in enumerate(pending_jobs, 1):
                    try:
                        # Start timing for this job
                        job_start_time = time.time()

                        # Mark as processing
                        cursor.execute("""
                            UPDATE raw_jobs
                            SET extraction_status = 'processing',
                                extraction_attempts = extraction_attempts + 1
                            WHERE job_id = %s
                        """, (job_data[0],))

                        # Extract skills using cleaned data
                        job_dict = {
                            'job_id': job_data[0],
                            'title': job_data[1],  # title_cleaned
                            'description': job_data[2],  # description_cleaned
                            'requirements': job_data[3],  # requirements_cleaned
                            'combined_text': job_data[4],  # pre-computed combined clean text
                            'portal': job_data[5],
                            'country': job_data[6],
                            'word_count': job_data[7]  # combined_word_count
                        }

                        extracted_skills = self.extract_skills_from_job(job_dict)

                        # Save extracted skills to database
                        self._save_extracted_skills(cursor, job_data[0], extracted_skills)

                        # Calculate job processing time
                        job_time = time.time() - job_start_time
                        job_times.append(job_time)

                        # Mark as completed
                        cursor.execute("""
                            UPDATE raw_jobs
                            SET extraction_status = 'completed',
                                extraction_completed_at = NOW()
                            WHERE job_id = %s
                        """, (job_data[0],))

                        # Update results
                        results['success'] += 1
                        results['total_skills'] += len(extracted_skills)
                        results['esco_matches'] += sum(1 for s in extracted_skills if s.esco_match)

                        job_result = {
                            'job_id': job_data[0],
                            'title': job_data[1][:50] + '...',
                            'skills_extracted': len(extracted_skills),
                            'esco_matches': sum(1 for s in extracted_skills if s.esco_match),
                            'processing_time': job_time
                        }
                        results['job_details'].append(job_result)

                        logger.info(f"✅ Job {job_data[0]}: {len(extracted_skills)} skills extracted ({job_time:.2f}s)")

                        # Progress report every 500 jobs
                        if idx % 500 == 0:
                            elapsed_time = time.time() - batch_start_time
                            avg_time = elapsed_time / idx
                            eta_seconds = avg_time * (len(pending_jobs) - idx)

                            logger.info("")
                            logger.info(f"📊 PROGRESS REPORT - Batch {idx}/{len(pending_jobs)}")
                            logger.info(f"   Progress: {idx/len(pending_jobs)*100:.1f}% complete")
                            logger.info(f"   Speed: {avg_time:.2f}s/job")
                            logger.info(f"   ETA: {eta_seconds/60:.1f} minutes ({eta_seconds/3600:.1f} hours)")
                            logger.info(f"   Success rate: {results['success']}/{idx} ({results['success']/idx*100:.1f}%)")
                            logger.info(f"   Avg skills/job: {results['total_skills']/results['success']:.1f}")
                            logger.info("")
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing job {job_data[0]}: {e}")
                        
                        # Mark as failed
                        cursor.execute("""
                            UPDATE raw_jobs 
                            SET extraction_status = 'failed',
                                extraction_error = %s
                            WHERE job_id = %s
                        """, (str(e), job_data[0]))
                        
                        results['errors'] += 1
                
                conn.commit()

                # Calculate final timing statistics
                total_time = time.time() - batch_start_time

                # Add timing metrics to results
                if job_times:
                    results['timing'] = {
                        'total_time_seconds': total_time,
                        'total_time_minutes': total_time / 60,
                        'total_time_hours': total_time / 3600,
                        'avg_time_per_job': statistics.mean(job_times),
                        'median_time_per_job': statistics.median(job_times),
                        'min_time_per_job': min(job_times),
                        'max_time_per_job': max(job_times),
                        'std_dev_time': statistics.stdev(job_times) if len(job_times) > 1 else 0
                    }

                # Log comprehensive summary
                logger.info("")
                logger.info("=" * 80)
                logger.info("🎉 BATCH PROCESSING COMPLETED")
                logger.info("=" * 80)
                logger.info(f"Jobs processed: {results['success']} success, {results['errors']} errors")
                logger.info(f"Total skills extracted: {results['total_skills']}")
                logger.info(f"ESCO matches: {results['esco_matches']} ({results['esco_matches']/results['total_skills']*100:.1f}%)")
                logger.info(f"Emergent skills: {results['total_skills'] - results['esco_matches']} ({(results['total_skills']-results['esco_matches'])/results['total_skills']*100:.1f}%)")
                logger.info(f"Avg skills/job: {results['total_skills']/results['success']:.1f}")

                if job_times:
                    logger.info("")
                    logger.info("⏱️  TIMING METRICS")
                    logger.info(f"Total time: {total_time/60:.2f} min ({total_time/3600:.2f} hours)")
                    logger.info(f"Avg time/job: {statistics.mean(job_times):.2f}s")
                    logger.info(f"Median time/job: {statistics.median(job_times):.2f}s")
                    logger.info(f"Min time/job: {min(job_times):.2f}s")
                    logger.info(f"Max time/job: {max(job_times):.2f}s")
                    logger.info(f"Std deviation: {statistics.stdev(job_times) if len(job_times) > 1 else 0:.2f}s")

                logger.info("=" * 80)
                logger.info("")

                return results
                
        except Exception as e:
            logger.error(f"❌ Batch processing failed: {e}")
            return {'error': str(e)}
    
    def _combine_skills(self, regex_skills: List[RegexSkill], ner_skills: List[NERSkill]) -> List[Any]:
        """Combine skills from different extractors and remove duplicates."""
        combined = []
        seen_texts = set()
        
        # Add regex skills first (higher confidence)
        for skill in regex_skills:
            normalized = skill.skill_text.lower().strip()
            if normalized not in seen_texts:
                seen_texts.add(normalized)
                combined.append(skill)
        
        # Add NER skills (avoiding duplicates)
        for skill in ner_skills:
            normalized = skill.skill_text.lower().strip()
            if normalized not in seen_texts:
                seen_texts.add(normalized)
                combined.append(skill)
        
        return combined
    
    def _calculate_final_confidence(self, extraction_confidence: float, esco_confidence: float) -> float:
        """Calculate final confidence score combining extraction and ESCO matching."""
        # Weight: 70% extraction confidence, 30% ESCO matching confidence
        return (extraction_confidence * 0.7) + (esco_confidence * 0.3)
    
    def _save_extracted_skills(self, cursor, job_id: str, skills: List[ExtractedSkillResult]):
        """Save extracted skills to the database."""
        for skill in skills:
            cursor.execute("""
                INSERT INTO extracted_skills (
                    job_id, skill_text, extraction_method, confidence_score, 
                    skill_type, source_section, span_start, span_end, esco_uri
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                job_id,
                skill.skill_text,
                skill.extraction_method,
                skill.final_confidence,
                skill.skill_type,
                skill.context[:50] if skill.context else None,  # Truncate to fit source_section
                skill.context_position[0] if hasattr(skill, 'context_position') else None,
                skill.context_position[1] if hasattr(skill, 'context_position') else None,
                skill.esco_match.esco_skill_uri if skill.esco_match else None
            ))
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get statistics about the extraction pipeline."""
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()
                
                # Get job status counts
                cursor.execute("""
                    SELECT extraction_status, COUNT(*) as count
                    FROM raw_jobs 
                    GROUP BY extraction_status
                """)
                
                status_counts = dict(cursor.fetchall())
                
                # Get skill extraction counts
                cursor.execute("""
                    SELECT COUNT(*) as total_skills,
                           COUNT(DISTINCT job_id) as jobs_with_skills
                    FROM extracted_skills
                """)
                
                skill_stats = cursor.fetchone()
                
                return {
                    'job_status': status_counts,
                    'total_skills_extracted': skill_stats[0] if skill_stats else 0,
                    'jobs_with_skills': skill_stats[1] if skill_stats else 0,
                    'extraction_pipeline_ready': True
                }
                
        except Exception as e:
            logger.error(f"Error getting extraction stats: {e}")
            return {'error': str(e)} 