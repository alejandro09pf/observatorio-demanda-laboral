"""
Process the 2 problematic gold standard jobs with adjusted parameters:
- Lower temperature (0.1 vs 0.3) to reduce repetitions
- Higher max_tokens (4096 vs 3072) for more space
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import psycopg2
from llm_processor.llm_handler import LLMHandler
from llm_processor.prompts import PromptTemplates
from llm_processor.pipeline import LLMExtractionPipeline
from config.settings import get_settings
import time
import uuid

def main():
    settings = get_settings()

    # Initialize components
    print("Loading Gemma 3 4B model...")
    llm = LLMHandler(model_name="gemma-3-4b-instruct")
    prompts = PromptTemplates()

    # We'll use the pipeline's ESCO matcher
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

    print(f"\n✅ Found {len(jobs_data)} jobs to process")
    print(f"🌡️  Temperature: 0.1 (reduced from 0.3)")
    print(f"🔢 Max tokens: 4096 (increased from 3072)\n")

    # Process each job
    for i, row in enumerate(jobs_data, 1):
        job_id = row[0]
        title = row[1]
        description = row[2]
        requirements = row[3]
        combined_text = row[4]
        portal = row[5]
        country = row[6]

        print(f"[{i}/{len(jobs_data)}] Processing: {title[:60]}...")
        print(f"   Text length: {len(combined_text)} chars")

        try:
            # Start timing
            start_time = time.time()

            # Format job description
            full_description = prompts.format_job_description(
                title=title,
                description=description,
                requirements=requirements,
                max_length=None
            )

            # Get prompt
            prompt = prompts.get_prompt(
                "extract_skills",
                job_title=title,
                job_description=full_description
            )

            print(f"   Calling LLM with temp=0.1, max_tokens=4096...")

            # Call LLM with adjusted parameters
            response = llm.generate_json(
                prompt,
                temperature=0.1,  # Lower temperature to reduce repetitions
                max_tokens=4096   # Higher max tokens for more space
            )

            if "parsed_json" not in response:
                print(f"    ❌ Failed to parse LLM response: {response.get('error')}\n")
                continue

            json_data = response["parsed_json"]
            tokens_used = response.get('tokens_used', 0)
            finish_reason = response.get('finish_reason', 'unknown')

            print(f"   ✅ LLM responded successfully")
            print(f"   Tokens: {tokens_used}, Finish: {finish_reason}")

            # Parse response
            skills = []
            hard_skills = json_data.get("hard_skills", [])
            soft_skills = json_data.get("soft_skills", [])

            for skill_text in hard_skills:
                skills.append({
                    "skill_text": skill_text,
                    "skill_type": "hard",
                    "confidence": 0.9,
                    "llm_model": "gemma-3-4b-instruct"
                })

            for skill_text in soft_skills:
                skills.append({
                    "skill_text": skill_text,
                    "skill_type": "soft",
                    "confidence": 0.9,
                    "llm_model": "gemma-3-4b-instruct"
                })

            print(f"   Extracted {len(skills)} skills ({len(hard_skills)} hard, {len(soft_skills)} soft)")

            # Add ESCO mapping
            skills = pipeline._add_esco_mapping(skills)

            # Calculate processing time
            processing_time = time.time() - start_time

            # Add metadata
            for skill in skills:
                skill['job_id'] = job_id
                skill['extraction_method'] = f'llm_gemma-3-4b-instruct'
                skill['processing_time_seconds'] = processing_time
                skill['tokens_used'] = tokens_used

            # Save to database
            if skills:
                pipeline._save_to_database(skills)
                print(f"    ✅ Saved {len(skills)} skills to database")
                print(f"    ⏱️  Processing time: {processing_time:.2f}s\n")
            else:
                print(f"    ⚠️  No skills extracted\n")

        except Exception as e:
            print(f"    ❌ Error: {e}\n")
            import traceback
            traceback.print_exc()

    print("✅ Done!")

if __name__ == "__main__":
    main()
