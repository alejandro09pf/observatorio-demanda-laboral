"""
Process the 2 missing gold standard jobs with Pipeline B.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import psycopg2
from llm_processor.pipeline import LLMExtractionPipeline
from config.settings import get_settings

def main():
    settings = get_settings()

    # Initialize Pipeline B
    print("Loading Gemma 3 4B model...")
    pipeline = LLMExtractionPipeline(model_name="gemma-3-4b-instruct")

    # Connect to DB
    db_url = settings.database_url.replace('postgresql://', 'postgres://')
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Get the 2 missing jobs
    missing_job_ids = [
        '5f71bb87-71f0-48e3-9a05-f7ceab15b226',  # Data Scientist Colombia
        'ee5c8660-e6e3-4c58-99a4-a9fbc63fa83c'   # Ingeniero DevOps
    ]

    query = """
        SELECT DISTINCT
            c.job_id, c.title_cleaned, c.description_cleaned,
            c.requirements_cleaned, c.combined_text,
            r.portal, r.country
        FROM cleaned_jobs c
        JOIN raw_jobs r ON c.job_id = r.job_id
        WHERE c.job_id::text = ANY(%s)
    """

    cur.execute(query, (missing_job_ids,))
    jobs_data = cur.fetchall()
    cur.close()
    conn.close()

    if not jobs_data:
        print("❌ No jobs found")
        return

    print(f"\n✅ Found {len(jobs_data)} jobs to process\n")

    # Convert to list of dicts
    jobs = []
    for row in jobs_data:
        jobs.append({
            'job_id': row[0],
            'title': row[1],
            'description': row[2],
            'requirements': row[3],
            'combined_text': row[4],
            'portal': row[5],
            'country': row[6]
        })

    # Process each job
    for i, job in enumerate(jobs, 1):
        print(f"[{i}/{len(jobs)}] Processing: {job['title'][:60]}...")

        try:
            skills = pipeline.extract_skills_from_job(job)

            if skills:
                # Save to database
                pipeline._save_to_database(skills)
                print(f"    ✅ Extracted and saved {len(skills)} skills\n")
            else:
                print(f"    ⚠️  No skills extracted\n")

        except Exception as e:
            print(f"    ❌ Error: {e}\n")

    print("✅ Done!")

if __name__ == "__main__":
    main()
