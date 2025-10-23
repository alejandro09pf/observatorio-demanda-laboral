#!/usr/bin/env python3
"""
Test Extraction Pipeline con 100 Job Ads Reales

Ejecuta el pipeline completo (Regex + NER + 3-Layer Matching) con 100 job ads
aleatorios de la base de datos y documenta resultados empíricos.

Métricas a capturar:
- Match rate por layer
- Distribution de confidence scores
- Top emergent skills
- Skills más comunes encontradas
- Performance por portal/país
- Tiempo de procesamiento
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import psycopg2
from typing import List, Dict, Any
import json
from datetime import datetime
from collections import Counter, defaultdict
import time

from config.settings import get_settings
from extractor.pipeline import ExtractionPipeline

def fetch_random_jobs(limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch random cleaned jobs from database."""
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    print(f"📥 Fetching {limit} random jobs from database...\n")

    cursor.execute("""
        SELECT
            c.job_id,
            c.title_cleaned,
            c.description_cleaned,
            c.requirements_cleaned,
            c.combined_text,
            c.combined_word_count,
            r.portal,
            r.country
        FROM cleaned_jobs c
        JOIN raw_jobs r ON c.job_id = r.job_id
        WHERE r.is_usable = TRUE
          AND c.combined_word_count >= 100
        ORDER BY RANDOM()
        LIMIT %s
    """, (limit,))

    jobs = []
    for row in cursor.fetchall():
        jobs.append({
            'job_id': str(row[0]),
            'title': row[1],
            'description': row[2],
            'requirements': row[3],
            'combined_text': row[4],
            'word_count': row[5],
            'portal': row[6],
            'country': row[7]
        })

    cursor.close()
    conn.close()

    print(f"✅ Fetched {len(jobs)} jobs")
    print(f"   Portals: {len(set(j['portal'] for j in jobs))}")
    print(f"   Countries: {len(set(j['country'] for j in jobs))}")
    print(f"   Avg word count: {sum(j['word_count'] for j in jobs) / len(jobs):.0f}\n")

    return jobs

