# ETL Strategy & Architecture Decisions

**Date:** October 19, 2025
**Status:** Design Complete, Implementation Ready
**Next Steps:** Implement cleaning script and update extraction pipeline

---

## 📊 Current Data Status

### Raw Data
- **Total jobs scraped:** 23,352
  - hiring_cafe/CO: 5,831
  - hiring_cafe/MX: 13,762
  - hiring_cafe/AR: 3,720
  - elempleo/CO: 38
  - zonajobs/AR: 1

- **Extraction status:** 0 jobs extracted (all pending)
- **Data quality issues identified:**
  - 6 jobs with empty descriptions (0.03%)
  - ~50-100 potential junk/test jobs (0.2-0.4%)
  - ~330 jobs missing requirements (1.4%)
  - HTML tags in descriptions/titles
  - Missing company names (~2%)

---

## 🎯 Architecture Decisions

### ✅ DECISION 1: Separate `cleaned_jobs` Table

**Question:** Store cleaned data in raw_jobs columns OR separate table?

**Decision:** **Separate `cleaned_jobs` table**

**Rationale:**
- Clean separation of concerns (raw vs processed)
- Can rebuild cleaned_jobs without touching raw data
- Easier to version/iterate on cleaning logic
- Same `job_id` as foreign key to raw_jobs

**Implementation:**
```sql
CREATE TABLE cleaned_jobs (
    job_id UUID PRIMARY KEY REFERENCES raw_jobs(job_id),
    title_cleaned TEXT,
    description_cleaned TEXT,
    requirements_cleaned TEXT,
    combined_text TEXT NOT NULL,  -- For extraction
    cleaning_method VARCHAR(50),
    cleaned_at TIMESTAMP,
    combined_word_count INTEGER,
    combined_char_count INTEGER
);
```

---

### ✅ DECISION 2: Store Combined Clean Text

**Question:** Combine title+description+requirements at extraction time OR store pre-combined?

**Decision:** **Store `combined_text` in `cleaned_jobs` table**

**Rationale:**
- Avoid recomputing combination 23k+ times
- Faster extraction (read one field instead of concatenating 3)
- Consistent text input across all extraction methods
- Matches existing pipeline logic

**Format:**
```python
combined_text = f"{title_cleaned}\n{description_cleaned}\n{requirements_cleaned}"
```

---

### ✅ DECISION 3: Clean Title Too

**Question:** Should we clean the title field?

**Decision:** **YES, clean title**

**Rationale:**
- Titles can contain HTML: `<strong>Senior Developer</strong>`
- Titles can contain junk: `URGENTE!!! 💰💰💰`
- Title is part of combined_text for extraction
- Important for skill extraction (job titles contain skills)

**Cleaning steps:**
1. Remove HTML tags
2. Remove excessive punctuation (!!!, ???)
3. Remove emojis
4. Normalize whitespace
5. Keep original case (helps NER)

---

### ✅ DECISION 4: Junk Filtering Strategy

**Question:** How to handle test/junk jobs?

**Decision:** **Flag with `is_usable=FALSE`, don't delete**

**Rationale:**
- Preserve all scraped data
- Reversible (can manually review flagged jobs)
- Clear audit trail

**Implementation:**
```sql
-- Add to raw_jobs:
is_usable BOOLEAN DEFAULT TRUE
unusable_reason TEXT

-- Filter rules:
- description < 100 chars → "Short description"
- title = "test" (exact) → "Test job"
- title = "002_Cand1" pattern → "Candidate placeholder"
- title = "Colombia Test 7" pattern → "Vendor test job"
```

**Strict regex to avoid false positives:**
```python
JUNK_PATTERNS = [
    r'^test$',                    # Just "test"
    r'^demo$',                    # Just "demo"
    r'^\d{3}_cand',              # "002_Cand1"
    r'^(colombia|mexico|argentina)\s+(credo\s+)?test\s+\d+$'
]

# KEEP legitimate jobs:
# - "Test Automation Engineer" ✅
# - "QA Tester" ✅
# - "Software Development Engineer in Test" ✅
```

