"""
Pipeline A.1: N-gram + TF-IDF Skill Extractor

Academic baseline for statistical skill extraction without deep learning.
Implements corpus-based TF-IDF with domain-aware filtering.

References:
- Salton & Buckley (1988): Term-weighting approaches in automatic text retrieval
- Manning et al. (2008): Introduction to Information Retrieval, Chapter 6
- Zhang et al. (2018): AutoPhrase - Automated Phrase Mining from Massive Text Corpora

Strategy:
1. Corpus-based TF-IDF: Use all gold standard jobs as corpus (prevents single-doc bias)
2. Multi-word n-grams: Capture technical terms like "Machine Learning", "React Native"
3. Domain-aware filtering: Remove noise patterns specific to job postings
4. Adaptive thresholding: Extract variable number of skills based on document length
"""

from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import re
import logging
from pathlib import Path
import spacy

logger = logging.getLogger(__name__)


@dataclass
class NGramSkill:
    """Represents a skill extracted using N-gram + TF-IDF."""
    skill_text: str
    tfidf_score: float
    ngram_length: int  # 1=unigram, 2=bigram, 3=trigram
    extraction_method: str  # Always 'ngram_tfidf'
    confidence: float  # Normalized score [0-1]
    context: str  # Surrounding text
    position: Tuple[int, int]  # (start, end) char positions


