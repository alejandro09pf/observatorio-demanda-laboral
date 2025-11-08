#!/usr/bin/env python3
"""Simple LLM model comparison using existing pipeline."""

import sys
import csv
import time
import psycopg2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config.settings import get_settings
from llm_processor.pipeline import LLMExtractionPipeline

# Get settings
settings = get_settings()
db_url = settings.database_url
if db_url.startswith('postgresql://'):
    db_url = db_url.replace('postgresql://', 'postgres://')

# Models to test
MODELS = [
    "llama-3.2-3b-instruct",
    "qwen2.5-3b-instruct",
    "phi-3.5-mini"
]

# Load job IDs
job_ids = []
with open('/tmp/selected_10_jobs.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        job_ids.append(row['job_id'])

print(f"Loaded {len(job_ids)} jobs")

# Process each model
for model_name in MODELS:
    print(f"\n{'='*80}")
    print(f"🤖 Model: {model_name}")
    print(f"{'='*80}\n")

    try:
        # Initialize pipeline
        pipeline = LLMExtractionPipeline(model_name=model_name)

        # Process jobs
        for idx, job_id in enumerate(job_ids, 1):
            print(f"[{idx}/10] Processing {job_id}...")
            try:
                pipeline.process_job(job_id)
                print(f"  ✅ Done")
            except Exception as e:
                print(f"  ❌ Error: {e}")

        print(f"\n✅ {model_name} complete\n")

    except Exception as e:
        print(f"❌ Failed to load {model_name}: {e}\n")

    # Wait between models
    if model_name != MODELS[-1]:
        print("⏳ Waiting 10s...\n")
        time.sleep(10)

print("\n" + "="*80)
print("✅ ALL MODELS COMPLETE")
print("="*80)
print("\nRun evaluation:")
print("venv/bin/python3 scripts/evaluate_pipelines.py --mode subset \\")
print("  --job-ids-file /tmp/selected_10_jobs.csv \\")
print("  --pipelines gemma-3-4b-instruct llama-3.2-3b-instruct \\")
print("               qwen2.5-3b-instruct phi-3.5-mini \\")
print("  --skill-type hard")
