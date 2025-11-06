"""
Metrics Calculator - Cálculo de métricas de evaluación para pipelines.

Métricas implementadas:
- Precision: % de skills extraídos que están en gold standard
- Recall: % de skills del gold standard detectados
- F1-Score: Media armónica de Precision y Recall
- Accuracy: % de predicciones correctas (TP + TN) / Total
- False Positives: Skills extraídos que NO están en gold standard
- False Negatives: Skills del gold standard que NO fueron detectados
- True Positives: Skills correctamente identificados
- Confusion Matrix: Matriz 2x2 de clasificación
"""

from typing import List, Set, Dict, Any, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConfusionMatrix:
    """Matriz de confusión para clasificación binaria."""
    true_positives: int  # TP: Correctamente identificados
    false_positives: int  # FP: Identificados pero incorrectos
    true_negatives: int  # TN: Correctamente NO identificados
    false_negatives: int  # FN: NO identificados pero deberían

    @property
    def total(self) -> int:
        """Total de predicciones."""
        return self.true_positives + self.false_positives + self.true_negatives + self.false_negatives

    def to_dict(self) -> Dict[str, int]:
        """Convierte a diccionario."""
        return {
            'true_positives': self.true_positives,
            'false_positives': self.false_positives,
            'true_negatives': self.true_negatives,
            'false_negatives': self.false_negatives,
            'total': self.total
        }


@dataclass
class EvaluationMetrics:
    """Métricas de evaluación de un pipeline."""
    precision: float  # TP / (TP + FP)
    recall: float  # TP / (TP + FN)
    f1_score: float  # 2 * (P * R) / (P + R)
    accuracy: float  # (TP + TN) / Total
    support: int  # Total de skills en gold standard
    predicted_count: int  # Total de skills predichos
    confusion_matrix: ConfusionMatrix
    true_positives_list: List[str]  # Lista de TPs
    false_positives_list: List[str]  # Lista de FPs
    false_negatives_list: List[str]  # Lista de FNs

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'precision': round(self.precision, 4),
            'recall': round(self.recall, 4),
            'f1_score': round(self.f1_score, 4),
            'accuracy': round(self.accuracy, 4),
            'support': self.support,
            'predicted_count': self.predicted_count,
            'confusion_matrix': self.confusion_matrix.to_dict(),
            'true_positives_count': len(self.true_positives_list),
            'false_positives_count': len(self.false_positives_list),
            'false_negatives_count': len(self.false_negatives_list),
        }

    def to_summary_dict(self) -> Dict[str, Any]:
        """Diccionario resumido (sin listas detalladas)."""
        return {
            'precision': round(self.precision, 4),
            'recall': round(self.recall, 4),
            'f1_score': round(self.f1_score, 4),
            'accuracy': round(self.accuracy, 4),
            'support': self.support,
            'predicted_count': self.predicted_count,
        }