class NGramExtractor:
    """
    Extracts skills using corpus-based TF-IDF with N-grams.

    This is an academic baseline to compare against:
    - Pipeline A (NER+Regex): Rule-based extraction
    - Pipeline B (LLM): Neural extraction

    The goal is to demonstrate that simple statistical methods can achieve
    competitive F1 scores (~45-50%) but struggle with normalization.
    """

    # Domain-specific stopwords (bilingual: ES + EN)
    STOPWORDS_SPANISH = [
        # Generic
        'el', 'la', 'los', 'las', 'de', 'en', 'con', 'por', 'para', 'y', 'a', 'o',
        'del', 'al', 'un', 'una', 'unos', 'unas', 'este', 'esta', 'estos', 'estas',
        'ese', 'esa', 'esos', 'esas', 'aquel', 'aquella', 'aquellos', 'aquellas',
        'que', 'cual', 'cuales', 'quien', 'quienes', 'como', 'donde', 'cuando',
        'muy', 'más', 'menos', 'mucho', 'poco', 'tanto', 'todo', 'toda', 'todos', 'todas',
        'si', 'no', 'ni', 'pero', 'sino', 'porque', 'pues', 'aunque', 'sin', 'sobre', 'entre',

        # Job posting noise
        'años', 'año', 'experiencia', 'conocimiento', 'conocimientos', 'requisitos', 'requisito',
        'responsabilidades', 'responsabilidad', 'funciones', 'función', 'tareas', 'tarea',
        'oferta', 'ofertas', 'perfil', 'perfiles', 'candidato', 'candidatos', 'candidata',
        'puesto', 'puestos', 'cargo', 'cargos', 'trabajo', 'trabajos', 'empleo', 'empleos',
        'salario', 'sueldo', 'beneficios', 'beneficio', 'condiciones', 'condición',
        'empresa', 'empresas', 'compañía', 'compañías', 'organización', 'organizaciones',
        'equipo', 'equipos', 'área', 'áreas', 'departamento', 'departamentos',
        'cliente', 'clientes', 'usuario', 'usuarios', 'servicio', 'servicios',
        'proyecto', 'proyectos', 'desarrollo', 'implementación', 'gestión',
        'nivel', 'niveles', 'grado', 'título', 'titulación', 'formación',
        'habilidad', 'habilidades', 'capacidad', 'capacidades', 'competencia', 'competencias',
        'deseable', 'deseables', 'preferible', 'preferibles', 'valorable', 'valorables',
        'necesario', 'necesaria', 'necesarios', 'necesarias', 'requerido', 'requerida',
        'excluyente', 'excluyentes', 'indispensable', 'indispensables',
        'mínimo', 'mínima', 'mínimos', 'mínimas', 'máximo', 'máxima', 'máximos', 'máximas',
        'modalidad', 'jornada', 'horario', 'disponibilidad', 'incorporación', 'inmediata',
        'enviar', 'envío', 'cv', 'postular', 'postularse', 'aplicar', 'inscribirse',

        # Noise from scraping
        'piano', 'cat', 'true', 'false', 'type', 'search', 'title', 'description',
        'null', 'undefined', 'none', 'na', 'n/a', 'error', 'warning',
        'click', 'aquí', 'acá', 'allá', 'ahí', 'ver', 'más', 'info', 'información',
    ]

    STOPWORDS_ENGLISH = [
        # Generic
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could',
        'this', 'that', 'these', 'those', 'what', 'which', 'who', 'when', 'where', 'why', 'how',
        'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such',
        'no', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
        'can', 'just', 'may', 'might', 'must', 'need', 'shall', 'through', 'during',

        # Job posting noise
        'years', 'year', 'experience', 'knowledge', 'requirements', 'requirement',
        'responsibilities', 'responsibility', 'functions', 'function', 'tasks', 'task',
        'offer', 'offers', 'profile', 'profiles', 'candidate', 'candidates',
        'position', 'positions', 'role', 'roles', 'job', 'jobs', 'employment',
        'salary', 'wage', 'benefits', 'benefit', 'conditions', 'condition',
        'company', 'companies', 'organization', 'organizations',
        'team', 'teams', 'area', 'areas', 'department', 'departments',
        'client', 'clients', 'customer', 'customers', 'user', 'users', 'service', 'services',
        'project', 'projects', 'development', 'implementation', 'management',
        'level', 'levels', 'degree', 'education', 'qualification', 'qualifications',
        'skill', 'skills', 'ability', 'abilities', 'competency', 'competencies',
        'desirable', 'preferred', 'preferable', 'valuable',
        'required', 'necessary', 'essential', 'mandatory', 'must',
        'minimum', 'maximum', 'at least', 'up to',
        'modality', 'schedule', 'availability', 'immediate', 'start',
        'send', 'submit', 'apply', 'application', 'resume',

        # Noise from scraping
        'piano', 'cat', 'true', 'false', 'type', 'search', 'title', 'description',
        'null', 'undefined', 'none', 'na', 'error', 'warning',
        'click', 'here', 'there', 'see', 'view', 'info', 'information',
    ]

    # Technical skill indicators (for confidence boosting)
    TECH_INDICATORS = [
        # Programming & frameworks
        'programming', 'programación', 'language', 'lenguaje', 'framework', 'library', 'librería',
        'api', 'sdk', 'ide', 'code', 'código', 'script', 'scripting',

        # Technologies
        'software', 'hardware', 'system', 'sistema', 'platform', 'plataforma',
        'database', 'base de datos', 'server', 'servidor', 'cloud', 'nube',
        'web', 'mobile', 'móvil', 'desktop', 'network', 'red',

        # Methodologies
        'agile', 'ágil', 'scrum', 'devops', 'ci/cd', 'testing', 'qa',
        'methodology', 'metodología', 'architecture', 'arquitectura',

        # Data & AI
        'data', 'datos', 'analytics', 'analítica', 'machine learning', 'ml',
        'artificial intelligence', 'ai', 'inteligencia artificial', 'deep learning',
        'model', 'modelo', 'algorithm', 'algoritmo', 'neural', 'neuronal',

        # Tools
        'tool', 'herramienta', 'suite', 'package', 'paquete', 'module', 'módulo',
        'plugin', 'extension', 'extensión', 'component', 'componente',
    ]

    # Ambiguous words (for confidence penalization)
    AMBIGUOUS_WORDS = [
        'office', 'excel', 'word', 'powerpoint', 'outlook',  # Too generic
        'windows', 'linux', 'mac', 'android', 'ios',  # OS names without context
        'email', 'internet', 'web', 'online',  # Too basic
        'comunicación', 'communication', 'teamwork', 'trabajo en equipo',  # Soft skills
        'liderazgo', 'leadership', 'proactividad', 'proactive',
    ]

    # Additional domain stopwords (detected from iterations 1-2)
    STOPWORDS_DOMAIN = [
        # Administrative/general terms
        'administración', 'administration', 'actividad', 'activity',
        'address', 'about', 'acerca', 'sobre',
        'confidencial', 'confidential', 'vacante', 'vacancy', 'mensual', 'monthly',
        'remota', 'remote', 'presencial', 'onsite', 'hibrido', 'hybrid',
        'tiempo completo', 'full time', 'part time', 'medio tiempo',

        # Iteration 2 additions
        'adopción', 'acompañar', 'administrator', 'against', 'aplica',
        'méxico', 'advanced', 'english', 'alto', 'rendimiento',
        'ambiente', 'colaborativo', 'agentes', 'agentic',
        'analítica', 'analytics', 'análisis', 'analysis',

        # Company/recruitment noise
        'composto', 'talentosos', 'innovate', 'accenture', 'acklen', 'avenue',
        'acreditamos', 'evolução', 'contínua', 'frontend', 'backend',
        'liderando', 'tecnología', 'technology', 'dacoders', 'a-team',

        # Job board artifacts
        'software engineer', 'backend engineer', 'frontend engineer',  # Too generic in isolation
        'senior', 'junior', 'mid', 'lead', 'manager',  # Seniority levels in isolation
    ]

    # Noise patterns (regex-based blacklist)
    NOISE_PATTERNS = [
        r'^\d+$',  # Pure numbers
        r'^\d+[a-z]$',  # "2Innovate", "3D" patterns
        r'^[a-z]$',  # Single letters (except standalone like "R", "C")
        r'^\W+$',  # Pure punctuation
        r'^(https?|www|http)',  # URLs
        r'@',  # Email addresses
        r'^\d+\s*(años?|years?|meses?|months?)$',  # "3 años", "5 years"
        r'^(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)$',  # Months
        r'^(january|february|march|april|may|june|july|august|september|october|november|december)$',
        r'^(lunes|martes|miércoles|jueves|viernes|sábado|domingo)$',  # Days
        r'^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$',
        r'^\d+\s+\w+',  # "000 Confidencial", "220 Talentosos", "15 Liderando"
        r'\d{3,}',  # 3+ consecutive digits (likely noise: "000", "220")
        r'^[A-Z]-[A-Z]',  # Patterns like "A-Team"
    ]

    def __init__(self, use_np_chunking: bool = True):
        """
        Initialize the N-gram extractor.

        Args:
            use_np_chunking: If True, use spaCy NP chunking (Iteration 4).
                             If False, use pure TF-IDF n-grams (Iterations 1-3).
        """
        # Combine ALL stopwords
        all_stopwords = list(set(
            self.STOPWORDS_SPANISH +
            self.STOPWORDS_ENGLISH +
            self.STOPWORDS_DOMAIN
        ))

        # Initialize TF-IDF vectorizer
        # NOTE: This will be fit on the CORPUS (all gold standard jobs), not single documents
        # ITERATION 3 CHANGES (Focus: Increase RECALL):
        # - Relax min_df: 3 → 2 (allow rarer but valid skills)
        # - Keep max_df=0.3, max_features=5000 (working well)
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),  # Unigrams, bigrams, trigrams
            max_df=0.3,  # Ignore terms in >30% of docs
            min_df=2,  # ↓ Relaxed from 3 (allow skills in ≥2 docs)
            stop_words=all_stopwords,
            lowercase=True,
            strip_accents=None,  # Keep accents for Spanish
            token_pattern=r'(?u)\b[\w#+\-.]+\b',  # Keep technical chars: C#, C++, .NET
            max_features=5000,
            sublinear_tf=True,  # Use log-scaling for term frequency
        )

        self.is_fitted = False
        self.feature_names = None
        self.use_np_chunking = use_np_chunking

        # ITERATION 4: Initialize spaCy for NP chunking
        if self.use_np_chunking:
            try:
                self.nlp = spacy.load("es_core_news_sm", disable=["ner"])  # Disable NER for speed
                logger.info("✅ NGramExtractor initialized with NP Chunking (spaCy loaded)")
            except OSError:
                logger.warning("⚠️  Spanish spaCy model not found. Falling back to pure TF-IDF.")
                self.use_np_chunking = False
                self.nlp = None
                logger.info("✅ NGramExtractor initialized (TF-IDF only, no NP chunking)")
        else:
            self.nlp = None
            logger.info("✅ NGramExtractor initialized (TF-IDF only, NP chunking disabled)")

    def fit_corpus(self, corpus: List[str]) -> None:
        """
        Fit the TF-IDF vectorizer on a corpus of documents.

        Args:
            corpus: List of text documents (job descriptions)
        """
        logger.info(f"Fitting TF-IDF on corpus of {len(corpus)} documents...")

        try:
            self.vectorizer.fit(corpus)
            self.feature_names = self.vectorizer.get_feature_names_out()
            self.is_fitted = True

            logger.info(f"✅ TF-IDF fitted - Vocabulary size: {len(self.feature_names):,}")
            logger.info(f"   N-gram examples: {list(self.feature_names[:10])}")

        except Exception as e:
            logger.error(f"❌ Error fitting TF-IDF: {e}")
            raise

    def _extract_noun_phrases(self, text: str) -> List[str]:
        """
        Extract noun phrases using spaCy POS tagging and chunking.

        Patterns extracted:
        1. PROPN+ : Proper nouns (Python, Docker, React)
        2. (ADJ)* NOUN+ : Noun phrases (Machine Learning, Data Science)
        3. Technical acronyms: All-caps words ≥2 chars (API, SQL, AWS)

        Args:
            text: Input text

        Returns:
            List of noun phrase strings
        """
        if not self.nlp:
            return []

        doc = self.nlp(text)
        noun_phrases = []

        # Pattern 1: Proper nouns (PROPN sequences)
        i = 0
        while i < len(doc):
            if doc[i].pos_ == "PROPN":
                # Collect consecutive proper nouns
                propn_sequence = []
                j = i
                while j < len(doc) and doc[j].pos_ == "PROPN":
                    propn_sequence.append(doc[j].text)
                    j += 1

                if propn_sequence:
                    phrase = " ".join(propn_sequence)
                    noun_phrases.append(phrase)
                    i = j
            else:
                i += 1

        # Pattern 2: Adjective + Noun sequences
        i = 0
        while i < len(doc):
            # Start with optional adjectives
            phrase_tokens = []

            # Collect leading adjectives
            while i < len(doc) and doc[i].pos_ == "ADJ":
                phrase_tokens.append(doc[i].text)
                i += 1

            # Require at least one noun
            noun_count = 0
            while i < len(doc) and doc[i].pos_ == "NOUN":
                phrase_tokens.append(doc[i].text)
                noun_count += 1
                i += 1

            # Only accept if we have at least one noun
            if noun_count > 0 and phrase_tokens:
                phrase = " ".join(phrase_tokens)
                noun_phrases.append(phrase)
            else:
                i += 1

        # Pattern 3: Technical acronyms (all-caps, ≥2 chars)
        for token in doc:
            if token.text.isupper() and len(token.text) >= 2 and token.text.isalpha():
                noun_phrases.append(token.text)

        # Deduplicate while preserving order
        seen = set()
        unique_nps = []
        for np in noun_phrases:
            np_lower = np.lower()
            if np_lower not in seen and len(np) >= 2:  # Min 2 chars
                seen.add(np_lower)
                unique_nps.append(np)

        return unique_nps

    def extract_skills(self, text: str, top_k: Optional[int] = None) -> List[NGramSkill]:
        """
        Extract skills from a single document using fitted TF-IDF.

        ITERATION 4: If use_np_chunking=True, extract noun phrases first,
        then rank them with TF-IDF. Otherwise use pure TF-IDF n-grams.

        Args:
            text: Job description text
            top_k: Number of top skills to extract. If None, uses adaptive threshold.

        Returns:
            List of NGramSkill objects, sorted by confidence (descending)
        """
        if not self.is_fitted:
            raise RuntimeError("TF-IDF not fitted! Call fit_corpus() first.")

        if not text or len(text.strip()) < 10:
            return []

        # ITERATION 4: Branch based on NP chunking mode
        if self.use_np_chunking:
            return self._extract_skills_with_np_chunking(text, top_k)
        else:
            return self._extract_skills_tfidf_only(text, top_k)

    def _extract_skills_tfidf_only(self, text: str, top_k: Optional[int]) -> List[NGramSkill]:
        """
        Original TF-IDF n-gram extraction (Iterations 1-3).

        This generates n-grams from TF-IDF vocabulary without entity boundaries.
        """
        # Step 1: Transform text to TF-IDF vector
        try:
            tfidf_vector = self.vectorizer.transform([text])
        except Exception as e:
            logger.error(f"Error transforming text: {e}")
            return []

        # Step 2: Get non-zero features (n-grams present in this document)
        nonzero_indices = tfidf_vector.nonzero()[1]

        if len(nonzero_indices) == 0:
            return []

        # Step 3: Extract (n-gram, tfidf_score) pairs
        candidates = []
        for idx in nonzero_indices:
            ngram = self.feature_names[idx]
            score = tfidf_vector[0, idx]

            # Calculate n-gram length
            ngram_length = len(ngram.split())

            candidates.append({
                'ngram': ngram,
                'score': float(score),
                'length': ngram_length
            })

        # Step 4: Filter candidates
        filtered = self._filter_candidates(candidates, text)

        # Step 5: Determine top-K (adaptive or fixed)
        if top_k is None:
            # ITERATION 3: Increased top_k to boost recall
            # Adaptive: Extract more skills from longer documents
            word_count = len(text.split())
            if word_count < 100:
                top_k = 10  # ↑ from 5
            elif word_count < 300:
                top_k = 20  # ↑ from 10
            elif word_count < 500:
                top_k = 30  # ↑ from 15
            else:
                top_k = 40  # ↑ from 20

        # Step 6: Sort by confidence and take top-K
        filtered = sorted(filtered, key=lambda x: x['confidence'], reverse=True)[:top_k]

        # Step 7: Convert to NGramSkill objects
        skills = []
        for item in filtered:
            # Find context (surrounding text)
            context, position = self._find_context(text, item['ngram'])

            skill = NGramSkill(
                skill_text=item['ngram'],
                tfidf_score=item['score'],
                ngram_length=item['length'],
                extraction_method='ngram_tfidf',
                confidence=item['confidence'],
                context=context,
                position=position
            )
            skills.append(skill)

        return skills

    def _extract_skills_with_np_chunking(self, text: str, top_k: Optional[int]) -> List[NGramSkill]:
        """
        ITERATION 4: Extract skills using NP chunking + TF-IDF ranking.

        Strategy:
        1. Extract noun phrases using spaCy POS tagging (entity boundaries)
        2. Score each NP using TF-IDF (if exists in vocabulary)
        3. Filter and rank by confidence
        4. Return top-K

        This solves the entity boundary problem:
        - "Python" extraído como "Python" (no "programación python")
        - "Machine Learning" extraído como "Machine Learning" (no "learning algorithms")
        """
        # Step 1: Extract noun phrases with entity boundaries
        noun_phrases = self._extract_noun_phrases(text)

        if not noun_phrases:
            return []

        # Step 2: Score NPs using TF-IDF
        # Transform text to get TF-IDF vector
        try:
            tfidf_vector = self.vectorizer.transform([text])
        except Exception as e:
            logger.error(f"Error transforming text: {e}")
            return []

        # Create lookup dict: feature_name -> tfidf_score
        feature_scores = {}
        nonzero_indices = tfidf_vector.nonzero()[1]
        for idx in nonzero_indices:
            feature_name = self.feature_names[idx]
            feature_scores[feature_name.lower()] = float(tfidf_vector[0, idx])

        # Step 3: Score each NP
        candidates = []
        for np in noun_phrases:
            np_lower = np.lower()

            # Try exact match in TF-IDF vocabulary
            score = feature_scores.get(np_lower, 0.0)

            # If not found, try matching individual tokens (fallback)
            if score == 0.0:
                tokens = np_lower.split()
                token_scores = [feature_scores.get(t, 0.0) for t in tokens]
                if token_scores:
                    # Use average of token scores as fallback
                    score = sum(token_scores) / len(token_scores)

            # Only keep NPs with non-zero score
            if score > 0:
                candidates.append({
                    'ngram': np,
                    'score': score,
                    'length': len(np.split())
                })

        if not candidates:
            return []

        # Step 4: Filter candidates (same filters as TF-IDF only)
        filtered = self._filter_candidates(candidates, text)

        # Step 5: Determine top-K (same adaptive logic)
        if top_k is None:
            word_count = len(text.split())
            if word_count < 100:
                top_k = 10
            elif word_count < 300:
                top_k = 20
            elif word_count < 500:
                top_k = 30
            else:
                top_k = 40

        # Step 6: Sort by confidence and take top-K
        filtered = sorted(filtered, key=lambda x: x['confidence'], reverse=True)[:top_k]

        # Step 7: Convert to NGramSkill objects
        skills = []
        for item in filtered:
            # Find context (surrounding text)
            context, position = self._find_context(text, item['ngram'])

            skill = NGramSkill(
                skill_text=item['ngram'],
                tfidf_score=item['score'],
                ngram_length=item['length'],
                extraction_method='np_chunking_tfidf',  # Different method name
                confidence=item['confidence'],
                context=context,
                position=position
            )
            skills.append(skill)

        return skills

    def _filter_candidates(self, candidates: List[Dict], full_text: str) -> List[Dict]:
        """
        Apply domain-aware filtering to candidate n-grams.

        Filters:
        1. Length: 2-50 characters
        2. Noise patterns: regex blacklist
        3. Substring elimination: keep longest n-gram
        4. Confidence scoring: boost/penalize based on content

        Args:
            candidates: List of {ngram, score, length} dicts
            full_text: Original document (for context)

        Returns:
            Filtered list with added 'confidence' field
        """
        filtered = []

        for item in candidates:
            ngram = item['ngram']

            # Filter 1: Length (2-50 chars)
            if len(ngram) < 2 or len(ngram) > 50:
                continue

            # Filter 2: Noise patterns
            if self._is_noise_pattern(ngram):
                continue

            # Filter 3: Calculate confidence score
            confidence = self._calculate_confidence(ngram, item['score'])

            # ITERATION 3: Lowered threshold 0.15 → 0.08 (prioritize recall)
            # Strategy: Better to have false positives filtered by ESCO
            if confidence < 0.08:
                continue

            item['confidence'] = confidence
            filtered.append(item)

        # Filter 4: Eliminate substrings (keep longest n-gram)
        filtered = self._eliminate_substrings(filtered)

        return filtered

    def _is_noise_pattern(self, ngram: str) -> bool:
        """Check if n-gram matches a noise pattern."""
        for pattern in self.NOISE_PATTERNS:
            if re.search(pattern, ngram, re.IGNORECASE):
                return True
        return False

    def _calculate_confidence(self, ngram: str, tfidf_score: float) -> float:
        """
        Calculate confidence score with domain-aware adjustments.

        Formula:
            base = tfidf_score (already normalized by sklearn)
            boost = +0.15 if contains tech indicator
            penalty = -0.25 if contains ambiguous word
            final = clip(base + boost + penalty, 0.0, 1.0)

        Args:
            ngram: The n-gram text
            tfidf_score: Raw TF-IDF score

        Returns:
            Confidence score [0.0-1.0]
        """
        confidence = tfidf_score

        ngram_lower = ngram.lower()

        # Boost: Contains technical indicator
        if any(indicator in ngram_lower for indicator in self.TECH_INDICATORS):
            confidence += 0.15

        # Penalty: Contains ambiguous word
        if any(amb in ngram_lower for amb in self.AMBIGUOUS_WORDS):
            confidence -= 0.25

        # Boost: Multi-word technical terms (bigrams/trigrams are often more specific)
        if len(ngram.split()) >= 2:
            confidence += 0.05

        # Clip to [0.0, 1.0]
        return max(0.0, min(1.0, confidence))

    def _eliminate_substrings(self, candidates: List[Dict]) -> List[Dict]:
        """
        Eliminate n-grams that are substrings of longer n-grams.

        Example: If "machine learning" is present, remove "machine" and "learning"

        Args:
            candidates: List of candidate dicts

        Returns:
            Filtered list with substrings removed
        """
        if len(candidates) <= 1:
            return candidates

        # Sort by n-gram length (descending) to prioritize longer terms
        sorted_candidates = sorted(candidates, key=lambda x: len(x['ngram']), reverse=True)

        kept = []
        kept_ngrams = set()

        for item in sorted_candidates:
            ngram = item['ngram']

            # Check if this n-gram is a substring of any already kept n-gram
            is_substring = False
            for kept_ngram in kept_ngrams:
                # Use word boundaries to avoid false positives
                # E.g., "python" should not eliminate "python programming"
                if ngram in kept_ngram and ngram != kept_ngram:
                    # Additional check: only eliminate if it's a proper substring
                    # (not just character overlap)
                    words_current = set(ngram.split())
                    words_kept = set(kept_ngram.split())
                    if words_current.issubset(words_kept):
                        is_substring = True
                        break

            if not is_substring:
                kept.append(item)
                kept_ngrams.add(ngram)

        return kept

    def _find_context(self, text: str, ngram: str, context_window: int = 50) -> Tuple[str, Tuple[int, int]]:
        """
        Find the context (surrounding text) for an n-gram.

        Args:
            text: Full document text
            ngram: N-gram to find
            context_window: Characters before/after to include

        Returns:
            (context_string, (start_pos, end_pos))
        """
        # Case-insensitive search
        pattern = re.compile(re.escape(ngram), re.IGNORECASE)
        match = pattern.search(text)

        if not match:
            # Fallback: return empty context
            return "", (0, 0)

        start = match.start()
        end = match.end()

        # Extract context window
        context_start = max(0, start - context_window)
        context_end = min(len(text), end + context_window)

        context = text[context_start:context_end]

        return context, (start, end)

    def get_extraction_stats(self, skills_list: List[List[NGramSkill]]) -> Dict:
        """
        Get statistics about extracted skills across multiple documents.

        Args:
            skills_list: List of skill lists (one per document)

        Returns:
            Dictionary with statistics
        """
        total_docs = len(skills_list)
        total_skills = sum(len(skills) for skills in skills_list)

        if total_skills == 0:
            return {
                'total_documents': total_docs,
                'total_skills': 0,
                'avg_skills_per_doc': 0.0,
                'unique_skills': 0,
                'ngram_distribution': {}
            }

        # Collect all skills
        all_skills = [skill.skill_text for skills in skills_list for skill in skills]
        unique_skills = set(all_skills)

        # N-gram distribution
        ngram_dist = {1: 0, 2: 0, 3: 0}
        for skills in skills_list:
            for skill in skills:
                ngram_dist[skill.ngram_length] = ngram_dist.get(skill.ngram_length, 0) + 1

        return {
            'total_documents': total_docs,
            'total_skills': total_skills,
            'avg_skills_per_doc': total_skills / total_docs,
            'unique_skills': len(unique_skills),
            'ngram_distribution': {
                'unigrams': ngram_dist.get(1, 0),
                'bigrams': ngram_dist.get(2, 0),
                'trigrams': ngram_dist.get(3, 0),
            },
            'avg_confidence': np.mean([skill.confidence for skills in skills_list for skill in skills])
        }
