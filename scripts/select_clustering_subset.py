#!/usr/bin/env python3
"""
Select subset of skills for clustering prototype.

This script:
1. Queries top N skills from gold_standard_annotations with embeddings
2. Analyzes skill distribution and diversity
3. Exports to JSON for reproducibility
4. Generates summary statistics

Usage:
    python scripts/select_clustering_subset.py --limit 400
    python scripts/select_clustering_subset.py --limit 400 --min-frequency 5
"""

import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter
import psycopg2

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config.settings import get_settings


def select_subset(
    limit: int = 400,
    min_frequency: int = 3,
    exclude_generic: bool = True
) -> List[Dict[str, Any]]:
    """
    Select top N skills for clustering prototype.

    Args:
        limit: Maximum number of skills to select
        min_frequency: Minimum skill frequency threshold
        exclude_generic: Exclude generic skills like "Backend", "Frontend"

    Returns:
        List of skill dicts with metadata
    """
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # Build exclusion filter
    exclusions = []
    if exclude_generic:
        exclusions = ['Backend', 'Frontend', 'Desarrollo', 'Programación',
                      'Full-stack', 'Fullstack development']

    exclusion_clause = ""
    if exclusions:
        exclusion_list = ", ".join([f"'{e}'" for e in exclusions])
        exclusion_clause = f"AND gs.skill_text NOT IN ({exclusion_list})"

    # Query top skills
    query = f"""
        SELECT
            gs.skill_text,
            COUNT(*) as frequency,
            COUNT(DISTINCT gs.job_id) as job_count,
            ROUND(COUNT(DISTINCT gs.job_id)::numeric / 300.0 * 100, 1) as job_coverage_pct,
            se.model_name,
            se.model_version
        FROM gold_standard_annotations gs
        INNER JOIN skill_embeddings se
            ON LOWER(TRIM(gs.skill_text)) = LOWER(TRIM(se.skill_text))
        WHERE gs.skill_type = 'hard'
          {exclusion_clause}
        GROUP BY gs.skill_text, se.model_name, se.model_version
        HAVING COUNT(*) >= %s
        ORDER BY frequency DESC
        LIMIT %s
    """

    cursor.execute(query, (min_frequency, limit))
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    # Convert to list of dicts
    skills = []
    for row in results:
        skills.append({
            'skill_text': row[0],
            'frequency': int(row[1]),
            'job_count': int(row[2]),
            'job_coverage_pct': float(row[3]),
            'model_name': row[4],
            'model_version': row[5]
        })

    return skills


