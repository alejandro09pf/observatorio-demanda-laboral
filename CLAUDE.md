# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Labor Market Observatory** - An automated system for monitoring technical skill demands in Latin American labor markets using AI, NLP, and data analysis. The system scrapes job postings, extracts skills using NER + Regex + ESCO taxonomy, and analyzes trends across Colombia (CO), México (MX), and Argentina (AR).

**Current Status**: Phases 1-2 Complete (Foundation & Database), Scraping Working, Extraction Pipeline Operational

## Common Commands

### Development & Testing

```bash
# Main CLI entry point (ALL commands go through this)
python -m src.orchestrator <command>

# System status and health
python -m src.orchestrator status              # Database stats, job counts
python -m src.orchestrator health              # System health metrics
python -m src.orchestrator automation-status   # Full automation system status

# Database setup (run once or when schema changes)
python scripts/setup_database.py              # Apply all migrations
python scripts/import_real_esco.py            # Load 13,000+ ESCO skills
```

### Scraping Operations

```bash
# Run individual spiders
python -m src.orchestrator run-once <spider> <country> --limit <n> --max-pages <p>
python -m src.orchestrator run-once bumeran CO --limit 10 --max-pages 2

# Run multiple spiders
python -m src.orchestrator run "bumeran,computrabajo" CO --limit 50 --max-pages 5

# List available spiders
python -m src.orchestrator list-spiders

# Available spiders: infojobs, elempleo, bumeran, computrabajo, zonajobs,
#                    magneto, occmundial, clarin, hiring_cafe
# Countries: CO, MX, AR, CL, PE, EC, PA, UY
```

### Automation System

```bash
# Start full automation (scheduler + pipeline + monitoring)
python -m src.orchestrator start-automation

# Process jobs through extraction pipeline
python -m src.orchestrator process-jobs --batch-size 10

# View scheduled jobs
python -m src.orchestrator list-jobs

# Force run a specific job
python -m src.orchestrator force-job <job_id>
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Test specific spider (debugging scripts available)
python scripts/debug_<spider_name>.py          # Individual spider debugging
python scripts/test_<spider_name>_real.py      # Real scraping tests

# Test extraction pipeline
python scripts/test_extraction_pipeline_detailed.py
python scripts/step_by_step_job_example.py
```

## Architecture & Key Concepts

### Pipeline Architecture (Linear Flow)

The system implements an **8-stage pipeline**:

1. **Scraping** (Scrapy + Selenium) → `src/scraper/`
2. **Extraction** (NER + Regex + ESCO) → `src/extractor/`
3. **LLM Processing** (Mistral 7B + OpenAI) → `src/llm_processor/` [In Development]
4. **Embedding** (E5 Multilingual) → `src/embedder/` [In Development]
5. **Dimension Reduction** (UMAP) → `src/analyzer/dimension_reducer.py` [In Development]
6. **Clustering** (HDBSCAN) → `src/analyzer/clustering.py` [In Development]
7. **Visualization** (Static Web) → `src/analyzer/visualizations.py` [In Development]
8. **Reports** (PDF/PNG/CSV) → `src/analyzer/report_generator.py` [In Development]

Each stage processes data and stores results in PostgreSQL before passing to the next stage.

### Database Schema (PostgreSQL + pgvector)

**Applied Migrations**: 001, 004, 005 (3 total, despite README saying "5")

Core tables:
- `raw_jobs` - Scraped job postings (portal, country, title, description, requirements, etc.)
- `extracted_skills` - Skills extracted via NER/Regex (skill_text, esco_uri, confidence_score)
- `enhanced_skills` - LLM-enhanced skills (normalized_skill, esco_concept_uri, llm_confidence)
- `skill_embeddings` - Vector embeddings (768D E5 model, pgvector)
- `analysis_results` - Clustering and analysis outputs (JSONB results)
- `esco_skills` - ESCO taxonomy (13,000+ skills, multilingual labels)

**Important**: Migration 002 exists in `src/database/migrations/` but is NOT applied. Check if it should be run or removed.

### Core Components

**Orchestrator** (`src/orchestrator.py`):
- Main CLI controller using Typer
- Routes all commands to appropriate subsystems
- Manages Scrapy subprocess execution with proper PYTHONPATH and cwd
- Parses scraping output to extract item counts

**Automation System** (`src/automation/`):
- `master_controller.py` - Central coordinator
- `intelligent_scheduler.py` - APScheduler-based spider scheduling
- `pipeline_automator.py` - Automatic job processing through extraction pipeline

