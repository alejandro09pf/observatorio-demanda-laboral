#!/usr/bin/env python3
"""
Compare LLM Models on 10 Selected Jobs

This script compares Gemma, Llama, Qwen, and Phi models on a fixed set of 10 jobs
to justify model selection for the thesis.

Models compared:
- Gemma 3 4B Instruct (baseline - already processed)
- Llama 3.2 3B Instruct
- Qwen2.5 3B Instruct
- Phi-3 Mini 3.8B Instruct

Metrics collected:
- Precision, Recall, F1 (vs gold standard)
- Processing time per job
- Errors/failures
- Skills extracted (emergent vs ESCO)
"""

import sys
import csv
import time
import logging
import psycopg2
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from uuid import UUID

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config.settings import get_settings
from llm_processor.llm_handler import LLMHandler

def get_db_connection():
    """Get database connection using psycopg2."""
    settings = get_settings()
    db_url = settings.database_url
    # Handle postgresql:// vs postgres:// inconsistency
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')
    return psycopg2.connect(db_url)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Models to compare (Gemma already done)
MODELS_TO_TEST = [
    "llama-3.2-3b-instruct",
    "qwen2.5-3b-instruct",
    "phi-3.5-mini"
]

JOBS_CSV = "/tmp/selected_10_jobs.csv"


def load_job_ids() -> List[str]:
    """Load the 10 selected job IDs from CSV."""
    job_ids = []
    with open(JOBS_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            job_ids.append(row['job_id'])

    logger.info(f"✅ Loaded {len(job_ids)} job IDs from {JOBS_CSV}")
    return job_ids


def load_job_data(job_id: str, conn) -> Dict[str, Any]:
    """Load job data from cleaned_jobs table."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                job_id,
                title_cleaned,
                description_cleaned,
                requirements_cleaned,
                combined_text,
                combined_char_count
            FROM cleaned_jobs
            WHERE job_id = %s
        """, (job_id,))

        row = cur.fetchone()
        if not row:
            raise ValueError(f"Job {job_id} not found in cleaned_jobs")

        return {
            'job_id': str(row[0]),
            'title': row[1] or '',
            'description': row[2] or '',
            'requirements': row[3] or '',
            'combined_text': row[4],
            'char_count': row[5]
        }


