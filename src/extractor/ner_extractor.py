import spacy
from spacy.tokens import Doc, Span
from typing import List, Dict, Tuple, Optional
import logging
import os
from config.settings import get_settings

logger = logging.getLogger(__name__)

class NERExtractor:
    """Extract skills using Named Entity Recognition."""
    
    def __init__(self, model_path: Optional[str] = None):
        self.settings = get_settings()
        
        # Load spaCy model
        if model_path and os.path.exists(model_path):
            self.nlp = spacy.load(model_path)
            logger.info(f"Loaded custom NER model from {model_path}")
        else:
            # Load default Spanish model
            try:
                self.nlp = spacy.load("es_core_news_lg")
                logger.info("Loaded default Spanish model")
            except:
                logger.warning("Spanish model not found, downloading...")
                os.system("python -m spacy download es_core_news_lg")
                self.nlp = spacy.load("es_core_news_lg")
        
        # Add custom pipeline components
        self._add_tech_entity_ruler()
    
    def _add_tech_entity_ruler(self):
        """Add rule-based entity recognition for tech terms."""
        # TODO: Implement entity ruler for technical skills
        pass
    
    def extract_skills(self, text: str) -> List[Dict[str, Any]]:
        """Extract skills from text using NER."""
        # TODO: Implement skill extraction logic
        pass 