**Extraction Pipeline** (`src/extractor/pipeline.py`):
- Orchestrates: NER → Regex → ESCO matching → Database storage
- `ExtractionPipeline.extract_skills_from_job()` - Main entry point
- Combines title + description + requirements for analysis
- Returns `ExtractedSkillResult` with ESCO mapping + confidence scores

**Scrapers** (`src/scraper/spiders/`):
- Mix of Scrapy-only and Scrapy+Selenium approaches
- Selenium spiders: bumeran, zonajobs, clarin, elempleo (for dynamic content)
- Base spider pattern in `base_spider.py`
- All spiders save to PostgreSQL via `pipelines.py`

### Configuration & Settings

**Environment Variables** (`.env`):
```
DATABASE_URL=postgresql://user:pass@localhost:5432/labor_market_db
SCRAPER_USER_AGENT=...
LLM_MODEL_PATH=./data/models/mistral-7b.gguf
EMBEDDING_MODEL=intfloat/multilingual-e5-base
OPENAI_API_KEY=...  # Optional
```

**Unified Settings** (`src/config/settings.py`):
- Pydantic-based settings management
- `get_settings()` returns cached singleton
- All modules should import settings from here, NOT from env directly

**Scrapy Configuration** (`src/scraper/settings.py`):
- Separate Scrapy-specific configuration
- Custom pipelines, middlewares, user agents, retry settings

### ESCO Taxonomy Integration

**ESCO Matcher** (`src/extractor/esco_matcher.py`):
- Maps extracted skills to ESCO taxonomy URIs
- Uses fuzzy matching + semantic search
- Database: `esco_skills` table with multilingual preferred labels
- Import script: `scripts/import_real_esco.py` (13,000+ skills)

**Important**: The system uses ESCO v1.1.0 by default. Skills are matched using:
1. Exact string matching (case-insensitive)
2. Fuzzy matching (similarity threshold)
3. SQL-based search in PostgreSQL

## Development Guidelines

### When Adding New Spiders

1. Extend `BaseSpider` in `src/scraper/spiders/base_spider.py`
2. Implement `parse()` and `parse_job_detail()` methods
3. Use Selenium if portal has dynamic content (see bumeran_spider.py as reference)
4. Test with debug script: `scripts/debug_<spider_name>.py`
5. Add spider name to `AVAILABLE_SPIDERS` in `src/orchestrator.py`

### When Modifying Database Schema

1. Create new migration file: `src/database/migrations/00X_description.sql`
2. Update SQLAlchemy models in `src/database/models.py`
3. Run migration: `psql -U postgres -f src/database/migrations/00X_description.sql`
4. Update `setup_database.py` to include new migration
5. **Update README.md** with correct migration count

### When Working with Extraction Pipeline

- Entry point: `ExtractionPipeline.extract_skills_from_job(job_data)`
- Input: `Dict[str, Any]` with keys: job_id, title, description, requirements
- Output: `List[ExtractedSkillResult]` with ESCO mapping
- Pipeline automatically deduplicates and combines NER + Regex results
- Skills are saved to `extracted_skills` table with job_id foreign key

### When Implementing New Pipeline Stages

Stages 3-8 are currently in development. When implementing:

1. Follow the pattern in `src/extractor/pipeline.py`
2. Create a processor class with `.process()` method
3. Read from previous stage's database table
4. Write results to next stage's table
5. Update `pipeline_automator.py` to include new stage
6. Add CLI command to `orchestrator.py` if needed

## Project Structure

