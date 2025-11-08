"""
Dual Pipeline Comparator - Comparación en 2 niveles:
1. Extracción Pura (texto normalizado)
2. Post-Mapeo ESCO (estandarización)

Este módulo implementa la estrategia acordada de comparación justa:
- Comparación 1: Evalúa capacidad de extracción sin bias de ESCO
- Comparación 2: Evalúa estandarización usando el MISMO código de mapeo
"""

from typing import List, Dict, Set, Any, Tuple, Optional
from dataclasses import dataclass
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

from .normalizer import SkillNormalizer
from .metrics import MetricsCalculator, EvaluationMetrics
from ..extractor.esco_matcher_3layers import ESCOMatcher3Layers
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class PipelineData:
    """Datos de un pipeline para evaluación."""
    name: str
    skills_by_job: Dict[str, Set[str]]  # job_id -> set of skill_texts
    skills_with_types: Dict[str, Dict[str, str]]  # job_id -> {skill_text: skill_type}
    total_skills: int
    unique_skills: int

    def filter_by_type(self, skill_type: Optional[str]) -> 'PipelineData':
        """
        Filtra skills por tipo.

        Args:
            skill_type: 'hard', 'soft', o None (ambos)

        Returns:
            Nuevo PipelineData con skills filtradas
        """
        if skill_type is None:
            return self

        filtered_skills_by_job = {}
        filtered_skills_with_types = {}
        total = 0

        for job_id, skills in self.skills_by_job.items():
            job_type_mapping = self.skills_with_types.get(job_id, {})

            # Filtrar skills de este job por tipo
            filtered_skills = {
                skill for skill in skills
                if job_type_mapping.get(skill) == skill_type
            }

            if filtered_skills:
                filtered_skills_by_job[job_id] = filtered_skills
                filtered_skills_with_types[job_id] = {
                    skill: skill_type for skill in filtered_skills
                }
                total += len(filtered_skills)

        unique = len(set().union(*filtered_skills_by_job.values())) if filtered_skills_by_job else 0

        return PipelineData(
            name=f"{self.name} ({skill_type})",
            skills_by_job=filtered_skills_by_job,
            skills_with_types=filtered_skills_with_types,
            total_skills=total,
            unique_skills=unique
        )


@dataclass
class ComparisonResult:
    """Resultado de una comparación (texto o ESCO)."""
    comparison_type: str  # "pure_text" o "post_esco"
    pipeline_name: str
    metrics: EvaluationMetrics
    coverage_esco: Optional[float] = None  # % skills mapeadas a ESCO
    skills_lost_in_mapping: Optional[List[str]] = None  # Skills perdidas en mapeo


@dataclass
class DualComparisonReport:
    """Reporte completo de comparación dual."""
    # Comparación 1: Texto normalizado
    pure_text_results: Dict[str, ComparisonResult]  # pipeline_name -> result

    # Comparación 2: Post-ESCO
    post_esco_results: Dict[str, ComparisonResult]  # pipeline_name -> result

    # Análisis de impacto ESCO
    esco_impact: Dict[str, Dict[str, Any]]  # pipeline_name -> impact analysis

    # Skills emergentes (no en ESCO)
    emergent_skills: List[str]

    # Metadatos
    total_jobs: int
    pipeline_names: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'pure_text_results': {
                name: {
                    'metrics': result.metrics.to_summary_dict(),
                    'pipeline_name': result.pipeline_name
                }
                for name, result in self.pure_text_results.items()
            },
            'post_esco_results': {
                name: {
                    'metrics': result.metrics.to_summary_dict(),
                    'coverage_esco': result.coverage_esco,
                    'skills_lost_count': len(result.skills_lost_in_mapping) if result.skills_lost_in_mapping else 0
                }
                for name, result in self.post_esco_results.items()
            },
            'esco_impact': self.esco_impact,
            'emergent_skills_count': len(self.emergent_skills),
            'emergent_skills': self.emergent_skills[:20],  # Primeras 20
            'total_jobs': self.total_jobs,
            'pipeline_names': self.pipeline_names
        }


