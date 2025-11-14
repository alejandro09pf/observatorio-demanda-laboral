"""
Labor Market Observatory - Main FastAPI Application

REST API for accessing labor market data, skill analysis, and clustering results.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import logging
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import routers
from api.routers import stats, jobs, skills, clusters, temporal, admin_celery, admin_llm

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Labor Market Observatory API",
    description="REST API for Latin American labor market analysis and skill demand insights",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:3001",  # Dev server alternative port
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (clustering outputs, visualizations)
outputs_path = Path(__file__).parent.parent.parent / "outputs"
if outputs_path.exists():
    app.mount("/api/static", StaticFiles(directory=str(outputs_path)), name="static")
    logger.info(f"Mounted static files from {outputs_path}")

# Include routers
app.include_router(stats.router, prefix="/api", tags=["Statistics"])
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])
app.include_router(skills.router, prefix="/api", tags=["Skills"])
app.include_router(clusters.router, prefix="/api", tags=["Clustering"])
app.include_router(temporal.router, prefix="/api", tags=["Temporal Analysis"])
app.include_router(admin_celery.router, prefix="/api/admin", tags=["Administration"])
app.include_router(admin_llm.router, tags=["LLM Pipeline B"])


@app.get("/")
def read_root():
    """Root endpoint - API information."""
    return {
        "name": "Labor Market Observatory API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/api/docs",
        "endpoints": {
            "stats": "/api/stats",
            "jobs": "/api/jobs",
            "skills": "/api/skills",
            "clusters": "/api/clusters",
            "temporal": "/api/temporal",
            "admin": "/api/admin"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "labor-observatory-api"
    }


@app.get("/api/ping")
def ping():
    """Simple ping endpoint for testing."""
    return {"message": "pong"}


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "path": str(request.url)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
