import psycopg2
from typing import List, Dict, Any, Optional
import logging
from config.settings import get_settings
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ESCOMatch:
    """Represents an ESCO skill match."""
    skill_text: str
    esco_skill_uri: str
    esco_skill_name: str
    confidence_score: float
    skill_type: str
    skill_group: str
    match_method: str

class ESCOMatcher:
    """Match skills to local ESCO taxonomy database."""
    
    def __init__(self):
        self.settings = get_settings()
        self.db_url = self.settings.database_url
        
        # Fix database URL format
        if self.db_url.startswith('postgresql://'):
            self.db_url = self.db_url.replace('postgresql://', 'postgres://')
    
    def match_skill(self, skill_text: str) -> Optional[ESCOMatch]:
        """Match a single skill to ESCO taxonomy."""
        if not skill_text:
            return None
        
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()
                
                # Use the search function we created
                cursor.execute("""
                    SELECT skill_uri, preferred_label, skill_type, skill_group, confidence_score
                    FROM search_esco_skills(%s, 'es', 0.3)
                    ORDER BY confidence_score DESC
                    LIMIT 1
                """, (skill_text,))
                
                result = cursor.fetchone()
                if result:
                    skill_uri, preferred_label, skill_type, skill_group, confidence = result
                    
                    return ESCOMatch(
                        skill_text=skill_text,
                        esco_skill_uri=skill_uri,
                        esco_skill_name=preferred_label,
                        confidence_score=confidence,
                        skill_type=skill_type or 'unknown',
                        skill_group=skill_group or 'unknown',
                        match_method='local_search'
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Error matching skill '{skill_text}' to ESCO: {e}")
            return None
    
    def batch_match_skills(self, skill_texts: List[str]) -> Dict[str, Optional[ESCOMatch]]:
        """Match multiple skills to ESCO taxonomy in batch."""
        if not skill_texts:
            return {}
        
        results = {}
        
        for skill_text in skill_texts:
            try:
                match = self.match_skill(skill_text)
                results[skill_text] = match
            except Exception as e:
                logger.error(f"Error in batch matching for '{skill_text}': {e}")
                results[skill_text] = None
        
        return results
    
    def search_skills(self, query: str, limit: int = 10) -> List[ESCOMatch]:
        """Search for skills in ESCO taxonomy."""
        if not query:
            return []
        
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()
                
                # Use the search function
                cursor.execute("""
                    SELECT skill_uri, preferred_label, skill_type, skill_group, confidence_score
                    FROM search_esco_skills(%s, 'es', 0.3)
                    ORDER BY confidence_score DESC
                    LIMIT %s
                """, (query, limit))
                
                results = cursor.fetchall()
                matches = []
                
                for result in results:
                    skill_uri, preferred_label, skill_type, skill_group, confidence = result
                    
                    match = ESCOMatch(
                        skill_text=query,
                        esco_skill_uri=skill_uri,
                        esco_skill_name=preferred_label,
                        confidence_score=confidence,
                        skill_type=skill_type or 'unknown',
                        skill_group=skill_group or 'unknown',
                        match_method='local_search'
                    )
                    matches.append(match)
                
                return matches
                
        except Exception as e:
            logger.error(f"Error searching skills for '{query}': {e}")
            return []
    
    def get_skill_details(self, skill_uri: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific ESCO skill."""
        if not skill_uri:
            return None
        
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT skill_uri, preferred_label_es, preferred_label_en, 
                           description_es, description_en, skill_type, skill_group, skill_family
                    FROM esco_skills
                    WHERE skill_uri = %s AND is_active = TRUE
                """, (skill_uri,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'skill_uri': result[0],
                        'preferred_label_es': result[1],
                        'preferred_label_en': result[2],
                        'description_es': result[3],
                        'description_en': result[4],
                        'skill_type': result[5],
                        'skill_group': result[6],
                        'skill_family': result[7]
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting skill details for '{skill_uri}': {e}")
            return None
    
    def get_related_skills(self, skill_uri: str, relation_type: str = 'related') -> List[Dict[str, Any]]:
        """Get related skills for a given skill URI."""
        if not skill_uri:
            return []
        
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT target_skill_uri, target_skill_name, relation_type
                    FROM get_related_esco_skills(%s, %s)
                """, (skill_uri, relation_type))
                
                results = cursor.fetchall()
                related_skills = []
                
                for result in results:
                    related_skills.append({
                        'skill_uri': result[0],
                        'skill_name': result[1],
                        'relation_type': result[2]
                    })
                
                return related_skills
                
        except Exception as e:
            logger.error(f"Error getting related skills for '{skill_uri}': {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test database connection and ESCO function."""
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()
                
                # Test basic connection
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
                # Test ESCO function
                cursor.execute("SELECT search_esco_skills('test', 'es', 0.0)")
                cursor.fetchall()
                
                logger.info("✅ ESCO matcher connection test successful")
                return True
                
        except Exception as e:
            logger.error(f"❌ ESCO matcher connection test failed: {e}")
            return False 