class DualPipelineComparator:
    """Compara pipelines en 2 niveles: texto normalizado y post-ESCO."""

    def __init__(self):
        """Inicializa el comparador."""
        self.settings = get_settings()
        self.normalizer = SkillNormalizer()
        self.metrics_calculator = MetricsCalculator()
        self.esco_matcher = ESCOMatcher3Layers()

        # Database connection
        self.db_url = self.settings.database_url
        if self.db_url.startswith('postgresql://'):
            self.db_url = self.db_url.replace('postgresql://', 'postgres://')

        logger.info("DualPipelineComparator initialized")

    def load_gold_standard(self) -> PipelineData:
        """
        Carga gold standard desde la base de datos.

        Returns:
            PipelineData con skills del gold standard
        """
        logger.info("Loading gold standard from database...")

        skills_by_job = {}
        skills_with_types = {}
        total_skills = 0

        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Cargar gold standard annotations
                    cursor.execute("""
                        SELECT job_id, skill_text, skill_type
                        FROM gold_standard_annotations
                        ORDER BY job_id, skill_text
                    """)

                    rows = cursor.fetchall()

                    for row in rows:
                        job_id = str(row['job_id'])
                        skill_text = row['skill_text']
                        skill_type = row['skill_type']

                        if job_id not in skills_by_job:
                            skills_by_job[job_id] = set()
                            skills_with_types[job_id] = {}

                        skills_by_job[job_id].add(skill_text)
                        skills_with_types[job_id][skill_text] = skill_type
                        total_skills += 1

            unique_skills = len(set().union(*skills_by_job.values()))

            logger.info(f"✅ Gold Standard loaded: {len(skills_by_job)} jobs, {total_skills} skills, {unique_skills} unique")

            return PipelineData(
                name="Gold Standard",
                skills_by_job=skills_by_job,
                skills_with_types=skills_with_types,
                total_skills=total_skills,
                unique_skills=unique_skills
            )

        except Exception as e:
            logger.error(f"Error loading gold standard: {e}")
            raise

    def load_pipeline_a(self, job_ids: Optional[List[str]] = None) -> PipelineData:
        """
        Carga skills extraídas por Pipeline A (NER+Regex).

        Args:
            job_ids: Lista de job IDs a cargar (None = todos)

        Returns:
            PipelineData con skills de Pipeline A
        """
        logger.info("Loading Pipeline A results from database...")

        skills_by_job = {}
        skills_with_types = {}
        total_skills = 0

        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Query base
                    if job_ids:
                        placeholders = ','.join(['%s'] * len(job_ids))
                        query = f"""
                            SELECT job_id, skill_text, skill_type
                            FROM extracted_skills
                            WHERE job_id IN ({placeholders})
                            ORDER BY job_id, skill_text
                        """
                        cursor.execute(query, job_ids)
                    else:
                        query = """
                            SELECT job_id, skill_text, skill_type
                            FROM extracted_skills
                            ORDER BY job_id, skill_text
                        """
                        cursor.execute(query)

                    rows = cursor.fetchall()

                    for row in rows:
                        job_id = str(row['job_id'])
                        skill_text = row['skill_text']
                        skill_type = row['skill_type'] or 'unknown'  # Default si es NULL

                        if job_id not in skills_by_job:
                            skills_by_job[job_id] = set()
                            skills_with_types[job_id] = {}

                        skills_by_job[job_id].add(skill_text)
                        skills_with_types[job_id][skill_text] = skill_type
                        total_skills += 1

            unique_skills = len(set().union(*skills_by_job.values())) if skills_by_job else 0

            logger.info(f"✅ Pipeline A loaded: {len(skills_by_job)} jobs, {total_skills} skills, {unique_skills} unique")

            return PipelineData(
                name="Pipeline A (NER+Regex)",
                skills_by_job=skills_by_job,
                skills_with_types=skills_with_types,
                total_skills=total_skills,
                unique_skills=unique_skills
            )

        except Exception as e:
            logger.error(f"Error loading Pipeline A: {e}")
            raise

    def load_pipeline_a1(self, job_ids: Optional[List[str]] = None, persist_to_db: bool = False) -> PipelineData:
        """
        Ejecuta Pipeline A.1 (N-gram + TF-IDF) y retorna skills extraídas.

        A diferencia de Pipeline A y B que leen de DB, este pipeline
        ejecuta extracción en tiempo real usando NGramExtractor.

        Args:
            job_ids: Lista de job IDs a procesar (None = todos los gold standard)
            persist_to_db: Si True, guarda las skills extraídas en extracted_skills table

        Returns:
            PipelineData con skills de Pipeline A.1
        """
        from ..extractor.ngram_extractor import NGramExtractor

        logger.info("Running Pipeline A.1 (N-gram + TF-IDF) extraction...")

        skills_by_job = {}
        skills_with_types = {}
        total_skills = 0

        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Step 1: Cargar corpus de textos para fitting TF-IDF
                    logger.info("  [1/4] Loading corpus for TF-IDF fitting...")
                    if job_ids:
                        placeholders = ','.join(['%s'] * len(job_ids))
                        query = f"""
                            SELECT cj.job_id, cj.combined_text
                            FROM cleaned_jobs cj
                            JOIN raw_jobs rj ON cj.job_id = rj.job_id
                            WHERE rj.is_gold_standard = TRUE
                              AND cj.job_id IN ({placeholders})
                            ORDER BY cj.job_id
                        """
                        cursor.execute(query, job_ids)
                    else:
                        query = """
                            SELECT cj.job_id, cj.combined_text
                            FROM cleaned_jobs cj
                            JOIN raw_jobs rj ON cj.job_id = rj.job_id
                            WHERE rj.is_gold_standard = TRUE
                            ORDER BY cj.job_id
                        """
                        cursor.execute(query)

                    rows = cursor.fetchall()
                    job_texts = [(row['job_id'], row['combined_text']) for row in rows if row['combined_text']]

                    if not job_texts:
                        logger.warning("No job texts found!")
                        return PipelineData(
                            name="Pipeline A.1 (N-gram + TF-IDF)",
                            skills_by_job={},
                            skills_with_types={},
                            total_skills=0,
                            unique_skills=0
                        )

                    logger.info(f"  ✅ Loaded {len(job_texts)} job texts")

                    # Step 2: Fit TF-IDF on corpus
                    logger.info("  [2/4] Fitting TF-IDF on corpus...")
                    extractor = NGramExtractor()
                    corpus = [text for _, text in job_texts]
                    extractor.fit_corpus(corpus)

                    # Step 3: Extract skills from each job
                    logger.info(f"  [3/4] Extracting skills from {len(job_texts)} jobs...")
                    for idx, (job_id, text) in enumerate(job_texts, 1):
                        ngram_skills = extractor.extract_skills(text)

                        # Convert NGramSkill to skill_text for PipelineData format
                        if job_id not in skills_by_job:
                            skills_by_job[job_id] = set()
                            skills_with_types[job_id] = {}

                        for skill in ngram_skills:
                            skills_by_job[job_id].add(skill.skill_text)
                            # Pipeline A.1 solo extrae hard skills (no clasifica soft/hard)
                            skills_with_types[job_id][skill.skill_text] = 'hard'
                            total_skills += 1

                        if idx % 50 == 0:
                            logger.info(f"    Progress: {idx}/{len(job_texts)} ({idx/len(job_texts)*100:.1f}%)")

                    logger.info(f"  ✅ Extracted {total_skills} skills from {len(skills_by_job)} jobs")

                    # Step 4: Persist to database if requested
                    if persist_to_db:
                        logger.info("  [4/4] Persisting skills to database...")
                        self._persist_pipeline_a1_skills(skills_by_job, skills_with_types)

            unique_skills = len(set().union(*skills_by_job.values())) if skills_by_job else 0

            logger.info(f"✅ Pipeline A.1 complete: {len(skills_by_job)} jobs, {total_skills} skills, {unique_skills} unique")

            return PipelineData(
                name="Pipeline A.1 (N-gram + TF-IDF)",
                skills_by_job=skills_by_job,
                skills_with_types=skills_with_types,
                total_skills=total_skills,
                unique_skills=unique_skills
            )

        except Exception as e:
            logger.error(f"Error running Pipeline A.1: {e}")
            raise

    def _persist_pipeline_a1_skills(self, skills_by_job: Dict[str, Set[str]], skills_with_types: Dict[str, Dict[str, str]]):
        """
        Persiste skills de Pipeline A.1 en extracted_skills table.

        Args:
            skills_by_job: Dict[job_id -> Set[skill_text]]
            skills_with_types: Dict[job_id -> Dict[skill_text -> skill_type]]
        """
        EXTRACTION_METHOD = 'pipeline-a1-tfidf-np'

        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cursor:
                    # Delete existing Pipeline A.1 extractions for these jobs
                    job_ids = list(skills_by_job.keys())
                    if job_ids:
                        placeholders = ','.join(['%s'] * len(job_ids))
                        delete_query = f"""
                            DELETE FROM extracted_skills
                            WHERE job_id IN ({placeholders})
                              AND extraction_method = %s
                        """
                        cursor.execute(delete_query, job_ids + [EXTRACTION_METHOD])
                        deleted_count = cursor.rowcount
                        logger.info(f"    Deleted {deleted_count} existing Pipeline A.1 skills")

                    # Insert new skills
                    insert_query = """
                        INSERT INTO extracted_skills (
                            job_id, skill_text, skill_type,
                            extraction_method, source_section, confidence_score
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """

                    skills_to_insert = []
                    for job_id, skills in skills_by_job.items():
                        for skill_text in skills:
                            skill_type = skills_with_types.get(job_id, {}).get(skill_text, 'hard')
                            skills_to_insert.append((
                                job_id,
                                skill_text,
                                skill_type,
                                EXTRACTION_METHOD,
                                'combined_text',  # Pipeline A.1 procesa combined_text
                                None  # Confidence score (podría agregarse TF-IDF score después)
                            ))

                    if skills_to_insert:
                        cursor.executemany(insert_query, skills_to_insert)
                        conn.commit()
                        logger.info(f"    ✅ Inserted {len(skills_to_insert)} Pipeline A.1 skills into database")
                    else:
                        logger.warning("    No skills to insert")

        except Exception as e:
            logger.error(f"Error persisting Pipeline A.1 skills: {e}")
            raise

    def load_pipeline_b(
        self,
        llm_model: str,
        job_ids: Optional[List[str]] = None
    ) -> PipelineData:
        """
        Carga skills extraídas por Pipeline B (LLM).

        Args:
            llm_model: Nombre del modelo LLM (ej: "llama-3.2-3b-instruct")
            job_ids: Lista de job IDs a cargar (None = todos)

        Returns:
            PipelineData con skills de Pipeline B
        """
        logger.info(f"Loading Pipeline B ({llm_model}) results from database...")

        skills_by_job = {}
        skills_with_types = {}
        total_skills = 0

        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Query con filtros
                    if job_ids:
                        placeholders = ','.join(['%s'] * len(job_ids))
                        query = f"""
                            SELECT job_id, normalized_skill, skill_type
                            FROM enhanced_skills
                            WHERE llm_model = %s
                              AND job_id IN ({placeholders})
                            ORDER BY job_id, normalized_skill
                        """
                        cursor.execute(query, [llm_model] + job_ids)
                    else:
                        query = """
                            SELECT job_id, normalized_skill, skill_type
                            FROM enhanced_skills
                            WHERE llm_model = %s
                            ORDER BY job_id, normalized_skill
                        """
                        cursor.execute(query, (llm_model,))

                    rows = cursor.fetchall()

                    for row in rows:
                        job_id = str(row['job_id'])
                        skill_text = row['normalized_skill']
                        skill_type = row['skill_type'] or 'unknown'  # Default si es NULL

                        if job_id not in skills_by_job:
                            skills_by_job[job_id] = set()
                            skills_with_types[job_id] = {}

                        skills_by_job[job_id].add(skill_text)
                        skills_with_types[job_id][skill_text] = skill_type
                        total_skills += 1

            unique_skills = len(set().union(*skills_by_job.values())) if skills_by_job else 0

            logger.info(f"✅ Pipeline B ({llm_model}) loaded: {len(skills_by_job)} jobs, {total_skills} skills, {unique_skills} unique")

            return PipelineData(
                name=f"Pipeline B ({llm_model})",
                skills_by_job=skills_by_job,
                skills_with_types=skills_with_types,
                total_skills=total_skills,
                unique_skills=unique_skills
            )

        except Exception as e:
            logger.error(f"Error loading Pipeline B: {e}")
            raise

    def compare_pure_text(
        self,
        gold_standard: PipelineData,
        pipeline: PipelineData
    ) -> ComparisonResult:
        """
        Comparación 1: Extracción pura con texto normalizado.

        Args:
            gold_standard: Datos del gold standard
            pipeline: Datos del pipeline a evaluar

        Returns:
            ComparisonResult
        """
        logger.info(f"Comparing {pipeline.name} vs Gold Standard (pure text)...")

        # Normalizar todos los skills
        normalized_gold_by_job = {}
        normalized_pipeline_by_job = {}

        # Obtener job IDs comunes (solo evaluar jobs que están en ambos)
        common_job_ids = set(gold_standard.skills_by_job.keys()) & set(pipeline.skills_by_job.keys())

        if not common_job_ids:
            logger.warning(f"No common job IDs between gold standard and {pipeline.name}")
            # Retornar métricas vacías
            empty_metrics = self.metrics_calculator.calculate(set(), set())
            return ComparisonResult(
                comparison_type="pure_text",
                pipeline_name=pipeline.name,
                metrics=empty_metrics
            )

        logger.info(f"Evaluating on {len(common_job_ids)} common jobs")

        # Normalizar skills por job
        for job_id in common_job_ids:
            # Normalizar gold standard
            gold_skills = gold_standard.skills_by_job[job_id]
            normalized_gold = set(self.normalizer.normalize_list(list(gold_skills)))
            normalized_gold_by_job[job_id] = normalized_gold

            # Normalizar pipeline
            pipeline_skills = pipeline.skills_by_job[job_id]
            normalized_pipeline = set(self.normalizer.normalize_list(list(pipeline_skills)))
            normalized_pipeline_by_job[job_id] = normalized_pipeline

        # Combinar todos los jobs para calcular métricas agregadas
        all_gold = set().union(*normalized_gold_by_job.values())
        all_pipeline = set().union(*normalized_pipeline_by_job.values())

        # Calcular métricas
        metrics = self.metrics_calculator.calculate(all_gold, all_pipeline)

        logger.info(f"✅ Pure text comparison complete: F1={metrics.f1_score:.4f}")

        return ComparisonResult(
            comparison_type="pure_text",
            pipeline_name=pipeline.name,
            metrics=metrics
        )

    def compare_post_esco(
        self,
        gold_standard: PipelineData,
        pipeline: PipelineData
    ) -> ComparisonResult:
        """
        Comparación 2: Post-mapeo ESCO con el MISMO código de mapeo.

        Args:
            gold_standard: Datos del gold standard
            pipeline: Datos del pipeline a evaluar

        Returns:
            ComparisonResult con métricas y análisis de cobertura ESCO
        """
        logger.info(f"Comparing {pipeline.name} vs Gold Standard (post-ESCO)...")

        # Job IDs comunes
        common_job_ids = set(gold_standard.skills_by_job.keys()) & set(pipeline.skills_by_job.keys())

        if not common_job_ids:
            logger.warning(f"No common job IDs")
            empty_metrics = self.metrics_calculator.calculate(set(), set())
            return ComparisonResult(
                comparison_type="post_esco",
                pipeline_name=pipeline.name,
                metrics=empty_metrics,
                coverage_esco=0.0,
                skills_lost_in_mapping=[]
            )

        # Paso 1: Normalizar todos los skills
        normalized_gold_skills = set()
        normalized_pipeline_skills = set()

        for job_id in common_job_ids:
            gold_skills = gold_standard.skills_by_job[job_id]
            normalized_gold_skills.update(self.normalizer.normalize_list(list(gold_skills)))

            pipeline_skills = pipeline.skills_by_job[job_id]
            normalized_pipeline_skills.update(self.normalizer.normalize_list(list(pipeline_skills)))

        # Paso 2: Mapear TODOS a ESCO usando el MISMO código
        logger.info(f"Mapping {len(normalized_gold_skills)} gold standard skills to ESCO...")
        gold_esco_matches = self.esco_matcher.batch_match_skills(list(normalized_gold_skills))

        logger.info(f"Mapping {len(normalized_pipeline_skills)} pipeline skills to ESCO...")
        pipeline_esco_matches = self.esco_matcher.batch_match_skills(list(normalized_pipeline_skills))

        # Paso 3: Extraer ESCO URIs (solo skills que se mapearon)
        gold_esco_uris = {match.esco_skill_uri for match in gold_esco_matches.values() if match}
        pipeline_esco_uris = {match.esco_skill_uri for match in pipeline_esco_matches.values() if match}

        # Paso 4: Calcular métricas usando ESCO URIs
        metrics = self.metrics_calculator.calculate(gold_esco_uris, pipeline_esco_uris)

        # Paso 5: Calcular cobertura ESCO
        gold_mapped_count = len([m for m in gold_esco_matches.values() if m])
        pipeline_mapped_count = len([m for m in pipeline_esco_matches.values() if m])

        gold_coverage = gold_mapped_count / len(normalized_gold_skills) if normalized_gold_skills else 0
        pipeline_coverage = pipeline_mapped_count / len(normalized_pipeline_skills) if normalized_pipeline_skills else 0

        logger.info(f"  Gold Standard ESCO coverage: {gold_coverage:.2%}")
        logger.info(f"  Pipeline ESCO coverage: {pipeline_coverage:.2%}")

        # Paso 6: Identificar skills perdidas en mapeo
        pipeline_unmapped = [
            skill for skill, match in pipeline_esco_matches.items() if not match
        ]

        logger.info(f"✅ Post-ESCO comparison complete: F1={metrics.f1_score:.4f}")

        return ComparisonResult(
            comparison_type="post_esco",
            pipeline_name=pipeline.name,
            metrics=metrics,
            coverage_esco=pipeline_coverage,
            skills_lost_in_mapping=pipeline_unmapped
        )

    def analyze_esco_impact(
        self,
        pure_result: ComparisonResult,
        esco_result: ComparisonResult
    ) -> Dict[str, Any]:
        """
        Analiza el impacto del mapeo a ESCO en las métricas.

        Args:
            pure_result: Resultado de comparación pura
            esco_result: Resultado de comparación post-ESCO

        Returns:
            Dict con análisis de impacto
        """
        delta_f1 = esco_result.metrics.f1_score - pure_result.metrics.f1_score
        delta_precision = esco_result.metrics.precision - pure_result.metrics.precision
        delta_recall = esco_result.metrics.recall - pure_result.metrics.recall

        impact = {
            'delta_f1': delta_f1,
            'delta_precision': delta_precision,
            'delta_recall': delta_recall,
            'delta_f1_percent': (delta_f1 / pure_result.metrics.f1_score * 100) if pure_result.metrics.f1_score > 0 else 0,
            'esco_coverage': esco_result.coverage_esco,
            'skills_lost_count': len(esco_result.skills_lost_in_mapping) if esco_result.skills_lost_in_mapping else 0,
            'skills_lost_sample': esco_result.skills_lost_in_mapping[:10] if esco_result.skills_lost_in_mapping else []
        }

        logger.info(f"ESCO impact: ΔF1 = {delta_f1:+.4f} ({impact['delta_f1_percent']:+.2f}%)")

        return impact

    def run_dual_comparison(
        self,
        gold_standard: PipelineData,
        pipelines: List[PipelineData],
        skill_type_filter: Optional[str] = None
    ) -> DualComparisonReport:
        """
        Ejecuta comparación dual completa para múltiples pipelines.

        Args:
            gold_standard: Datos del gold standard
            pipelines: Lista de pipelines a evaluar
            skill_type_filter: Filtrar por 'hard', 'soft', o None (ambos)

        Returns:
            DualComparisonReport con resultados completos
        """
        logger.info(f"Running dual comparison for {len(pipelines)} pipelines...")
        if skill_type_filter:
            logger.info(f"  Filtering by skill_type: {skill_type_filter}")

        # Filtrar datos si se especifica tipo
        filtered_gold = gold_standard.filter_by_type(skill_type_filter)
        filtered_pipelines = [p.filter_by_type(skill_type_filter) for p in pipelines]

        # Comparación 1: Texto normalizado
        pure_text_results = {}
        for pipeline in filtered_pipelines:
            result = self.compare_pure_text(filtered_gold, pipeline)
            pure_text_results[pipeline.name] = result

        # Comparación 2: Post-ESCO
        post_esco_results = {}
        for pipeline in filtered_pipelines:
            result = self.compare_post_esco(filtered_gold, pipeline)
            post_esco_results[pipeline.name] = result

        # Análisis de impacto ESCO
        esco_impact = {}
        for pipeline_name in pure_text_results.keys():
            impact = self.analyze_esco_impact(
                pure_text_results[pipeline_name],
                post_esco_results[pipeline_name]
            )
            esco_impact[pipeline_name] = impact

        # Identificar skills emergentes (perdidas en mapeo ESCO)
        all_emergent = set()
        for result in post_esco_results.values():
            if result.skills_lost_in_mapping:
                all_emergent.update(result.skills_lost_in_mapping)

        emergent_skills = sorted(list(all_emergent))

        # Crear reporte
        report = DualComparisonReport(
            pure_text_results=pure_text_results,
            post_esco_results=post_esco_results,
            esco_impact=esco_impact,
            emergent_skills=emergent_skills,
            total_jobs=len(filtered_gold.skills_by_job),
            pipeline_names=[p.name for p in filtered_pipelines]
        )

        logger.info(f"✅ Dual comparison complete!")
        logger.info(f"   Total jobs evaluated: {report.total_jobs}")
        logger.info(f"   Emergent skills identified: {len(emergent_skills)}")

        return report

    def compare_llms_head_to_head(
        self,
        llm_models: List[str],
        job_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compara múltiples LLMs entre sí (sin gold standard).

        Calcula estadísticas agregadas: promedio de skills/job, overlap entre modelos,
        velocidad, etc.

        Args:
            llm_models: Lista de nombres de modelos LLM
            job_ids: IDs de jobs a analizar (None = todos)

        Returns:
            Dict con análisis comparativo
        """
        logger.info(f"Comparing {len(llm_models)} LLMs head-to-head...")

        # Cargar datos de cada LLM
        llm_data = {}
        for model in llm_models:
            pipeline = self.load_pipeline_b(llm_model=model, job_ids=job_ids)
            llm_data[model] = pipeline

        # Estadísticas básicas
        stats = {}
        for model, pipeline in llm_data.items():
            all_skills = set().union(*pipeline.skills_by_job.values()) if pipeline.skills_by_job else set()
            avg_skills = pipeline.total_skills / len(pipeline.skills_by_job) if pipeline.skills_by_job else 0

            stats[model] = {
                'total_jobs': len(pipeline.skills_by_job),
                'total_skills': pipeline.total_skills,
                'unique_skills': len(all_skills),
                'avg_skills_per_job': avg_skills
            }

        # Overlap entre modelos (Jaccard similarity)
        if len(llm_models) >= 2:
            overlaps = {}
            for i, model1 in enumerate(llm_models):
                for model2 in llm_models[i+1:]:
                    skills1 = set().union(*llm_data[model1].skills_by_job.values())
                    skills2 = set().union(*llm_data[model2].skills_by_job.values())

                    intersection = len(skills1 & skills2)
                    union = len(skills1 | skills2)
                    jaccard = intersection / union if union > 0 else 0

                    overlaps[f"{model1}_vs_{model2}"] = {
                        'jaccard_similarity': jaccard,
                        'common_skills': intersection,
                        'total_unique': union
                    }
        else:
            overlaps = {}

        logger.info(f"✅ Head-to-head comparison complete")

        return {
            'models_compared': llm_models,
            'statistics': stats,
            'overlaps': overlaps
        }

    def evaluate_pipeline_without_gold(
        self,
        pipeline: PipelineData,
        map_to_esco: bool = True
    ) -> Dict[str, Any]:
        """
        Evalúa un pipeline sin gold standard (análisis descriptivo).

        Args:
            pipeline: Datos del pipeline
            map_to_esco: Si True, mapea a ESCO y calcula cobertura

        Returns:
            Dict con análisis descriptivo
        """
        logger.info(f"Evaluating {pipeline.name} (no gold standard)...")

        # Skills únicos
        all_skills = set().union(*pipeline.skills_by_job.values()) if pipeline.skills_by_job else set()

        # Normalizar
        normalized_skills = self.normalizer.normalize_list(list(all_skills))

        analysis = {
            'pipeline_name': pipeline.name,
            'total_jobs': len(pipeline.skills_by_job),
            'total_skill_extractions': pipeline.total_skills,
            'unique_skills': len(all_skills),
            'unique_skills_normalized': len(normalized_skills),
            'avg_skills_per_job': pipeline.total_skills / len(pipeline.skills_by_job) if pipeline.skills_by_job else 0
        }

        # Mapear a ESCO si se solicita
        if map_to_esco:
            logger.info(f"  Mapping {len(normalized_skills)} skills to ESCO...")
            esco_matches = self.esco_matcher.batch_match_skills(normalized_skills)

            mapped_count = len([m for m in esco_matches.values() if m])
            unmapped = [skill for skill, match in esco_matches.items() if not match]

            analysis['esco_coverage'] = mapped_count / len(normalized_skills) if normalized_skills else 0
            analysis['esco_mapped_count'] = mapped_count
            analysis['esco_unmapped_count'] = len(unmapped)
            analysis['esco_unmapped_sample'] = unmapped[:20]

        logger.info(f"✅ Evaluation complete: {analysis['unique_skills']} unique skills, avg {analysis['avg_skills_per_job']:.1f}/job")

        return analysis
