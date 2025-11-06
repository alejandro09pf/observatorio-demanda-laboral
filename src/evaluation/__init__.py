"""
Evaluation Module - Sistema de evaluación de pipelines de extracción.

Este módulo proporciona herramientas para evaluar y comparar:
- Pipeline A (NER + Regex + ESCO)
- Pipeline B (LLM Direct Extraction)

Modos de evaluación:
1. vs Gold Standard - Evaluación completa con ground truth
2. Head-to-head - Comparar LLMs entre sí
3. Descriptive - Análisis sin gold standard

Comparaciones:
- Texto normalizado (sin mapeo ESCO)
- Post-mapeo ESCO (estandarización)
- Análisis de impacto ESCO
"""

from .normalizer import SkillNormalizer, normalize_skill, normalize_skills_list
from .metrics import MetricsCalculator, calculate_metrics, print_metrics
from .dual_comparator import DualPipelineComparator, PipelineData

__all__ = [
    # Normalización
    'SkillNormalizer',
    'normalize_skill',
    'normalize_skills_list',

    # Métricas
    'MetricsCalculator',
    'calculate_metrics',
    'print_metrics',

    # Comparación
    'DualPipelineComparator',
    'PipelineData',
]
