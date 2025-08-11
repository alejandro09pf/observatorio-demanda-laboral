from typing import List, Dict, Any, Optional
import logging
from .esco_matcher import ESCOMatcher

logger = logging.getLogger(__name__)

class ESCONormalizer:
    """Normalizes skills using ESCO taxonomy."""
    
    def __init__(self):
        self.esco_matcher = ESCOMatcher()
    
    def normalize_skill(self, skill_text: str) -> Optional[Dict[str, Any]]:
        """Normalize a skill using ESCO taxonomy."""
        # TODO: Implement skill normalization
        pass
    
    def normalize_skills(self, skills: List[str]) -> List[Dict[str, Any]]:
        """Normalize multiple skills."""
        # TODO: Implement batch skill normalization
        pass 