def process_model(model_name: str, job_ids: List[str]) -> Dict[str, Any]:
    """Process all jobs with a specific model."""
    logger.info(f"\n{'='*80}")
    logger.info(f"🤖 Processing with model: {model_name}")
    logger.info(f"{'='*80}\n")

    settings = get_settings()
    conn = get_db_connection()

    # Initialize LLM Handler
    logger.info(f"Loading model {model_name}...")
    start_load = time.time()

    try:
        llm_handler = LLMHandler(model_name=model_name)
    except Exception as e:
        logger.error(f"❌ Failed to load model {model_name}: {e}")
        return {
            'model': model_name,
            'status': 'failed_to_load',
            'error': str(e),
            'jobs_processed': 0
        }

    load_time = time.time() - start_load
    logger.info(f"✅ Model loaded in {load_time:.2f}s\n")

    # Process each job
    results = []
    total_time = 0
    errors = 0

    for idx, job_id in enumerate(job_ids, 1):
        logger.info(f"[{idx}/10] Processing job {job_id}...")

        try:
            # Load job data
            job_data = load_job_data(job_id, conn)
            logger.info(f"  📄 Text length: {job_data['char_count']} chars")

            # Process with LLM
            start_time = time.time()
            extracted_skills = llm_handler.extract_skills(
                title=job_data['title'],
                description=job_data['description'],
                requirements=job_data['requirements']
            )
            processing_time = time.time() - start_time
            total_time += processing_time

            logger.info(f"  ✅ Extracted {len(extracted_skills)} skills in {processing_time:.2f}s")

            # Save to database
            with conn.cursor() as cur:
                for skill in extracted_skills:
                    cur.execute("""
                        INSERT INTO enhanced_skills
                        (job_id, skill_text, skill_type, llm_model, llm_confidence,
                         processing_time_seconds, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (
                        job_id,
                        skill['skill_text'],
                        skill.get('skill_type', 'unknown'),
                        model_name,
                        skill.get('confidence', 0.0),
                        processing_time
                    ))
                conn.commit()

            results.append({
                'job_id': job_id,
                'skills_count': len(extracted_skills),
                'processing_time': processing_time,
                'status': 'success'
            })

        except Exception as e:
            logger.error(f"  ❌ Error processing job {job_id}: {e}")
            errors += 1
            results.append({
                'job_id': job_id,
                'status': 'error',
                'error': str(e)
            })
            conn.rollback()

    conn.close()

    # Calculate statistics
    successful = [r for r in results if r['status'] == 'success']
    avg_time = total_time / len(successful) if successful else 0

    logger.info(f"\n{'='*80}")
    logger.info(f"📊 {model_name} Results:")
    logger.info(f"  ✅ Successful: {len(successful)}/10")
    logger.info(f"  ❌ Errors: {errors}/10")
    logger.info(f"  ⏱️  Avg time/job: {avg_time:.2f}s")
    logger.info(f"  ⏱️  Total time: {total_time:.2f}s")
    logger.info(f"{'='*80}\n")

    return {
        'model': model_name,
        'status': 'completed',
        'jobs_processed': len(successful),
        'errors': errors,
        'avg_time_per_job': avg_time,
        'total_time': total_time,
        'model_load_time': load_time,
        'results': results
    }


def generate_comparison_report(all_results: List[Dict]) -> str:
    """Generate markdown comparison report."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"data/reports/LLM_MODEL_COMPARISON_{timestamp}.md"

    report = []
    report.append("# LLM Model Comparison - 10 Jobs Test\n")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**Jobs Tested:** 10 randomly selected from gold standard\n")
    report.append(f"**Models:** Gemma 3 4B, Llama 3.2 3B, Qwen2.5 3B, Phi-3 Mini\n")
    report.append("\n---\n\n")

    # Summary Table
    report.append("## Performance Summary\n\n")
    report.append("| Model | Jobs Processed | Errors | Avg Time/Job | Total Time | Load Time |\n")
    report.append("|-------|----------------|--------|--------------|------------|----------|\n")

    for result in all_results:
        if result['status'] == 'completed':
            report.append(
                f"| {result['model']} | "
                f"{result['jobs_processed']}/10 | "
                f"{result['errors']} | "
                f"{result['avg_time_per_job']:.2f}s | "
                f"{result['total_time']:.2f}s | "
                f"{result['model_load_time']:.2f}s |\n"
            )
        else:
            report.append(f"| {result['model']} | FAILED | - | - | - | - |\n")

    report.append("\n---\n\n")
    report.append("## Next Steps\n\n")
    report.append("Run evaluation script to compare vs gold standard:\n\n")
    report.append("```bash\n")
    report.append("python scripts/evaluate_pipelines.py --mode subset \\\n")
    report.append("  --job-ids-file /tmp/selected_10_jobs.csv \\\n")
    report.append("  --pipelines " + " ".join([r['model'] for r in all_results if r['status'] == 'completed']) + " \\\n")
    report.append("  --skill-type hard\n")
    report.append("```\n")

    report_text = "".join(report)

    # Write report
    Path("data/reports").mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(report_text)

    logger.info(f"📄 Report saved to: {report_path}")
    return report_path


def main():
    """Main execution."""
    import sys

    # Check for test mode
    test_mode = len(sys.argv) > 1 and sys.argv[1] == "--test"

    logger.info("="*80)
    if test_mode:
        logger.info("🧪 LLM Model Comparison - TEST MODE (1 Job)")
    else:
        logger.info("🚀 LLM Model Comparison - 10 Jobs Test")
    logger.info("="*80)

    # Load job IDs
    all_job_ids = load_job_ids()

    # Use only first job in test mode
    job_ids = all_job_ids[:1] if test_mode else all_job_ids
    logger.info(f"📋 Processing {len(job_ids)} job(s)")

    # Check if Gemma already processed
    conn = get_db_connection()
    with conn.cursor() as cur:
        # Cast job_ids to UUID[]
        cur.execute("""
            SELECT COUNT(DISTINCT job_id)
            FROM enhanced_skills
            WHERE llm_model = 'gemma-3-4b-instruct'
              AND job_id = ANY(%s::uuid[])
        """, (job_ids,))
        gemma_count = cur.fetchone()[0]
    conn.close()

    logger.info(f"\n📊 Gemma 3 4B: {gemma_count}/10 jobs already processed")

    if gemma_count < 10:
        logger.warning(f"⚠️  Missing {10 - gemma_count} jobs for Gemma!")
        logger.info("   Run: python -m src.orchestrator process-gold-standard --model gemma-3-4b-instruct")

    # Process each new model
    all_results = []

    for model_name in MODELS_TO_TEST:
        result = process_model(model_name, job_ids)
        all_results.append(result)

        # Wait a bit between models to let GPU cool down
        if model_name != MODELS_TO_TEST[-1]:
            logger.info("⏳ Waiting 10s before next model...\n")
            time.sleep(10)

    # Generate comparison report
    report_path = generate_comparison_report(all_results)

    logger.info("\n" + "="*80)
    logger.info("✅ COMPARISON COMPLETE!")
    logger.info("="*80)
    logger.info(f"📄 Report: {report_path}")
    logger.info("\nNext: Run evaluate_pipelines.py to get Precision/Recall/F1 metrics")


if __name__ == "__main__":
    main()