class MetricsCalculator:
    """Calculador de métricas de evaluación."""

    def __init__(self):
        """Inicializa el calculador."""
        pass

    def calculate(
        self,
        gold_standard_skills: Set[str],
        predicted_skills: Set[str]
    ) -> EvaluationMetrics:
        """
        Calcula métricas comparando predicted vs gold standard.

        Args:
            gold_standard_skills: Set de skills del gold standard (ground truth)
            predicted_skills: Set de skills predichos por el pipeline

        Returns:
            EvaluationMetrics con todas las métricas calculadas
        """
        # Calcular conjuntos
        true_positives_set = gold_standard_skills & predicted_skills  # Intersección
        false_positives_set = predicted_skills - gold_standard_skills  # Predichos pero incorrectos
        false_negatives_set = gold_standard_skills - predicted_skills  # No predichos pero deberían

        # True Negatives es conceptualmente infinito (todas las skills NO en ambos)
        # Para propósitos prácticos, lo calculamos como 0 o lo estimamos
        # En este contexto, TN no es relevante para nuestras métricas principales
        true_negatives = 0

        # Counts
        tp = len(true_positives_set)
        fp = len(false_positives_set)
        fn = len(false_negatives_set)
        tn = true_negatives

        # Confusion Matrix
        confusion = ConfusionMatrix(
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn
        )

        # Precision: TP / (TP + FP)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

        # Recall: TP / (TP + FN)
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        # F1-Score: 2 * (P * R) / (P + R)
        f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Accuracy: (TP + TN) / Total
        # En este contexto, accuracy no es tan relevante como F1
        total = tp + fp + tn + fn
        accuracy = (tp + tn) / total if total > 0 else 0.0

        # Support (total en gold standard)
        support = len(gold_standard_skills)

        # Predicted count
        predicted_count = len(predicted_skills)

        # Listas detalladas
        true_positives_list = sorted(list(true_positives_set))
        false_positives_list = sorted(list(false_positives_set))
        false_negatives_list = sorted(list(false_negatives_set))

        metrics = EvaluationMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            accuracy=accuracy,
            support=support,
            predicted_count=predicted_count,
            confusion_matrix=confusion,
            true_positives_list=true_positives_list,
            false_positives_list=false_positives_list,
            false_negatives_list=false_negatives_list
        )

        logger.info(f"Metrics calculated: P={precision:.4f}, R={recall:.4f}, F1={f1_score:.4f}")
        logger.debug(f"  TP={tp}, FP={fp}, FN={fn}")

        return metrics

    def calculate_aggregate(
        self,
        all_gold_skills: List[Set[str]],
        all_predicted_skills: List[Set[str]]
    ) -> EvaluationMetrics:
        """
        Calcula métricas agregadas para múltiples jobs.

        Args:
            all_gold_skills: Lista de sets de skills gold standard (1 por job)
            all_predicted_skills: Lista de sets de skills predichos (1 por job)

        Returns:
            EvaluationMetrics agregadas
        """
        if len(all_gold_skills) != len(all_predicted_skills):
            raise ValueError("Número de gold standard y predicted skills no coincide")

        # Opción 1: Micro-averaging (combinar todos los jobs en un solo set)
        combined_gold = set()
        combined_predicted = set()

        for gold, predicted in zip(all_gold_skills, all_predicted_skills):
            combined_gold.update(gold)
            combined_predicted.update(predicted)

        return self.calculate(combined_gold, combined_predicted)

    def calculate_per_job(
        self,
        all_gold_skills: List[Set[str]],
        all_predicted_skills: List[Set[str]]
    ) -> Tuple[EvaluationMetrics, List[EvaluationMetrics]]:
        """
        Calcula métricas agregadas + métricas por job individual.

        Args:
            all_gold_skills: Lista de sets de skills gold standard
            all_predicted_skills: Lista de sets de skills predichos

        Returns:
            Tuple de (métricas agregadas, lista de métricas por job)
        """
        # Calcular métricas por job
        per_job_metrics = []
        for gold, predicted in zip(all_gold_skills, all_predicted_skills):
            job_metrics = self.calculate(gold, predicted)
            per_job_metrics.append(job_metrics)

        # Calcular métricas agregadas (micro-averaging)
        aggregate_metrics = self.calculate_aggregate(all_gold_skills, all_predicted_skills)

        return aggregate_metrics, per_job_metrics

    def calculate_macro_average(
        self,
        per_job_metrics: List[EvaluationMetrics]
    ) -> Dict[str, float]:
        """
        Calcula macro-average de métricas (promedio simple de métricas por job).

        Args:
            per_job_metrics: Lista de métricas por job

        Returns:
            Dict con promedios de precision, recall, f1
        """
        if not per_job_metrics:
            return {
                'precision_macro': 0.0,
                'recall_macro': 0.0,
                'f1_score_macro': 0.0
            }

        total_precision = sum(m.precision for m in per_job_metrics)
        total_recall = sum(m.recall for m in per_job_metrics)
        total_f1 = sum(m.f1_score for m in per_job_metrics)
        n = len(per_job_metrics)

        return {
            'precision_macro': total_precision / n,
            'recall_macro': total_recall / n,
            'f1_score_macro': total_f1 / n
        }


# Función de conveniencia

def calculate_metrics(
    gold_standard_skills: Set[str],
    predicted_skills: Set[str]
) -> EvaluationMetrics:
    """
    Calcula métricas (función de conveniencia).

    Args:
        gold_standard_skills: Set de skills gold standard
        predicted_skills: Set de skills predichos

    Returns:
        EvaluationMetrics
    """
    calculator = MetricsCalculator()
    return calculator.calculate(gold_standard_skills, predicted_skills)


def compare_pipelines(
    gold_standard_skills: Set[str],
    pipeline_a_skills: Set[str],
    pipeline_b_skills: Set[str]
) -> Dict[str, EvaluationMetrics]:
    """
    Compara dos pipelines contra gold standard.

    Args:
        gold_standard_skills: Set de skills gold standard
        pipeline_a_skills: Set de skills Pipeline A
        pipeline_b_skills: Set de skills Pipeline B

    Returns:
        Dict con métricas de cada pipeline
    """
    calculator = MetricsCalculator()

    metrics_a = calculator.calculate(gold_standard_skills, pipeline_a_skills)
    metrics_b = calculator.calculate(gold_standard_skills, pipeline_b_skills)

    return {
        'pipeline_a': metrics_a,
        'pipeline_b': metrics_b
    }


def print_metrics(metrics: EvaluationMetrics, pipeline_name: str = "Pipeline"):
    """
    Imprime métricas de manera legible.

    Args:
        metrics: Métricas calculadas
        pipeline_name: Nombre del pipeline
    """
    print(f"\n{'='*60}")
    print(f"{pipeline_name} - Evaluation Metrics")
    print(f"{'='*60}")
    print(f"Precision:       {metrics.precision:.4f} ({metrics.precision*100:.2f}%)")
    print(f"Recall:          {metrics.recall:.4f} ({metrics.recall*100:.2f}%)")
    print(f"F1-Score:        {metrics.f1_score:.4f} ({metrics.f1_score*100:.2f}%)")
    print(f"Accuracy:        {metrics.accuracy:.4f} ({metrics.accuracy*100:.2f}%)")
    print(f"\nSupport (Gold):  {metrics.support} skills")
    print(f"Predicted:       {metrics.predicted_count} skills")
    print(f"\nConfusion Matrix:")
    print(f"  True Positives:  {metrics.confusion_matrix.true_positives}")
    print(f"  False Positives: {metrics.confusion_matrix.false_positives}")
    print(f"  False Negatives: {metrics.confusion_matrix.false_negatives}")
    print(f"{'='*60}\n")
