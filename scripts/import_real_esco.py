#!/usr/bin/env python3
"""
Import Complete ESCO Taxonomy from All Collections
"""

import sys
import os
import csv
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.settings import get_settings
from config.logging_config import setup_logging

# Setup logging
settings = get_settings()
setup_logging(settings.log_level, settings.log_file)
logger = logging.getLogger(__name__)

def import_esco_collection(collection_name: str, csv_file: Path, skill_group: str = None):
    """Import skills from a specific ESCO collection."""
    try:
        import psycopg2
        
        # Connect to database
        db_url = settings.database_url
        if db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', 'postgres://')
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        logger.info(f"Importing {collection_name}...")
        
        if not csv_file.exists():
            logger.warning(f"File not found: {csv_file}")
            return 0
        
        skills_count = 0
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Map ESCO fields to our database schema - handle different CSV structures
                    skill_uri = row.get('conceptUri', '')
                    skill_id = skill_uri.split('/')[-1] if skill_uri else ''
                    preferred_label_es = row.get('preferredLabel', '')
                    preferred_label_en = ''
                    description_es = row.get('description', '')
                    description_en = ''
                    
                    # Handle different field names for skill type
                    skill_type = row.get('skillType', 'knowledge')
                    skill_group_final = skill_group or row.get('skillGroup', '')
                    skill_family = row.get('conceptType', 'knowledge')
                    
                    # Only insert if we have a Spanish label and URI
                    if preferred_label_es and skill_uri:
                        cursor.execute("""
                            INSERT INTO esco_skills (
                                skill_uri, skill_id, preferred_label_es, preferred_label_en,
                                description_es, description_en, skill_type, skill_group, skill_family,
                                is_active
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (skill_uri) DO NOTHING
                        """, (
                            skill_uri, skill_id, preferred_label_es, preferred_label_en,
                            description_es, description_en, skill_type, skill_group_final, skill_family,
                            True
                        ))
                        
                        if cursor.rowcount > 0:
                            skills_count += 1
                            
                            if skills_count % 100 == 0:
                                logger.info(f"  Processed {skills_count} skills...")
                                
                except Exception as e:
                    logger.warning(f"Failed to insert skill {row.get('conceptUri', '')}: {e}")
                    continue
        
        conn.commit()
        logger.info(f"✅ {collection_name}: {skills_count} skills imported")
        return skills_count
        
    except Exception as e:
        logger.error(f"Error importing {collection_name}: {e}")
        return 0
    finally:
        if 'conn' in locals():
            conn.close()

def import_all_esco_collections():
    """Import all ESCO skill collections."""
    try:
        import psycopg2
        
        # Connect to database
        db_url = settings.database_url
        if db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', 'postgres://')
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        logger.info("Starting complete ESCO taxonomy import...")
        
        # First, clear existing data
        cursor.execute("DELETE FROM esco_skills")
        cursor.execute("DELETE FROM esco_skill_groups")
        logger.info("Cleared existing ESCO data")
        
        conn.commit()
        conn.close()
        
        total_skills = 0
        esco_dir = Path(__file__).parent.parent / "data" / "esco"
        
        # Import all collections
        collections = [
            ("Main Skills", esco_dir / "skills_es.csv", "General Skills"),
            ("Digital Skills", esco_dir / "digitalSkillsCollection_es.csv", "Digital Skills"),
            ("Transversal Skills", esco_dir / "transversalSkillsCollection_es.csv", "Soft Skills"),
            ("Digital Competence", esco_dir / "digCompSkillsCollection_es.csv", "Digital Competence"),
            ("Green Skills", esco_dir / "greenSkillsCollection_es.csv", "Sustainability"),
            ("Language Skills", esco_dir / "languageSkillsCollection_es.csv", "Languages"),
            ("Research Skills", esco_dir / "researchSkillsCollection_es.csv", "Research & Academic")
        ]
        
        for collection_name, csv_file, skill_group in collections:
            skills_imported = import_esco_collection(collection_name, csv_file, skill_group)
            total_skills += skills_imported
        
        # Import skill groups
        skill_groups_imported = import_esco_skill_groups()
        
        logger.info(f"🎉 ESCO import completed successfully!")
        logger.info(f"📊 Total skills imported: {total_skills}")
        logger.info(f"📊 Skill groups imported: {skill_groups_imported}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in complete ESCO import: {e}")
        return False

def import_esco_skill_groups():
    """Import ESCO skill groups."""
    try:
        import psycopg2
        
        # Connect to database
        db_url = settings.database_url
        if db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', 'postgres://')
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        logger.info("Importing ESCO skill groups...")
        
        groups_file = Path(__file__).parent.parent / "data" / "esco" / "skillGroups_es.csv"
        
        if not groups_file.exists():
            logger.error(f"Skill groups file not found: {groups_file}")
            return 0
        
        groups_count = 0
        with open(groups_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    group_id = row.get('code', '')
                    group_name_es = row.get('preferredLabel', '')
                    group_name_en = ''
                    description_es = row.get('description', '')
                    description_en = ''
                    
                    if group_name_es and group_id:
                        cursor.execute("""
                            INSERT INTO esco_skill_groups (
                                group_id, group_name_es, group_name_en, description_es, description_en
                            ) VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (group_id) DO NOTHING
                        """, (
                            group_id, group_name_es, group_name_en, description_es, description_en
                        ))
                        
                        if cursor.rowcount > 0:
                            groups_count += 1
                            
                except Exception as e:
                    logger.warning(f"Failed to insert skill group {row.get('code', '')}: {e}")
                    continue
        
        conn.commit()
        logger.info(f"✅ Skill groups: {groups_count} imported")
        return groups_count
        
    except Exception as e:
        logger.error(f"Error importing skill groups: {e}")
        return 0
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Main function to import complete ESCO taxonomy."""
    logger.info("🚀 Starting complete ESCO taxonomy import...")
    
    if not import_all_esco_collections():
        logger.error("Failed to import ESCO collections")
        return False
    
    logger.info("✅ Complete ESCO taxonomy import completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
