"""
Deep analysis: Why are we missing 43% of skills?
Analyze regex vs NER performance and identify patterns in missing skills.
"""
import sys
sys.path.insert(0, '/Users/nicocamacho/Documents/Tesis/observatorio-demanda-laboral/src')

import psycopg2
from src.extractor.pipeline import ExtractionPipeline
from src.config.settings import get_settings

def analyze_job_deep(job_id, job_title):
    """Deep analysis of a single job."""

    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    with psycopg2.connect(db_url) as conn:
        cursor = conn.cursor()

        # Get job text
        cursor.execute("""
            SELECT r.job_id, r.title, c.combined_text
            FROM raw_jobs r
            JOIN cleaned_jobs c ON r.job_id = c.job_id
            WHERE r.job_id = %s
        """, (job_id,))

        job_data = cursor.fetchone()
        if not job_data:
            print(f"❌ Job {job_id} not found")
            return None

        job_id, title, combined_text = job_data

        # Get gold standard annotations (hard skills only)
        cursor.execute("""
            SELECT skill_text
            FROM gold_standard_annotations
            WHERE job_id = %s AND skill_type = 'hard'
            ORDER BY skill_text
        """, (job_id,))

        gold_skills = [row[0] for row in cursor.fetchall()]

        print("\n" + "="*100)
        print(f"🔍 JOB: {title[:70]}")
        print(f"   ID: {job_id}")
        print(f"   Gold Standard: {len(gold_skills)} hard skills")
        print("="*100)

        # Extract skills with Pipeline A
        pipeline = ExtractionPipeline()

        job_input = {
            'job_id': job_id,
            'title': title,
            'combined_text': combined_text
        }

        results = pipeline.extract_skills_from_job(job_input)

        # Separate regex and NER results
        regex_results = [r for r in results if r.extraction_method == 'regex']
        ner_results = [r for r in results if r.extraction_method == 'ner']

        regex_skills = set([r.skill_text.lower() for r in regex_results])
        ner_skills = set([r.skill_text.lower() for r in ner_results])
        all_skills = set([r.skill_text.lower() for r in results])

        gold_normalized = set([s.lower() for s in gold_skills])

        # Analysis
        print(f"\n📊 EXTRACTION BREAKDOWN:")
        print(f"   Regex extracted: {len(regex_skills)} unique skills")
        print(f"   NER extracted: {len(ner_skills)} unique skills")
        print(f"   Combined (deduplicated): {len(all_skills)} unique skills")
        print(f"   Gold Standard: {len(gold_normalized)} hard skills")

        # Found by each method
        found_regex = gold_normalized & regex_skills
        found_ner = gold_normalized & ner_skills
        found_both = found_regex & found_ner
        found_regex_only = found_regex - found_ner
        found_ner_only = found_ner - found_regex
        found_total = gold_normalized & all_skills
        missing = gold_normalized - all_skills

        print(f"\n✅ FOUND BY REGEX ONLY: {len(found_regex_only)}")
        print(f"✅ FOUND BY NER ONLY: {len(found_ner_only)}")
        print(f"✅ FOUND BY BOTH: {len(found_both)}")
        print(f"✅ TOTAL FOUND: {len(found_total)}")
        print(f"❌ MISSING: {len(missing)}")

        recall_regex = len(found_regex) / len(gold_normalized) if gold_normalized else 0
        recall_ner = len(found_ner) / len(gold_normalized) if gold_normalized else 0
        recall_total = len(found_total) / len(gold_normalized) if gold_normalized else 0

        print(f"\n📈 RECALL BREAKDOWN:")
        print(f"   Regex recall: {recall_regex:.2%} ({len(found_regex)}/{len(gold_normalized)})")
        print(f"   NER recall: {recall_ner:.2%} ({len(found_ner)}/{len(gold_normalized)})")
        print(f"   Total recall: {recall_total:.2%} ({len(found_total)}/{len(gold_normalized)})")

        # Analyze missing skills
        print(f"\n❌ MISSING SKILLS ANALYSIS ({len(missing)} skills):")
        print("\nSearching for each missing skill in the text...")

        missing_categories = {
            'in_text_exact': [],  # Exact match in text, but not extracted
            'in_text_variation': [],  # Variation in text (e.g., "react native" vs "React Native")
            'not_in_text': [],  # Not found in text at all (annotation error?)
            'acronym': [],  # Acronym/abbreviation in text, full form in gold
        }

        for skill in sorted(missing):
            skill_lower = skill.lower()
            text_lower = combined_text.lower()

            if skill_lower in text_lower:
                missing_categories['in_text_exact'].append(skill)
            elif any(word in text_lower for word in skill_lower.split() if len(word) > 3):
                missing_categories['in_text_variation'].append(skill)
            else:
                # Check for common acronyms
                acronym_map = {
                    'programación orientada a objetos': ['poo', 'oop'],
                    'inteligencia artificial': ['ia', 'ai'],
                    'rest api': ['rest', 'restful'],
                    'ci/cd': ['ci', 'cd', 'continuous integration', 'continuous deployment'],
                }

                found_acronym = False
                for full_form, acronyms in acronym_map.items():
                    if full_form in skill_lower:
                        for acr in acronyms:
                            if acr in text_lower:
                                missing_categories['acronym'].append(skill)
                                found_acronym = True
                                break
                    if found_acronym:
                        break

                if not found_acronym:
                    missing_categories['not_in_text'].append(skill)

        print(f"\n🔍 MISSING SKILL CATEGORIES:")
        print(f"   ✅ Exact match in text, not extracted: {len(missing_categories['in_text_exact'])}")
        print(f"   ⚠️  Variation in text: {len(missing_categories['in_text_variation'])}")
        print(f"   📝 Acronym issue: {len(missing_categories['acronym'])}")
        print(f"   ❓ Not found in text: {len(missing_categories['not_in_text'])}")

        # Show examples
        if missing_categories['in_text_exact']:
            print(f"\n⚠️  CRITICAL: Skills EXACTLY in text but NOT extracted (sample):")
            for skill in sorted(missing_categories['in_text_exact'])[:10]:
                # Find where in text
                idx = combined_text.lower().find(skill.lower())
                if idx != -1:
                    context_start = max(0, idx - 40)
                    context_end = min(len(combined_text), idx + len(skill) + 40)
                    context = combined_text[context_start:context_end].replace('\n', ' ')
                    print(f"   • '{skill}' → ...{context}...")

        if missing_categories['in_text_variation']:
            print(f"\n📝 Skills with variations in text (sample):")
            for skill in sorted(missing_categories['in_text_variation'])[:5]:
                print(f"   • '{skill}'")

        if missing_categories['acronym']:
            print(f"\n🔤 Acronym/full form mismatch (sample):")
            for skill in sorted(missing_categories['acronym'])[:5]:
                print(f"   • '{skill}'")

        if missing_categories['not_in_text']:
            print(f"\n❓ NOT found in text (possible annotation error, sample):")
            for skill in sorted(missing_categories['not_in_text'])[:5]:
                print(f"   • '{skill}'")

        return {
            'job_id': job_id,
            'title': title,
            'regex_skills': len(regex_skills),
            'ner_skills': len(ner_skills),
            'total_skills': len(all_skills),
            'found_regex': len(found_regex),
            'found_ner': len(found_ner),
            'found_both': len(found_both),
            'found_total': len(found_total),
            'gold_total': len(gold_normalized),
            'missing': len(missing),
            'recall_regex': recall_regex,
            'recall_ner': recall_ner,
            'recall_total': recall_total,
            'missing_categories': {k: len(v) for k, v in missing_categories.items()}
        }