---

### ✅ DECISION 5: FAISS for Embeddings

**Question:** Use pgvector OR FAISS OR both?

**Decision:** **FAISS for clustering, keep PostgreSQL for metadata**

**Rationale:**
- FAISS optimized for large-scale similarity search
- Better for clustering algorithms (UMAP + HDBSCAN)
- Loads all vectors into memory (fast)
- PostgreSQL stores metadata + skill text

**Implementation:**
```python
# skill_embeddings table (PostgreSQL):
skill_text, faiss_index_position, model_name, created_at

# FAISS index (file):
data/embeddings/skill_vectors.faiss

# Workflow:
1. Generate embeddings → store in PostgreSQL
2. Export to numpy matrix → build FAISS index
3. Use FAISS for similarity search + clustering
4. Query PostgreSQL for skill metadata
```

---

## 🔄 Complete ETL Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│ STAGE 1: SCRAPING (✅ DONE - 23,352 jobs)                    │
│                                                               │
│ Output: raw_jobs table                                       │
│ ├── title, description, requirements (with HTML)             │
│ ├── is_usable = TRUE (default)                               │
│ └── extraction_status = 'pending'                            │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ STAGE 2: ETL CLEANING (🔄 TO IMPLEMENT)                      │
│                                                               │
│ Script: scripts/clean_raw_jobs.py                            │
│                                                               │
│ For each job in raw_jobs:                                    │
│   1. Check if junk → UPDATE is_usable=FALSE if junk          │
│   2. Clean title → title_cleaned                             │
│   3. Clean description → description_cleaned                 │
│   4. Clean requirements → requirements_cleaned               │
│   5. Combine → combined_text                                 │
│   6. INSERT INTO cleaned_jobs                                │
│                                                               │
│ Output: cleaned_jobs table (~23,250 usable jobs)             │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ STAGE 3: SKILL EXTRACTION (🔄 TO UPDATE)                     │
│                                                               │
│ Read from: extraction_ready_jobs VIEW                        │
│ ├── Filters: is_usable=TRUE + has cleaned_jobs record        │
│ └── Returns: job_id, combined_text                           │
│                                                               │
│ Process:                                                      │
│ 1. Extract skills from combined_text                         │
│ 2. Map to ESCO OR custom_skill_mappings                      │
│ 3. Store in extracted_skills                                 │
│ 4. UPDATE raw_jobs.extraction_status = 'completed'           │
│                                                               │
│ Output: extracted_skills table                               │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ STAGE 4: EMBEDDING GENERATION (⏳ FUTURE)                    │
│                                                               │
│ 1. Generate embeddings with E5 model                         │
│ 2. Store metadata in skill_embeddings (PostgreSQL)           │
│ 3. Build FAISS index for fast similarity search              │
│                                                               │
│ Output:                                                       │
│ ├── skill_embeddings table (metadata)                        │
│ └── data/embeddings/skill_vectors.faiss (index file)         │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ STAGE 5-6: CLUSTERING (⏳ FUTURE)                            │
│                                                               │
│ 1. Load FAISS index                                          │
│ 2. UMAP dimensionality reduction (768D → 2D/3D)              │
│ 3. HDBSCAN clustering                                        │
│ 4. Store in analysis_results                                 │
└──────────────────────────────────────────────────────────────┘
```

---

## 📋 Database Schema Changes

### Migration 006: `cleaned_jobs` table

**New table:**
```sql
cleaned_jobs (
    job_id UUID PRIMARY KEY → raw_jobs(job_id),
    title_cleaned TEXT,
    description_cleaned TEXT,
    requirements_cleaned TEXT,
    combined_text TEXT NOT NULL,
    cleaning_method VARCHAR(50),
    cleaned_at TIMESTAMP,
    combined_word_count INTEGER,
    combined_char_count INTEGER
)
```

**New columns in raw_jobs:**
```sql
is_usable BOOLEAN DEFAULT TRUE,
unusable_reason TEXT
```

**New view:**
```sql
extraction_ready_jobs VIEW
-- Returns jobs ready for extraction:
-- WHERE is_usable=TRUE AND has cleaned_jobs record
```

**New function:**
```sql
get_cleaning_stats()
-- Returns ETL pipeline statistics
```

---

## 🛠️ Text Cleaning Rules

### HTML Removal
```python
# Remove all HTML tags
text = re.sub(r'<[^>]+>', ' ', text)