```
src/
├── orchestrator.py           # Main CLI controller (Typer-based)
├── config/
│   ├── settings.py          # Pydantic settings (use get_settings())
│   ├── database.py          # Database connection utilities
│   └── logging_config.py    # Logging setup
├── scraper/
│   ├── spiders/             # Scrapy spiders (11 portals)
│   │   ├── base_spider.py   # Base class for all spiders
│   │   ├── *_spider.py      # Individual portal spiders
│   ├── pipelines.py         # Scrapy item pipelines (DB storage)
│   ├── middlewares.py       # Custom Scrapy middlewares
│   └── settings.py          # Scrapy configuration
├── extractor/
│   ├── pipeline.py          # Main extraction orchestrator
│   ├── ner_extractor.py     # spaCy NER-based extraction
│   ├── regex_patterns.py    # Regex-based extraction
│   └── esco_matcher.py      # ESCO taxonomy mapping
├── llm_processor/           # [In Development]
│   ├── llm_handler.py       # Mistral/OpenAI interface
│   ├── esco_normalizer.py   # Skill normalization logic
│   └── pipeline.py          # LLM processing pipeline
├── embedder/                # [In Development]
│   ├── vectorizer.py        # E5 model wrapper
│   └── batch_processor.py   # Batch embedding generation
├── analyzer/                # [In Development]
│   ├── dimension_reducer.py # UMAP implementation
│   ├── clustering.py        # HDBSCAN clustering
│   ├── visualizations.py    # Chart generation
│   └── report_generator.py  # PDF/PNG/CSV reports
├── automation/
│   ├── master_controller.py      # Central coordinator
│   ├── intelligent_scheduler.py  # APScheduler jobs
│   └── pipeline_automator.py     # Auto job processing
├── database/
│   ├── models.py            # SQLAlchemy ORM models
│   ├── operations.py        # Database CRUD operations
│   └── migrations/          # SQL migration files (001, 004, 005 applied)
└── utils/
    ├── cleaners.py          # Text cleaning utilities
    ├── validators.py        # Data validation
    └── logger.py            # Custom logging utilities

scripts/
├── setup_database.py        # Apply all migrations
├── import_real_esco.py      # Load ESCO taxonomy
├── debug_*.py               # Spider debugging scripts
├── test_*_real.py           # Real scraping tests
└── process_*.py             # Data processing utilities
```

## Important Notes

### Database URL Normalization
The codebase has inconsistent handling of `postgresql://` vs `postgres://` connection strings. Many modules include this normalization:

```python
db_url = settings.database_url
if db_url.startswith('postgresql://'):
    db_url = db_url.replace('postgresql://', 'postgres://')
```

When working with database connections, check if this normalization is needed.

### Scrapy Execution Context
The orchestrator runs Scrapy as a subprocess and must:
1. Set `cwd` to project root (where `scrapy.cfg` is)
2. Set `PYTHONPATH` to include `src/` directory
3. Parse stderr (not stdout) for item counts - Scrapy logs to stderr

### spaCy Model Requirement
The NER extractor requires the Spanish language model:
```bash
python -m spacy download es_core_news_lg
```

### TODO Items in Codebase
- Migration 002 (`add_missing_portals.sql`) exists but is not applied - investigate
- README says "5 migrations" but only 3 are applied (001, 004, 005)
- HDBSCAN is commented out in requirements.txt due to ARM64 compilation issues
- LLM, Embedding, Clustering, Visualization stages are scaffolded but not fully implemented

## Key Workflows

### Complete Scraping + Processing Workflow
```bash
# 1. Ensure database is ready
python scripts/setup_database.py
python scripts/import_real_esco.py

# 2. Scrape jobs from a portal
python -m src.orchestrator run-once bumeran CO --limit 50 --max-pages 5

# 3. Process scraped jobs through extraction pipeline
python -m src.orchestrator process-jobs --batch-size 50

# 4. Check results
python -m src.orchestrator status
```

### Automated 24/7 Operation
```bash
# Start automation system (runs forever until Ctrl+C)
python -m src.orchestrator start-automation

# In another terminal, monitor status
python -m src.orchestrator automation-status
python -m src.orchestrator list-jobs
python -m src.orchestrator health
```

## Troubleshooting

### "Database connection failed"
- Verify PostgreSQL is running: `docker-compose up -d postgres` OR `pg_ctl status`
- Check `.env` has correct `DATABASE_URL`
- Ensure pgvector extension is installed: `psql -c "CREATE EXTENSION IF NOT EXISTS pgvector;"`

### "Spider not found"
- Verify spider name in `AVAILABLE_SPIDERS` list (orchestrator.py:59)
- Check `scrapy.cfg` has correct path to spiders: `default = src.scraper.settings`
- Ensure you're running from project root directory

### "ESCO skills table is empty"
- Run `python scripts/import_real_esco.py`
- Verify migration 004 was applied: `psql -c "\d esco_skills"`

### Selenium spiders not working
- Ensure ChromeDriver is installed and in PATH
- Check Selenium version matches ChromeDriver version
- Look for "selenium" errors in scraper output
- Some portals (bumeran, zonajobs, clarin, elempleo) require Selenium for dynamic content

## Additional Resources

For detailed implementation guidance, see:
- `docs/ONBOARDING_GUIDE.md` - Complete onboarding for new developers
- `docs/technical-specification.md` - Full system specification
- `docs/implementation-guide.md` - Production-ready code examples
- `docs/data-flow-reference.md` - Inter-module communication patterns
- `README.md` - Project overview and quick start