if __name__ == "__main__":
    # Analyze 3 diverse jobs: best, middle, worst
    jobs = [
        ('d942e87a-a716-4473-ae6f-db95cea82d64', 'Java Backend (Best: 72%)'),
        ('3550cbc4-5ca7-4ec6-ab33-9a257c67ae28', 'Laravel/PHP (Middle: 68%)'),
        ('39e75f82-c466-4721-9521-cf90a6e7ded1', 'BI Developer (Worst: 43%)'),
    ]

    results = []
    for job_id, job_title in jobs:
        result = analyze_job_deep(job_id, job_title)
        if result:
            results.append(result)

    # Summary
    print("\n" + "="*100)
    print("📊 SUMMARY: REGEX vs NER PERFORMANCE")
    print("="*100)

    total_gold = sum(r['gold_total'] for r in results)
    total_found_regex = sum(r['found_regex'] for r in results)
    total_found_ner = sum(r['found_ner'] for r in results)
    total_found_both = sum(r['found_both'] for r in results)
    total_found = sum(r['found_total'] for r in results)

    avg_recall_regex = total_found_regex / total_gold if total_gold > 0 else 0
    avg_recall_ner = total_found_ner / total_gold if total_gold > 0 else 0
    avg_recall_total = total_found / total_gold if total_gold > 0 else 0

    print(f"\n📈 AVERAGE RECALL:")
    print(f"   Regex: {avg_recall_regex:.2%} ({total_found_regex}/{total_gold})")
    print(f"   NER: {avg_recall_ner:.2%} ({total_found_ner}/{total_gold})")
    print(f"   Total: {avg_recall_total:.2%} ({total_found}/{total_gold})")

    print(f"\n🔄 OVERLAP:")
    print(f"   Found by BOTH: {total_found_both} ({total_found_both/total_found*100:.1f}% of found skills)")
    print(f"   Regex ONLY: {total_found_regex - total_found_both}")
    print(f"   NER ONLY: {total_found_ner - total_found_both}")

    # Missing categories summary
    print(f"\n❌ MISSING SKILLS BREAKDOWN:")
    total_exact = sum(r['missing_categories']['in_text_exact'] for r in results)
    total_variation = sum(r['missing_categories']['in_text_variation'] for r in results)
    total_acronym = sum(r['missing_categories']['acronym'] for r in results)
    total_not_in_text = sum(r['missing_categories']['not_in_text'] for r in results)

    total_missing = sum(r['missing'] for r in results)

    print(f"   ✅ Exact in text, not extracted: {total_exact} ({total_exact/total_missing*100:.1f}%)")
    print(f"   ⚠️  Variation in text: {total_variation} ({total_variation/total_missing*100:.1f}%)")
    print(f"   📝 Acronym mismatch: {total_acronym} ({total_acronym/total_missing*100:.1f}%)")
    print(f"   ❓ Not in text: {total_not_in_text} ({total_not_in_text/total_missing*100:.1f}%)")

    print("\n" + "="*100)
    print("🎯 CONCLUSION: Where to focus improvements?")
    print("="*100)
    print(f"1. PRIORITY HIGH: {total_exact} skills are EXACTLY in text but we don't extract them")
    print(f"2. PRIORITY MEDIUM: {total_variation} skills have variations we don't recognize")
    print(f"3. PRIORITY LOW: {total_acronym} acronym/full form mismatches")
    print(f"4. REVIEW: {total_not_in_text} skills not found in text (annotation issues?)")