# Decode HTML entities
text = html.unescape(text)  # &nbsp; → space, &amp; → &

# Examples:
"<div><b>Buscamos</b> desarrollador</div>" → "Buscamos desarrollador"
"Empresa &amp; Asociados" → "Empresa & Asociados"
```

### Whitespace Normalization
```python
# Multiple spaces → single space
text = re.sub(r'\s+', ' ', text)

# Trim leading/trailing
text = text.strip()

# Examples:
"Buscamos    desarrollador" → "Buscamos desarrollador"
"  Senior Developer  " → "Senior Developer"
```

### Title-Specific Cleaning
```python
# Remove excessive punctuation
text = re.sub(r'([!?]){2,}', r'\1', text)

# Remove emojis (Unicode ranges)
text = re.sub(r'[\U00010000-\U0010ffff]', '', text)

# Examples:
"URGENTE!!! Desarrollador" → "URGENTE! Desarrollador"
"Senior Dev 💰💰" → "Senior Dev"
```

### What We DON'T Change
- ✅ Keep accents: "Desarrollador" (important for Spanish NER)
- ✅ Keep case: "Senior Developer" (helps entity recognition)
- ✅ Keep punctuation: "Full-stack" (meaningful)
- ✅ Keep numbers: "5+ years" (meaningful)

---

## 📊 Expected Results

### After ETL Cleaning

```
Input: 23,352 raw jobs

Junk Detection:
├── Empty description (< 100 chars): ~30 jobs
├── Test jobs (exact match): ~20 jobs
├── Candidate placeholders: ~10 jobs
├── Total unusable: ~100 jobs (0.4%)
└── Usable jobs: ~23,250 (99.6%)

Cleaning Results:
├── Jobs with cleaned text: 23,250
├── Average combined_text length: ~5,000 chars
├── Average word count: ~700 words
└── Ready for extraction: 23,250 jobs
```

### Storage Impact

```
Raw data size: 97 MB (raw_jobs)
Cleaned data size: ~80 MB (cleaned_jobs) [estimated]
Total database size: ~177 MB
Disk space increase: +82% (acceptable)
```

---

## 🎯 Implementation Checklist

### ✅ Completed
1. [x] Analyze data quality issues
2. [x] Define ETL strategy and make architecture decisions
3. [x] Create SQL migration 006
4. [x] Run migration (cleaned_jobs table created)
5. [x] Document decisions and rationale

### 🔄 Next Steps
1. [ ] Implement `scripts/clean_raw_jobs.py`
2. [ ] Run ETL on all 23k jobs
3. [ ] Verify cleaning results
4. [ ] Update extraction pipeline to use `extraction_ready_jobs` view
5. [ ] Test extraction on cleaned data
6. [ ] Document FAISS index implementation (Stage 4)

---

## 📚 References

- Migration file: `src/database/migrations/006_add_cleaned_jobs_table.sql`
- Extraction pipeline: `src/extractor/pipeline.py` (needs update)
- ESCO matcher: `src/extractor/esco_matcher.py`
- Custom skills: `custom_skill_mappings` table

---

**Document Status:** Complete
**Last Updated:** 2025-10-19
**Ready for Implementation:** YES
