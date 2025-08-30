import spacy
from spacy.tokens import Doc, Span
from typing import List, Dict, Tuple, Optional, Any
import logging
import os
from pathlib import Path
from dataclasses import dataclass
from config.settings import get_settings
import re

logger = logging.getLogger(__name__)

@dataclass
class NERSkill:
    """Represents a skill found by NER."""
    skill_text: str
    skill_type: str
    confidence: float
    position: tuple
    context: str
    ner_label: str
    extraction_method: str

class NERExtractor:
    """Extract skills using Named Entity Recognition."""
    
    def __init__(self, model_path: Optional[str] = None):
        self.settings = get_settings()
        self.nlp = None
        
        # Load spaCy model
        if model_path and Path(model_path).exists():
            try:
                self.nlp = spacy.load(model_path)
                logger.info(f"Loaded custom NER model from {model_path}")
            except Exception as e:
                logger.warning(f"Failed to load custom model: {e}")
                self._load_default_model()
        else:
            self._load_default_model()
        
        # Add custom pipeline components
        if self.nlp:
            self._add_tech_entity_ruler()
    
    def _load_default_model(self):
        """Load default spaCy model."""
        try:
            # Try Spanish model first
            self.nlp = spacy.load("es_core_news_sm")
            logger.info("Loaded Spanish spaCy model")
        except OSError:
            try:
                # Fallback to English
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded English spaCy model")
            except OSError:
                logger.warning("No spaCy models found. NER extraction will be disabled.")
                self.nlp = None
    
    def _add_tech_entity_ruler(self):
        """Add rule-based entity recognition for tech terms."""
        if not self.nlp:
            return
        
        # Add patterns for technical skills
        patterns = [
            {"label": "TECH_SKILL", "pattern": [{"LOWER": "python"}]},
            {"label": "TECH_SKILL", "pattern": [{"LOWER": "react"}]},
            {"label": "TECH_SKILL", "pattern": [{"LOWER": "docker"}]},
            {"label": "TECH_SKILL", "pattern": [{"LOWER": "aws"}]},
            {"label": "TECH_SKILL", "pattern": [{"LOWER": "postgresql"}]},
            {"label": "TECH_SKILL", "pattern": [{"LOWER": "git"}]},
        ]
        
        ruler = self.nlp.add_pipe("entity_ruler", before="ner")
        ruler.add_patterns(patterns)
        logger.info("Added custom entity ruler for tech skills")
    
    def extract_skills(self, text: str) -> List[NERSkill]:
        """Extract skills from text using NER."""
        if not text or not self.nlp:
            return []
        
        logger.info(f"Extracting skills with NER from text (length: {len(text)})")
        skills = []
        
        try:
            doc = self.nlp(text)
            
            # Extract named entities
            for ent in doc.ents:
                if self._is_technical_skill(ent.text):
                    skill = NERSkill(
                        skill_text=ent.text,
                        skill_type='ner_entity',
                        confidence=0.6,
                        position=(ent.start_char, ent.end_char),
                        context=ent.sent.text.strip(),
                        ner_label=ent.label_,
                        extraction_method='ner'
                    )
                    skills.append(skill)
            
            # Extract noun phrases that might be skills
            for chunk in doc.noun_chunks:
                if self._is_technical_skill(chunk.text):
                    skill = NERSkill(
                        skill_text=chunk.text,
                        skill_type='noun_chunk',
                        confidence=0.5,
                        position=(chunk.start_char, chunk.end_char),
                        context=chunk.sent.text.strip(),
                        ner_label='NOUN_CHUNK',
                        extraction_method='ner'
                    )
                    skills.append(skill)
            
            # Remove duplicates
            unique_skills = self._deduplicate_skills(skills)
            logger.info(f"Found {len(unique_skills)} unique skills with NER")
            return unique_skills
            
        except Exception as e:
            logger.error(f"Error in NER extraction: {e}")
            return []
    
    def _is_technical_skill(self, text: str) -> bool:
        """Check if text looks like a technical skill."""
        text_lower = text.lower()
        
        # Technical indicators
        tech_indicators = [
            'framework', 'library', 'tool', 'platform', 'service',
            'database', 'language', 'technology', 'stack', 'api',
            'cloud', 'devops', 'frontend', 'backend', 'fullstack'
        ]
        
        # Check for technical terms
        for indicator in tech_indicators:
            if indicator in text_lower:
                return True
        
        # Check for common tech patterns
        tech_patterns = [
            r'\.js$', r'\.py$', r'\.net$', r'\.io$', r'\.com$',
            r'^[A-Z][a-z]+$',  # CamelCase
            r'^[A-Z]+$',       # ALL_CAPS
        ]
        
        for pattern in tech_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _deduplicate_skills(self, skills: List[NERSkill]) -> List[NERSkill]:
        """Remove duplicate skills based on normalized text."""
        unique_skills = []
        seen_texts = set()
        
        for skill in skills:
            normalized = skill.skill_text.lower().strip()
            if normalized not in seen_texts:
                seen_texts.add(normalized)
                unique_skills.append(skill)
        
        return unique_skills 