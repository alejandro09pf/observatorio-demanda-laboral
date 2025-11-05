"""
LLM Benchmarking System - Compare multiple LLM models for skill extraction quality.
Evaluates speed, accuracy, ESCO matching quality, and cost.
"""

from typing import List, Dict, Any, Optional
import logging
import time
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

from .llm_handler import LLMHandler
from .pipeline import LLMProcessingPipeline
from .model_registry import MODEL_REGISTRY, DEFAULT_COMPARISON_MODELS
from ..config.settings import get_settings
from ..database.operations import DatabaseOperations

logger = logging.getLogger(__name__)


class LLMBenchmark:
    """Benchmark and compare LLM models for skill extraction."""

    def __init__(
        self,
        output_dir: Optional[str] = None
    ):
        """
        Initialize benchmarking system.

        Args:
            output_dir: Directory to save benchmark results
        """
        self.settings = get_settings()
        self.output_dir = Path(output_dir or self.settings.benchmark_output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db_ops = DatabaseOperations()

    def run_comparison(
        self,
        models: Optional[List[str]] = None,
        sample_size: int = 50,
        job_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run benchmark comparison across multiple models.

        Args:
            models: List of model names to compare (or None for defaults)
            sample_size: Number of jobs to process per model
            job_ids: Specific job IDs to use (or None for random sample)

        Returns:
            Comparison results with statistics
        """
        models = models or DEFAULT_COMPARISON_MODELS

        logger.info(f"Starting benchmark comparison for {len(models)} models")
        logger.info(f"Models: {models}")
        logger.info(f"Sample size: {sample_size} jobs")

        # Get sample jobs
        if job_ids:
            sample_jobs = [self.db_ops.get_job_by_id(jid) for jid in job_ids[:sample_size]]
            sample_jobs = [j for j in sample_jobs if j]
        else:
            sample_jobs = self.db_ops.get_sample_jobs_for_benchmark(limit=sample_size)

        if not sample_jobs:
            logger.error("No sample jobs available for benchmarking")
            return {"status": "error", "error": "No sample jobs"}

        logger.info(f"Using {len(sample_jobs)} jobs for benchmark")

        # Run benchmark for each model
        results = []
        for model_name in models:
            logger.info(f"\n{'='*60}")
            logger.info(f"Benchmarking: {model_name}")
            logger.info(f"{'='*60}")

            try:
                model_result = self._benchmark_model(model_name, sample_jobs)
                results.append(model_result)

                logger.info(f"✓ {model_name} benchmark complete")
                logger.info(f"  Speed: {model_result['avg_time_per_job']:.2f}s/job")
                logger.info(f"  Skills/job: {model_result['avg_skills_per_job']:.1f}")
                logger.info(f"  Total tokens: {model_result['total_tokens']}")

            except Exception as e:
                logger.error(f"Failed to benchmark {model_name}: {e}")
                results.append({
                    "model_name": model_name,
                    "status": "error",
                    "error": str(e)
                })

        # Generate comparison report
        comparison = self._generate_comparison_report(results)

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"benchmark_comparison_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"\n✓ Benchmark complete. Results saved to: {output_file}")

        # Save CSV summary
        self._save_csv_summary(results, timestamp)

        return comparison

    def _benchmark_model(
        self,
        model_name: str,
        sample_jobs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Benchmark a single model."""
        # Initialize pipeline with this model
        pipeline = LLMProcessingPipeline(model_name=model_name)

        # Statistics
        start_time = time.time()
        total_jobs = len(sample_jobs)
        total_skills_processed = 0
        total_skills_enhanced = 0
        total_tokens = 0
        job_times = []
        errors = 0

        # Process each job
        for i, job in enumerate(sample_jobs, 1):
            job_id = job.get('job_id')

            try:
                job_start = time.time()

                # Process job
                result = pipeline.process_job(job_id)

                job_time = time.time() - job_start
                job_times.append(job_time)

                total_skills_processed += result.get('skills_processed', 0)
                total_skills_enhanced += result.get('skills_enhanced', 0)

                if result.get('status') != 'success':
                    errors += 1

                # Progress log
                if i % 10 == 0:
                    logger.info(
                        f"  [{i}/{total_jobs}] "
                        f"Avg time: {sum(job_times)/len(job_times):.2f}s/job"
                    )

            except Exception as e:
                logger.error(f"Error processing job {job_id}: {e}")
                errors += 1

        total_time = time.time() - start_time

        # Calculate statistics
        avg_time_per_job = total_time / total_jobs if total_jobs > 0 else 0
        avg_skills_per_job = total_skills_enhanced / total_jobs if total_jobs > 0 else 0
        success_rate = (total_jobs - errors) / total_jobs * 100 if total_jobs > 0 else 0

        # Get model info
        model_info = pipeline.get_model_info()

        return {
            "model_name": model_name,
            "display_name": model_info.get("display_name", model_name),
            "status": "success",
            "total_jobs": total_jobs,
            "total_skills_processed": total_skills_processed,
            "total_skills_enhanced": total_skills_enhanced,
            "total_time_seconds": round(total_time, 2),
            "avg_time_per_job": round(avg_time_per_job, 2),
            "avg_skills_per_job": round(avg_skills_per_job, 1),
            "total_tokens": total_tokens,
            "success_rate": round(success_rate, 2),
            "errors": errors,
            "model_size_gb": model_info.get("size_gb"),
            "quantization": model_info.get("quantization"),
            "gpu_layers": model_info.get("gpu_layers"),
            "timestamp": datetime.now().isoformat()
        }

    def _generate_comparison_report(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate comparison report from benchmark results."""
        successful_results = [r for r in results if r.get('status') == 'success']

        if not successful_results:
            return {
                "status": "error",
                "error": "No successful benchmarks",
                "results": results
            }

        # Find best models
        best_speed = min(successful_results, key=lambda x: x['avg_time_per_job'])
        best_quality = max(successful_results, key=lambda x: x['avg_skills_per_job'])
        most_reliable = max(successful_results, key=lambda x: x['success_rate'])

        # Rankings
        rankings = {
            "by_speed": sorted(
                successful_results,
                key=lambda x: x['avg_time_per_job']
            ),
            "by_quality": sorted(
                successful_results,
                key=lambda x: x['avg_skills_per_job'],
                reverse=True
            ),
            "by_reliability": sorted(
                successful_results,
                key=lambda x: x['success_rate'],
                reverse=True
            )
        }

        return {
            "status": "success",
            "models_tested": len(results),
            "successful_benchmarks": len(successful_results),
            "failed_benchmarks": len(results) - len(successful_results),
            "best_models": {
                "fastest": {
                    "model": best_speed['model_name'],
                    "time_per_job": best_speed['avg_time_per_job']
                },
                "best_quality": {
                    "model": best_quality['model_name'],
                    "skills_per_job": best_quality['avg_skills_per_job']
                },
                "most_reliable": {
                    "model": most_reliable['model_name'],
                    "success_rate": most_reliable['success_rate']
                }
            },
            "rankings": rankings,
            "detailed_results": results,
            "generated_at": datetime.now().isoformat()
        }

    def _save_csv_summary(
        self,
        results: List[Dict[str, Any]],
        timestamp: str
    ):
        """Save comparison as CSV for easy analysis."""
        df = pd.DataFrame(results)

        # Select key columns
        columns = [
            'model_name', 'display_name', 'total_jobs',
            'total_skills_enhanced', 'avg_time_per_job',
            'avg_skills_per_job', 'success_rate',
            'model_size_gb', 'quantization'
        ]

        # Filter to existing columns
        columns = [c for c in columns if c in df.columns]
        df_summary = df[columns]

        # Save
        csv_file = self.output_dir / f"benchmark_summary_{timestamp}.csv"
        df_summary.to_csv(csv_file, index=False)

        logger.info(f"CSV summary saved to: {csv_file}")

    def quality_evaluation(
        self,
        model_name: str,
        gold_standard_jobs: List[Dict[str, Any]],
        ground_truth_skills: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Evaluate model quality against gold standard annotations.

        Args:
            model_name: Model to evaluate
            gold_standard_jobs: Jobs with manual annotations
            ground_truth_skills: Dict mapping job_id -> list of correct skills

        Returns:
            Quality metrics (precision, recall, F1)
        """
        logger.info(f"Running quality evaluation for {model_name}")

        pipeline = LLMProcessingPipeline(model_name=model_name)

        total_tp = 0  # True positives
        total_fp = 0  # False positives
        total_fn = 0  # False negatives

        for job in gold_standard_jobs:
            job_id = job.get('job_id')
            ground_truth = set(ground_truth_skills.get(job_id, []))

            # Process job
            result = pipeline.process_job(job_id)

            # Get predicted skills
            predicted_skills = self.db_ops.get_enhanced_skills_by_job(job_id)
            predicted = set(
                skill.get('normalized_skill', '').lower()
                for skill in predicted_skills
            )

            # Calculate metrics
            tp = len(predicted & ground_truth)
            fp = len(predicted - ground_truth)
            fn = len(ground_truth - predicted)

            total_tp += tp
            total_fp += fp
            total_fn += fn

        # Calculate overall metrics
        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "model_name": model_name,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(f1_score, 3),
            "true_positives": total_tp,
            "false_positives": total_fp,
            "false_negatives": total_fn,
            "total_jobs_evaluated": len(gold_standard_jobs)
        }

    def generate_comparison_report_markdown(
        self,
        comparison_data: Dict[str, Any]
    ) -> str:
        """Generate a markdown report from comparison data."""
        md = ["# LLM Benchmark Comparison Report\n"]
        md.append(f"**Generated:** {comparison_data.get('generated_at')}\n")
        md.append(f"**Models Tested:** {comparison_data.get('models_tested')}\n\n")

        # Best models
        md.append("## Best Models\n\n")
        best = comparison_data.get('best_models', {})

        md.append(f"- **Fastest:** {best.get('fastest', {}).get('model')} "
                 f"({best.get('fastest', {}).get('time_per_job')}s/job)\n")
        md.append(f"- **Best Quality:** {best.get('best_quality', {}).get('model')} "
                 f"({best.get('best_quality', {}).get('skills_per_job')} skills/job)\n")
        md.append(f"- **Most Reliable:** {best.get('most_reliable', {}).get('model')} "
                 f"({best.get('most_reliable', {}).get('success_rate')}% success rate)\n\n")

        # Detailed results table
        md.append("## Detailed Results\n\n")
        md.append("| Model | Time/Job (s) | Skills/Job | Success Rate | Size (GB) |\n")
        md.append("|-------|--------------|------------|--------------|----------|\n")

        for result in comparison_data.get('detailed_results', []):
            if result.get('status') == 'success':
                md.append(
                    f"| {result['model_name']} | "
                    f"{result['avg_time_per_job']} | "
                    f"{result['avg_skills_per_job']} | "
                    f"{result['success_rate']}% | "
                    f"{result.get('model_size_gb', 'N/A')} |\n"
                )

        return "".join(md)