def process_jobs_with_pipeline(jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process jobs through extraction pipeline and collect stats."""

    print("🔄 Processing jobs through extraction pipeline...\n")

    pipeline = ExtractionPipeline()

    results = {
        'total_jobs': len(jobs),
        'total_skills_extracted': 0,
        'total_skills_matched': 0,
        'match_rate_overall': 0.0,
        'by_layer': {
            'exact': 0,
            'fuzzy': 0,
            'semantic': 0,
            'emergent': 0
        },
        'by_portal': defaultdict(lambda: {
            'jobs': 0,
            'skills_extracted': 0,
            'skills_matched': 0,
            'match_rate': 0.0
        }),
        'by_country': defaultdict(lambda: {
            'jobs': 0,
            'skills_extracted': 0,
            'skills_matched': 0,
            'match_rate': 0.0
        }),
        'top_matched_skills': Counter(),
        'top_emergent_skills': Counter(),
        'confidence_distribution': {
            '1.00 (exact)': 0,
            '0.85-0.99 (fuzzy)': 0,
            '0.87-0.99 (semantic)': 0
        },
        'extraction_method_stats': {
            'regex_only': 0,
            'ner_only': 0,
            'both': 0,
            'regex_avg': 0,
            'ner_avg': 0
        },
        'processing_time_seconds': 0.0,
        'jobs_processed': []
    }

    start_time = time.time()

    for idx, job in enumerate(jobs, 1):
        if idx % 10 == 0:
            print(f"   Progress: {idx}/{len(jobs)} jobs processed...")

        try:
            # Extract skills
            extracted = pipeline.extract_skills_from_job(job)

            job_result = {
                'job_id': job['job_id'],
                'title': job['title'],
                'portal': job['portal'],
                'country': job['country'],
                'word_count': job['word_count'],
                'skills_extracted': len(extracted),
                'skills_matched': sum(1 for s in extracted if s.esco_match),
                'skills_emergent': sum(1 for s in extracted if not s.esco_match),
                'match_rate': sum(1 for s in extracted if s.esco_match) / len(extracted) if extracted else 0.0,
                'by_layer': {
                    'exact': sum(1 for s in extracted if s.esco_match and s.esco_match.match_method == 'exact'),
                    'fuzzy': sum(1 for s in extracted if s.esco_match and s.esco_match.match_method == 'fuzzy'),
                    'semantic': sum(1 for s in extracted if s.esco_match and s.esco_match.match_method == 'semantic')
                }
            }

            results['jobs_processed'].append(job_result)

            # Update global stats
            results['total_skills_extracted'] += len(extracted)

            for skill in extracted:
                if skill.esco_match:
                    results['total_skills_matched'] += 1
                    results['by_layer'][skill.esco_match.match_method] += 1
                    # Use esco_skill_name (more reliable) or matched_skill_text
                    matched_name = getattr(skill.esco_match, 'esco_skill_name', None) or getattr(skill.esco_match, 'matched_skill_text', 'Unknown')
                    results['top_matched_skills'][matched_name] += 1

                    # Confidence distribution
                    if skill.esco_match.confidence_score == 1.0:
                        results['confidence_distribution']['1.00 (exact)'] += 1
                    elif skill.esco_match.match_method == 'fuzzy':
                        results['confidence_distribution']['0.85-0.99 (fuzzy)'] += 1
                    elif skill.esco_match.match_method == 'semantic':
                        results['confidence_distribution']['0.87-0.99 (semantic)'] += 1
                else:
                    results['by_layer']['emergent'] += 1
                    results['top_emergent_skills'][skill.skill_text] += 1

            # Update portal stats
            portal = job['portal']
            results['by_portal'][portal]['jobs'] += 1
            results['by_portal'][portal]['skills_extracted'] += len(extracted)
            results['by_portal'][portal]['skills_matched'] += sum(1 for s in extracted if s.esco_match)

            # Update country stats
            country = job['country']
            results['by_country'][country]['jobs'] += 1
            results['by_country'][country]['skills_extracted'] += len(extracted)
            results['by_country'][country]['skills_matched'] += sum(1 for s in extracted if s.esco_match)

        except Exception as e:
            import traceback
            if idx == 1:  # Only print full traceback for first error
                print(f"\n   ⚠️  Full error for job {job['job_id']}:")
                traceback.print_exc()
                print()
            else:
                print(f"   ⚠️  Error processing job {job['job_id']}: {e}")
            continue

    end_time = time.time()
    results['processing_time_seconds'] = round(end_time - start_time, 2)

    # Calculate overall match rate
    if results['total_skills_extracted'] > 0:
        results['match_rate_overall'] = results['total_skills_matched'] / results['total_skills_extracted']

    # Calculate portal match rates
    for portal_stats in results['by_portal'].values():
        if portal_stats['skills_extracted'] > 0:
            portal_stats['match_rate'] = portal_stats['skills_matched'] / portal_stats['skills_extracted']

    # Calculate country match rates
    for country_stats in results['by_country'].values():
        if country_stats['skills_extracted'] > 0:
            country_stats['match_rate'] = country_stats['skills_matched'] / country_stats['skills_extracted']

    # Convert defaultdicts to regular dicts for JSON serialization
    results['by_portal'] = dict(results['by_portal'])
    results['by_country'] = dict(results['by_country'])
    results['top_matched_skills'] = dict(results['top_matched_skills'].most_common(30))
    results['top_emergent_skills'] = dict(results['top_emergent_skills'].most_common(30))

    print(f"\n✅ Processing complete in {results['processing_time_seconds']:.1f}s\n")

    return results

def print_summary(results: Dict[str, Any]):
    """Print summary of results."""

    print("\n" + "="*100)
    print(" "*30 + "PIPELINE TEST RESULTS: 100 JOB ADS")
    print("="*100 + "\n")

    # Overall stats
    print("📊 OVERALL STATISTICS\n")
    print(f"   Total Jobs Processed:      {results['total_jobs']}")
    print(f"   Total Skills Extracted:    {results['total_skills_extracted']:,}")
    print(f"   Total Skills Matched:      {results['total_skills_matched']:,}")
    print(f"   Overall Match Rate:        {results['match_rate_overall']:.1%}")
    print(f"   Avg Skills per Job:        {results['total_skills_extracted'] / results['total_jobs']:.1f}")
    print(f"   Processing Time:           {results['processing_time_seconds']:.1f}s")
    print(f"   Avg Time per Job:          {results['processing_time_seconds'] / results['total_jobs']:.2f}s\n")

    # By layer
    print("="*100)
    print("🎯 MATCHING BY LAYER\n")

    total_extracted = results['total_skills_extracted']
    for layer, count in results['by_layer'].items():
        pct = (count / total_extracted * 100) if total_extracted > 0 else 0
        print(f"   {layer.capitalize():<12}: {count:>5,} skills ({pct:>5.1f}%)")

    # By portal
    print("\n" + "="*100)
    print("🌐 PERFORMANCE BY PORTAL\n")

    portal_sorted = sorted(results['by_portal'].items(),
                          key=lambda x: x[1]['jobs'],
                          reverse=True)

    print(f"{'Portal':<20} | {'Jobs':>5} | {'Skills Ext':>10} | {'Skills Match':>12} | {'Match Rate':>10}")
    print("-" * 100)

    for portal, stats in portal_sorted:
        print(f"{portal:<20} | {stats['jobs']:>5} | {stats['skills_extracted']:>10,} | "
              f"{stats['skills_matched']:>12,} | {stats['match_rate']:>9.1%}")

    # By country
    print("\n" + "="*100)
    print("🌎 PERFORMANCE BY COUNTRY\n")

    country_sorted = sorted(results['by_country'].items(),
                           key=lambda x: x[1]['jobs'],
                           reverse=True)

    print(f"{'Country':<20} | {'Jobs':>5} | {'Skills Ext':>10} | {'Skills Match':>12} | {'Match Rate':>10}")
    print("-" * 100)

    for country, stats in country_sorted:
        print(f"{country:<20} | {stats['jobs']:>5} | {stats['skills_extracted']:>10,} | "
              f"{stats['skills_matched']:>12,} | {stats['match_rate']:>9.1%}")

    # Top matched skills
    print("\n" + "="*100)
    print("⭐ TOP 20 MATCHED SKILLS\n")

    for idx, (skill, count) in enumerate(list(results['top_matched_skills'].items())[:20], 1):
        print(f"   {idx:>2}. {skill:<50} ({count:>3} occurrences)")

    # Top emergent skills
    print("\n" + "="*100)
    print("🆕 TOP 20 EMERGENT SKILLS (No ESCO Match)\n")

    for idx, (skill, count) in enumerate(list(results['top_emergent_skills'].items())[:20], 1):
        print(f"   {idx:>2}. {skill:<50} ({count:>3} occurrences)")

    # Confidence distribution
    print("\n" + "="*100)
    print("📈 CONFIDENCE SCORE DISTRIBUTION\n")

    for conf_range, count in results['confidence_distribution'].items():
        pct = (count / results['total_skills_matched'] * 100) if results['total_skills_matched'] > 0 else 0
        print(f"   {conf_range:<25}: {count:>5,} skills ({pct:>5.1f}%)")

    print("\n" + "="*100 + "\n")

def save_results(results: Dict[str, Any], output_path: Path):
    """Save results to JSON file."""

    # Add metadata
    results['metadata'] = {
        'timestamp': datetime.now().isoformat(),
        'test_description': 'Extraction pipeline test with 100 random job ads',
        'layer3_enabled': False,
        'thresholds': {
            'fuzzy': 0.85,
            'semantic': 0.87
        }
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"💾 Results saved to: {output_path}\n")

def main():
    print("\n" + "="*100)
    print(" "*25 + "EXTRACTION PIPELINE TEST: 100 JOB ADS")
    print("="*100 + "\n")

    # Fetch jobs
    jobs = fetch_random_jobs(limit=100)

    # Process jobs
    results = process_jobs_with_pipeline(jobs)

    # Print summary
    print_summary(results)

    # Save results
    output_path = Path(__file__).parent.parent / "data" / "test_results" / f"pipeline_test_100jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_results(results, output_path)

    print("✅ Test complete!\n")

if __name__ == '__main__':
    main()