def analyze_subset(skills: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze skill subset composition and distribution.

    Args:
        skills: List of skill dicts

    Returns:
        Analysis dict with statistics
    """
    frequencies = [s['frequency'] for s in skills]
    job_counts = [s['job_count'] for s in skills]
    coverages = [s['job_coverage_pct'] for s in skills]

    # Categorize skills by type (heuristic)
    categories = {
        'languages': [],
        'frameworks': [],
        'cloud': [],
        'databases': [],
        'devops': [],
        'methodologies': [],
        'tools': [],
        'concepts': [],
        'other': []
    }

    # Simple categorization rules
    for skill in skills:
        text = skill['skill_text'].lower()

        if any(lang in text for lang in ['javascript', 'python', 'java', 'c#', 'c++', 'go',
                                          'rust', 'typescript', 'php', 'ruby', 'kotlin', 'swift']):
            categories['languages'].append(skill['skill_text'])
        elif any(fw in text for fw in ['react', 'angular', 'vue', 'django', 'flask', 'spring',
                                        'express', 'nest', 'laravel', 'rails', '.net']):
            categories['frameworks'].append(skill['skill_text'])
        elif any(cloud in text for cloud in ['aws', 'azure', 'gcp', 'cloud', 'serverless', 'lambda']):
            categories['cloud'].append(skill['skill_text'])
        elif any(db in text for db in ['sql', 'postgres', 'mysql', 'mongodb', 'redis', 'oracle',
                                        'nosql', 'database', 'db']):
            categories['databases'].append(skill['skill_text'])
        elif any(devops in text for devops in ['docker', 'kubernetes', 'ci/cd', 'jenkins', 'gitlab',
                                                'terraform', 'ansible', 'devops', 'git']):
            categories['devops'].append(skill['skill_text'])
        elif any(method in text for method in ['agile', 'scrum', 'kanban', 'lean', 'metodolog']):
            categories['methodologies'].append(skill['skill_text'])
        elif any(tool in text for tool in ['github', 'jira', 'postman', 'figma', 'vscode']):
            categories['tools'].append(skill['skill_text'])
        elif any(concept in text for concept in ['microservicio', 'api', 'rest', 'graphql',
                                                  'arquitectura', 'patrón', 'testing', 'seguridad',
                                                  'escalabilidad', 'performance']):
            categories['concepts'].append(skill['skill_text'])
        else:
            categories['other'].append(skill['skill_text'])

    # Calculate statistics
    analysis = {
        'total_skills': len(skills),
        'frequency_stats': {
            'min': min(frequencies),
            'max': max(frequencies),
            'mean': sum(frequencies) / len(frequencies),
            'median': sorted(frequencies)[len(frequencies) // 2],
            'total': sum(frequencies)
        },
        'job_coverage_stats': {
            'min': min(coverages),
            'max': max(coverages),
            'mean': sum(coverages) / len(coverages),
            'median': sorted(coverages)[len(coverages) // 2]
        },
        'categories': {
            cat: len(skills_list)
            for cat, skills_list in categories.items()
            if len(skills_list) > 0
        },
        'top_10_skills': [
            {'skill': s['skill_text'], 'frequency': s['frequency']}
            for s in skills[:10]
        ],
        'category_breakdown': {
            cat: skills_list
            for cat, skills_list in categories.items()
            if len(skills_list) > 0
        }
    }

    return analysis


def export_subset(
    skills: List[Dict[str, Any]],
    analysis: Dict[str, Any],
    output_path: str
):
    """
    Export subset to JSON file.

    Args:
        skills: List of skill dicts
        analysis: Analysis dict
        output_path: Output file path
    """
    from datetime import datetime

    output = {
        'metadata': {
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'selection_criteria': {
                'limit': len(skills),
                'min_frequency': 3,
                'skill_type': 'hard',
                'exclude_generic': True,
                'data_source': 'gold_standard_annotations'
            },
            'model_info': {
                'embedding_model': skills[0]['model_name'] if skills else None,
                'model_version': skills[0]['model_version'] if skills else None,
                'embedding_dim': 768
            }
        },
        'analysis': analysis,
        'skills': skills
    }

    # Create output directory if needed
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return output_file


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Select subset of skills for clustering prototype"
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=400,
        help="Maximum number of skills to select (default: 400)"
    )
    parser.add_argument(
        '--min-frequency',
        type=int,
        default=3,
        help="Minimum skill frequency (default: 3)"
    )
    parser.add_argument(
        '--output',
        type=str,
        default='outputs/clustering/prototype_subset.json',
        help="Output JSON file path"
    )

    args = parser.parse_args()

    print("="*70)
    print("CLUSTERING SUBSET SELECTOR")
    print("="*70)
    print(f"Limit:         {args.limit} skills")
    print(f"Min frequency: {args.min_frequency} appearances")
    print(f"Output:        {args.output}")
    print()

    # Step 1: Select subset
    print("📂 Selecting skills from gold_standard_annotations...")
    skills = select_subset(
        limit=args.limit,
        min_frequency=args.min_frequency,
        exclude_generic=True
    )
    print(f"   Selected: {len(skills)} skills")

    if len(skills) == 0:
        print("\n❌ No skills found matching criteria")
        return

    # Step 2: Analyze subset
    print("\n📊 Analyzing subset composition...")
    analysis = analyze_subset(skills)

    # Step 3: Export to JSON
    print(f"\n💾 Exporting to {args.output}...")
    output_file = export_subset(skills, analysis, args.output)
    print(f"   ✅ Exported: {output_file}")

    # Step 4: Print summary
    print("\n" + "="*70)
    print("📊 SUBSET ANALYSIS SUMMARY")
    print("="*70)
    print(f"\n🔢 Total Skills: {analysis['total_skills']}")

    print(f"\n📈 Frequency Distribution:")
    print(f"   Min:    {analysis['frequency_stats']['min']}")
    print(f"   Max:    {analysis['frequency_stats']['max']}")
    print(f"   Mean:   {analysis['frequency_stats']['mean']:.1f}")
    print(f"   Median: {analysis['frequency_stats']['median']}")
    print(f"   Total:  {analysis['frequency_stats']['total']:,} appearances")

    print(f"\n🎯 Job Coverage:")
    print(f"   Min:    {analysis['job_coverage_stats']['min']:.1f}%")
    print(f"   Max:    {analysis['job_coverage_stats']['max']:.1f}%")
    print(f"   Mean:   {analysis['job_coverage_stats']['mean']:.1f}%")
    print(f"   Median: {analysis['job_coverage_stats']['median']:.1f}%")

    print(f"\n🗂️  Skill Categories:")
    for category, count in sorted(analysis['categories'].items(), key=lambda x: x[1], reverse=True):
        pct = count / analysis['total_skills'] * 100
        print(f"   {category:20s}: {count:3d} ({pct:5.1f}%)")

    print(f"\n🏆 Top 10 Skills:")
    for i, skill in enumerate(analysis['top_10_skills'], 1):
        print(f"   {i:2d}. {skill['skill']:30s} ({skill['frequency']:3d} appearances)")

    print("\n" + "="*70)
    print("✅ SUBSET SELECTION COMPLETE")
    print("="*70)
    print(f"\n📄 Subset saved to: {output_file}")
    print(f"🎯 Ready for clustering with {len(skills)} skills")
    print("\n🚀 Next step: Run clustering prototype")
    print("   python scripts/prototype_clustering.py")
    print()


if __name__ == '__main__':
    main()
