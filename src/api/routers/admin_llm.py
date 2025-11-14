"""
Admin API Router - LLM Pipeline B Management
Simple MVP for downloading Gemma and running Pipeline B
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/llm", tags=["admin-llm"])


class PipelineBRequest(BaseModel):
    limit: int = 100
    country: str | None = None
    model: str = "gemma-3-4b-instruct"


@router.get("/status")
def get_llm_status():
    """
    Check if Gemma model is downloaded and system is ready for Pipeline B.
    """
    try:
        from src.llm_processor.model_downloader import ModelDownloader

        downloader = ModelDownloader()
        model_name = "gemma-3-4b-instruct"

        is_downloaded = downloader.is_model_downloaded(model_name)
        model_info = downloader.get_model_info(model_name) if is_downloaded else None

        return {
            "model_name": model_name,
            "downloaded": is_downloaded,
            "size_gb": 2.8,
            "model_info": model_info,
            "ready": is_downloaded
        }
    except Exception as e:
        logger.error(f"Failed to get LLM status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download-gemma")
def download_gemma(background_tasks: BackgroundTasks):
    """
    Download Gemma 3 4B Instruct model (2.8 GB).
    This runs in background via subprocess.
    """
    try:
        from src.llm_processor.model_downloader import ModelDownloader

        downloader = ModelDownloader()
        model_name = "gemma-3-4b-instruct"

        # Check if already downloaded
        if downloader.is_model_downloaded(model_name):
            return {
                "status": "already_downloaded",
                "message": "Gemma 3 4B is already downloaded",
                "model_name": model_name
            }

        # Start download in background
        def download_task():
            logger.info(f"Starting Gemma download: {model_name}")
            try:
                model_path = downloader.download_model(model_name, force=False, show_progress=True)
                logger.info(f"Gemma downloaded successfully: {model_path}")
            except Exception as e:
                logger.error(f"Gemma download failed: {e}")

        background_tasks.add_task(download_task)

        return {
            "status": "downloading",
            "message": "Gemma 3 4B download started (2.8 GB, may take 5-10 minutes)",
            "model_name": model_name,
            "size_gb": 2.8
        }
    except Exception as e:
        logger.error(f"Failed to start Gemma download: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-pipeline-b")
def run_pipeline_b(request: PipelineBRequest):
    """
    Run Pipeline B (LLM extraction) on N jobs.
    Creates a Celery task for async processing.
    """
    try:
        from src.llm_processor.model_downloader import ModelDownloader
        from src.tasks.llm_tasks import process_jobs_llm_task

        # Verify model is downloaded
        downloader = ModelDownloader()
        if not downloader.is_model_downloaded(request.model):
            raise HTTPException(
                status_code=400,
                detail=f"Model {request.model} is not downloaded. Please download it first."
            )

        # Enqueue Celery task
        task = process_jobs_llm_task.delay(
            limit=request.limit,
            model_name=request.model,
            country=request.country
        )

        return {
            "status": "started",
            "task_id": task.id,
            "message": f"Pipeline B started: processing {request.limit} jobs with {request.model}",
            "limit": request.limit,
            "model": request.model,
            "country": request.country
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start Pipeline B: {e}")
        raise HTTPException(status_code=500, detail=str(e))
