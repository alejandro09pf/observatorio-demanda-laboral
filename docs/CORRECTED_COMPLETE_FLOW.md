# Observatorio de Demanda Laboral - FLUJO COMPLETO CORREGIDO

**Version:** 2.0 (Corregida)
**Date:** October 19, 2025
**Status:** FINAL - Responde todas las preguntas críticas

---

## 🎯 **Respuestas a Preguntas Críticas**

### **Q1: ¿En qué momento se mapean las skills de AMBOS flows a ESCO/O*NET?**

**A:** DESPUÉS de la extracción de cada pipeline, ANTES de merge/comparación.

```
Pipeline A → Extract → Map to ESCO (2 layers) → extracted_skills_A
Pipeline B → Extract → Map to ESCO (2 layers) → extracted_skills_B

Luego: Compare A vs B
```

### **Q2: ¿Dónde entran los embeddings?**

**A:** En 2 momentos diferentes:

1. **Setup (ONE-TIME, Phase 0)**: Generate ESCO taxonomy embeddings (13,939 skills) + build FAISS index
2. **Mapping (RUNTIME, Module 4)**: Generate embedding for candidate skill → FAISS search → cosine similarity vs ESCO

**Note:** Los embeddings de skills individuales se generan en Phase 0 para ESCO y en Module 6 Step 6.1 para todas las skills extraídas (para clustering)

### **Q3: ¿Qué hacemos si un LLM identifica una skill que NO está en ESCO/O*NET?**

**A:** 3-step process:

1. **Flag as emergent**: Mark skill as unmapped, save to `emergent_skills` table
2. **Track frequency**: Count how many jobs mention this skill
3. **Manual review**: High-frequency emergent skills → add to custom taxonomy OR map to nearest ESCO

### **Q4: ¿Cómo comparar múltiples LLMs?**

**A:** Run múltiples LLMs en Pipeline B, compare resultados:

```
Pipeline B:
├── Run GPT-3.5 → skills_gpt35 → Map to ESCO → Save with llm_model='gpt-3.5'
├── Run Mistral-7B → skills_mistral → Map to ESCO → Save with llm_model='mistral'
├── Run Llama-2 → skills_llama → Map to ESCO → Save with llm_model='llama'
└── Compare: Coverage, Confidence, ESCO mapping rate, Implicit skills
```

### **Q5: ¿Cómo comparamos A vs B sin LLM mediador?**

**A:** Comparación directa con métricas objetivas + análisis cualitativo manual:

**Metrics:**
- Coverage: Skills únicas de A, B, y overlap
- ESCO mapping success rate
- Confidence scores distribution
- Explicit vs Implicit (solo B)

**Qualitative Analysis:**
- Manual review de skills únicas de cada pipeline
- ¿Cuál encontró skills más relevantes?
- ¿Qué skills perdió cada método?

---

## 📊 **FLUJO COMPLETO CORREGIDO**

### **FASE 0: One-Time Setup (Run Once)**

```
┌─────────────────────────────────────────────┐
│ 0.1: Load ESCO Taxonomy                    │
│     - 13,939 skills from ESCO database     │
│     - multilingual labels (ES + EN)        │
└─────────────────────┬───────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│ 0.2: Generate ESCO Embeddings              │
│     Model: multilingual-e5-base (768D)     │
│     ┌──────────────────────────────┐       │
│     │ for each ESCO skill:         │       │
│     │   text = label + description │       │
│     │   embedding = E5.encode(text)│       │
│     │   save to skill_embeddings   │       │
│     └──────────────────────────────┘       │
│     Output: 13,939 embeddings              │
└─────────────────────┬───────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│ 0.3: Build FAISS Index (CRITICAL)          │
│     ⚠️ NOT optional - needed for Layer 2   │
│        semantic matching at scale          │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ import faiss                           │ │
│ │ import numpy as np                     │ │
│ │                                        │ │
│ │ # Load embeddings from DB              │ │
│ │ embeddings = load_esco_embeddings()    │ │
│ │ # Shape: (13,939 skills, 768 dims)     │ │
│ │                                        │ │
│ │ # Normalize for cosine similarity      │ │
│ │ faiss.normalize_L2(embeddings)         │ │
│ │                                        │ │
│ │ # Create IndexFlatIP (Inner Product)   │ │
│ │ index = faiss.IndexFlatIP(768)         │ │
│ │ index.add(embeddings)                  │ │
│ │                                        │ │
│ │ # Save index                           │ │
│ │ faiss.write_index(index,               │ │
│ │   'data/embeddings/esco.faiss')        │ │
│ │                                        │ │
│ │ # Also save mapping esco_uri → index   │ │
│ │ np.save('data/embeddings/esco_uris.npy'│ │
│ │         esco_uris)                     │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Why FAISS?                                  │
│   - PostgreSQL pgvector: ~5s per query     │
│   - FAISS IndexFlatIP: ~0.2s per query     │
│   - 25x speedup for semantic matching      │
│                                             │
│ Output Files:                               │
│   ✅ data/embeddings/esco.faiss (index)    │
│   ✅ data/embeddings/esco_uris.npy (map)   │
│   ✅ data/embeddings/esco_embeddings.npy   │
└─────────────────────────────────────────────┘

ONE-TIME SETUP COMPLETE ✅
(Run once, reuse for all 23K+ jobs)
```

---

### **FASE 1: Data Collection & Cleaning (DONE ✅)**

#### **Module 1.1: Web Scraping Configuration**

**Input:**
- Target countries: `Colombia (CO)`, `Mexico (MX)`, `Argentina (AR)`
- Target portals: `hiring_cafe`, `computrabajo`, `bumeran`, `elempleo`, `zonajobs`, `infojobs`
- Scraping parameters: `limit`, `max_pages`, `country_code`

**Orchestrator Command:**
```bash
python -m src.orchestrator run-once hiring_cafe CO --limit 50000 --max-pages 1000
```

**Output:**
- Spider instances configured with portal-specific selectors
- Ready to execute async scraping

**Files:** `src/orchestrator.py`, `src/scraper/spiders/*.py`
**Status:** ✅ Complete

---

#### **Module 1.2: Web Navigation & HTML Download**

**Action:**
1. Execute spiders using **Scrapy** (async collection)
2. Use **Selenium** as fallback for JavaScript-rendered content (bumeran, zonajobs, clarin)
3. Navigate pagination (sorted by newest first when possible)
4. Download complete HTML of each job posting page

**Deduplication Strategy (During Scraping):**
- Track last 2 job IDs seen
- If 2 consecutive duplicates → stop spider (all new jobs collected)

**Output:**
- Raw HTML responses for each job posting

**Current Stats:**
- hiring_cafe: 23,313 jobs
- elempleo: 38 jobs
- zonajobs: 1 job
- **Total:** 23,352 jobs scraped

---

#### **Module 1.3: HTML Parsing & Structured Extraction**

**Input:** Raw HTML responses

**Extracted Fields:**
- `title` - Job title
- `company` - Company name
- `description` - Full job description (HTML)
- `requirements` - Requirements section (HTML)
- `location` - Location/city
- `salary` - Salary range (if available)
- `contract_type` - Full-time/Part-time/Contract
- `posted_date` - Date published
- `url` - Original job posting URL

**Output:** Scrapy Items with structured data

**Files:** `src/scraper/spiders/*.py` (parse methods), `src/scraper/items.py`

---

#### **Module 1.4: Database Storage with SHA256 Deduplication**

**Deduplication Algorithm:**
```
1. Calculate content_hash = SHA256(title + description + requirements)
2. Check: SELECT job_id FROM raw_jobs WHERE content_hash = ?
3. If duplicate → skip (log event)
4. If unique → INSERT into raw_jobs
```

**Database Schema: raw_jobs**
```sql
raw_jobs (
    job_id UUID PRIMARY KEY,
    portal VARCHAR(50),           -- 'hiring_cafe', 'bumeran', etc
    country VARCHAR(2),            -- 'CO', 'MX', 'AR'
    url TEXT UNIQUE,
    title TEXT NOT NULL,
    company TEXT,
    description TEXT NOT NULL,    -- Raw HTML
    requirements TEXT,            -- Raw HTML (can be NULL)
    location TEXT,
    salary TEXT,
    contract_type VARCHAR(50),
    posted_date DATE,
    content_hash VARCHAR(64) UNIQUE,  -- SHA256 for deduplication
    scraped_at TIMESTAMP DEFAULT NOW(),

    -- Extraction tracking
    extraction_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    extraction_attempts INTEGER DEFAULT 0,
    extraction_completed_at TIMESTAMP,
    extraction_error TEXT,

    -- Data quality flags (added in migration 006)
    is_usable BOOLEAN DEFAULT TRUE,
    unusable_reason TEXT
)
```

**Files:** `src/scraper/pipelines.py`, `src/database/models.py`
**Status:** ✅ Complete

---

#### **Module 2.1: HTML Removal & Text Cleaning**

**Input:** `raw_jobs` table with HTML content

**Cleaning Process:**

**Step 2.1.1: HTML Tag Removal**
- Remove all `<tag>` elements
- Decode HTML entities (`&nbsp;` → space, `&amp;` → &)
- Preserve text content only

**Step 2.1.2: Text Normalization**
- Multiple whitespace → single space
- Remove excessive punctuation (!!!, ???)
- Remove emojis and Unicode symbols
- Trim leading/trailing whitespace
- Keep accents (español)
- Keep case (helps NER)
- Keep meaningful punctuation (-, /, +)

**Step 2.1.3: Junk Detection**

**Junk Patterns (Conservative):**
```
- Exact "test" (case-insensitive)
- Exact "demo"
- "002_Cand1" pattern (placeholder candidates)
- "Colombia Test 7" pattern (vendor test jobs)
- Description < 50 characters (extremely short)
```

**Action:**
- If junk detected → UPDATE raw_jobs SET is_usable=FALSE, unusable_reason='...'
- Junk jobs are NOT deleted (preserved for audit)

**Step 2.1.4: Combined Text Generation**
```
Format: title_cleaned + "\n" + description_cleaned + "\n" + requirements_cleaned
```

**Step 2.1.5: Metadata Calculation**
- `combined_word_count` - Number of words in combined text
- `combined_char_count` - Number of characters

**Output: cleaned_jobs table**
```sql
cleaned_jobs (
    job_id UUID PRIMARY KEY REFERENCES raw_jobs(job_id),
    title_cleaned TEXT,
    description_cleaned TEXT,
    requirements_cleaned TEXT,
    combined_text TEXT NOT NULL,          -- Pre-computed for extraction
    cleaning_method VARCHAR(50) DEFAULT 'html_strip',
    cleaned_at TIMESTAMP DEFAULT NOW(),
    combined_word_count INTEGER,          -- ~552 words avg
    combined_char_count INTEGER
)
```

**Stats After Cleaning:**
- Total raw_jobs: 23,352
- Junk jobs (is_usable=FALSE): 125 (0.5%)
- Cleaned jobs: 23,188 (99.5%)
- Average combined_word_count: 552 words
- Average combined_char_count: ~3,000 characters

**extraction_ready_jobs VIEW:**
```sql
CREATE VIEW extraction_ready_jobs AS
SELECT
    r.job_id, r.portal, r.country, r.url, r.company, r.location,
    r.posted_date, r.scraped_at, r.extraction_status,
    c.title_cleaned, c.description_cleaned, c.requirements_cleaned,
    c.combined_text, c.combined_word_count, c.cleaned_at
FROM raw_jobs r
INNER JOIN cleaned_jobs c ON r.job_id = c.job_id
WHERE r.is_usable = TRUE
  AND r.extraction_status = 'pending';
```

**Files:** `scripts/clean_raw_jobs.py`, `src/database/migrations/006_add_cleaned_jobs_table.sql`
**Status:** ✅ Complete

---

**DATA READY FOR EXTRACTION ✅**
- 23,188 clean, usable job postings
- All HTML removed, text normalized
- Combined text pre-computed for extraction
- Junk jobs filtered out

---

### **FASE 2: Parallel Skill Extraction**

```
                    cleaned_jobs.combined_text
                              |
                    ┌─────────┴─────────┐
                    ▼                   ▼
        ╔═══════════════════╗   ╔═══════════════════╗
        ║  PIPELINE A       ║   ║  PIPELINE B       ║
        ║  (Traditional)    ║   ║  (LLM-based)      ║
        ╚═══════════════════╝   ╚═══════════════════╝
```

---

### **PIPELINE A: Traditional Extraction (Regex + NER)**

```
Step 3A.1: Regex Pattern Matching
┌─────────────────────────────────────────────┐
│ Input: cleaned_jobs.combined_text           │
│                                             │
│ Patterns:                                   │
│   - Programming: Python, Java, JS, C++     │
│   - Frameworks: React, Django, Spring      │
│   - Databases: PostgreSQL, MongoDB         │
│   - Cloud: AWS, Azure, GCP                 │
│   - Tools: Git, Docker, Kubernetes         │
│                                             │
│ Output: List of regex-matched skills       │
│   [{skill: "Python", method: "regex",      │
│     confidence: 0.8, context: "..."}]      │
└─────────────────────┬───────────────────────┘
                      ↓
Step 3A.2: spaCy NER Processing with EntityRuler
┌─────────────────────────────────────────────┐
│ Model: es_core_news_lg                      │
│                                             │
│ ✅ IMPLEMENTATION: Custom Entity Ruler     │
│ ┌─────────────────────────────────────────┐ │
│ │ # Load spaCy + add EntityRuler         │ │
│ │ nlp = spacy.load("es_core_news_lg")    │ │
│ │ ruler = nlp.add_pipe("entity_ruler",   │ │
│ │                      before="ner")     │ │
│ │                                        │ │
│ │ # Load 13,939 ESCO skills as patterns │ │
│ │ patterns = []                          │ │
│ │ for skill in esco_skills:              │ │
│ │   patterns.append({                    │ │
│ │     "label": "SKILL",                  │ │
│ │     "pattern": skill.preferred_label   │ │
│ │   })                                   │ │
│ │                                        │ │
│ │ ruler.add_patterns(patterns)           │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Benefits:                                   │
│   ✅ Exact match for all ESCO skills       │
│   ✅ Higher recall (captures more skills)  │
│   ✅ No false positives on ESCO terms      │
│                                             │
│ Process:                                    │
│   doc = nlp(combined_text)                 │
│   for ent in doc.ents:                     │
│     if ent.label_ == "SKILL":              │
│       extract(ent)                         │
│                                             │
│ Output: List of NER-extracted skills       │
│   (includes both spaCy NER + EntityRuler)  │
└─────────────────────┬───────────────────────┘
                      ↓
Step 3A.3: Combine & Deduplicate
┌─────────────────────────────────────────────┐
│ Merge: regex_skills + ner_skills            │
│                                             │
│ Deduplicate:                                │
│   - Normalize: lowercase, strip whitespace │
│   - Group by normalized text               │
│   - Keep highest confidence score          │
│                                             │
│ Output: Unified list of candidate skills   │
│   (de-duplicated, sorted by confidence)    │
└─────────────────────┬───────────────────────┘
                      ↓
Step 3A.4: NO ESCO MAPPING YET
(Mapping happens in Module 4)
```

---

### **PIPELINE B: LLM-based Extraction**

```
Step 3B.1: LLM Selection & Comparison Strategy
┌─────────────────────────────────────────────┐
│ LLM OPTIONS TO COMPARE:                     │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ Model Comparison Table                 │ │
│ ├─────────────┬──────┬──────┬─────┬─────┤ │
│ │ Model       │ Cost │ Speed│ F1  │ ES? │ │
│ ├─────────────┼──────┼──────┼─────┼─────┤ │
│ │ GPT-3.5     │ $0.50│ Fast │ 0.62│ ✅  │ │
│ │ GPT-4       │$15.00│ Slow │ 0.68│ ✅  │ │
│ │ Mistral-7B  │ $0   │ Med  │ 0.58│ ✅  │ │
│ │ Llama-3-8B  │ $0   │ Med  │ 0.64│ ✅  │ │
│ └─────────────┴──────┴──────┴─────┴─────┘ │
│                                             │
│ SELECTION CRITERIA:                         │
│   1. Cost (API vs local)                   │
│   2. Speed (jobs/second)                   │
│   3. F1-Score (from literature)            │
│   4. Spanish support                       │
│   5. **Gold Standard accuracy**            │
│                                             │
│ COMPARISON STRATEGY:                        │
│   ✅ Run multiple LLMs in parallel         │
│   ✅ Validate ALL against Gold Standard    │
│   ✅ Compare:                               │
│      - Precision/Recall vs Gold (300 jobs) │
│      - Distance to Silver Bullet (15K jobs)│
│      - Explicit vs Implicit skill coverage │
│      - Cost per 1M skills extracted        │
│                                             │
│ RECOMMENDED: Llama-3-8B                     │
│   Reason: Best balance (F1=0.64, free,     │
│           16GB VRAM, Spanish support)      │
└─────────────────────┬───────────────────────┘
                      ↓
Step 3B.2: Prompt Engineering
┌─────────────────────────────────────────────┐
│ Prompt Template:                            │
│ ┌─────────────────────────────────────────┐ │
│ │ You are an expert HR analyst.          │ │
│ │                                         │ │
│ │ Job: {title} at {company}              │ │
│ │ Description: {combined_text}           │ │
│ │                                         │ │
│ │ Extract ALL skills (explicit+implicit) │ │
│ │                                         │ │
│ │ Output JSON:                           │ │
│ │ {                                      │ │
│ │   "explicit_skills": [                 │ │
│ │     {"skill": "Python",                │ │
│ │      "category": "Programming",        │ │
│ │      "confidence": 0.95,               │ │
│ │      "evidence": "quoted text"}        │ │
│ │   ],                                   │ │
│ │   "implicit_skills": [                 │ │
│ │     {"skill": "Problem Solving",       │ │
│ │      "category": "Soft Skill",         │ │
│ │      "confidence": 0.8,                │ │
│ │      "evidence": "inferred from..."}   │ │
│ │   ]                                    │ │
│ │ }                                      │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────┘
                      ↓
Step 3B.3: LLM Inference (PER LLM)
┌─────────────────────────────────────────────┐
│ FOR EACH LLM (GPT, Mistral, Llama):        │
│                                             │
│   response = llm.generate(prompt)          │
│   parsed = parse_json(response)            │
│                                             │
│   skills_from_llm_X = {                    │
│     'llm_model': 'gpt-3.5-turbo',          │
│     'explicit': parsed.explicit_skills,    │
│     'implicit': parsed.implicit_skills     │
│   }                                        │
│                                             │
│ Output: Skills from EACH LLM separately    │
└─────────────────────┬───────────────────────┘
                      ↓
Step 3B.4: Compare LLM Results (OPTIONAL)
┌─────────────────────────────────────────────┐
│ IF running multiple LLMs:                   │
│                                             │
│ Compare:                                    │
│   - Coverage: Which found most skills?     │
│   - Confidence: Which has higher scores?   │
│   - Implicit: Which inferred more?         │
│                                             │
│ Select:                                     │
│   - Use BEST LLM results, OR               │
│   - MERGE all LLMs (union of skills)       │
│                                             │
│ Output: Selected/merged LLM skills         │
└─────────────────────┬───────────────────────┘
                      ↓
Step 3B.5: NO ESCO MAPPING YET
(Mapping happens in Module 4)
```

---

### **MODULE 4: ESCO/O*NET Mapping (SHARED BY BOTH PIPELINES)**

```
┌───────────────────────┬───────────────────────┐
│   Skills from         │    Skills from        │
│   Pipeline A          │    Pipeline B         │
│   (Regex + NER)       │    (LLM)              │
└───────────┬───────────┴───────────┬───────────┘
            │                       │
            │    BOTH GO THROUGH    │
            │    SAME MAPPING       │
            │    PROCESS            │
            └──────────┬────────────┘
                       ↓
```

#### **Layer 1: Direct & Fuzzy Matching**

```
Step 4.1: Exact Match
┌─────────────────────────────────────────────┐
│ FOR EACH candidate skill:                   │
│                                             │
│ Query ESCO database:                        │
│   SELECT esco_uri, preferred_label         │
│   FROM esco_skills                         │
│   WHERE LOWER(preferred_label_es) =        │
│         LOWER(candidate_skill)             │
│      OR LOWER(preferred_label_en) =        │
│         LOWER(candidate_skill)             │
│                                             │
│ IF match found:                            │
│   skill.esco_uri = match.esco_uri          │
│   skill.mapping_method = 'exact'           │
│   skill.mapping_confidence = 1.0           │
│   DONE ✅                                   │
│                                             │
│ IF no match:                               │
│   Go to Step 4.2 (Fuzzy)                   │
└─────────────────────┬───────────────────────┘
                      ↓
Step 4.2: Fuzzy Match
┌─────────────────────────────────────────────┐
│ from fuzzywuzzy import fuzz                 │
│                                             │
│ best_match = None                          │
│ best_score = 0                             │
│                                             │
│ FOR EACH esco_skill in esco_database:      │
│   score = fuzz.ratio(                      │
│     normalize(candidate_skill),            │
│     normalize(esco_skill.label)            │
│   )                                        │
│                                             │
│   if score > best_score:                   │
│     best_match = esco_skill                │
│     best_score = score                     │
│                                             │
│ THRESHOLD = 85  # 85% similarity           │
│                                             │
│ IF best_score >= THRESHOLD:                │
│   skill.esco_uri = best_match.esco_uri     │
│   skill.mapping_method = 'fuzzy'           │
│   skill.mapping_confidence = best_score/100│
│   DONE ✅                                   │
│                                             │
│ IF best_score < THRESHOLD:                 │
│   Go to Layer 2 (Semantic)                 │
└─────────────────────┬───────────────────────┘
                      ↓
```

#### **Layer 2: Semantic Matching with Embeddings**

```
Step 4.3: Generate Candidate Embedding
┌─────────────────────────────────────────────┐
│ Load E5 model:                              │
│   model = SentenceTransformer(             │
│     'intfloat/multilingual-e5-base'        │
│   )                                        │
│                                             │
│ Generate embedding:                        │
│   candidate_embedding = model.encode(      │
│     candidate_skill,                       │
│     convert_to_numpy=True                  │
│   )                                        │
│                                             │
│ Normalize for cosine similarity:           │
│   candidate_embedding = (                  │
│     candidate_embedding /                  │
│     np.linalg.norm(candidate_embedding)    │
│   )                                        │
└─────────────────────┬───────────────────────┘
                      ↓
Step 4.4: Similarity Search with FAISS
┌─────────────────────────────────────────────┐
│ ✅ USE FAISS (25x faster than PostgreSQL)  │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ # Load pre-built FAISS index           │ │
│ │ import faiss                           │ │
│ │ import numpy as np                     │ │
│ │                                        │ │
│ │ index = faiss.read_index(              │ │
│ │   'data/embeddings/esco.faiss'         │ │
│ │ )                                      │ │
│ │                                        │ │
│ │ # Load ESCO URI mapping                │ │
│ │ esco_uris = np.load(                   │ │
│ │   'data/embeddings/esco_uris.npy'      │ │
│ │ )                                      │ │
│ │                                        │ │
│ │ # Search for top 10 matches            │ │
│ │ k = 10                                 │ │
│ │ similarities, indices = index.search(  │ │
│ │   candidate_embedding.reshape(1, -1),  │ │
│ │   k                                    │ │
│ │ )                                      │ │
│ │                                        │ │
│ │ # Get best match                       │ │
│ │ best_idx = indices[0][0]               │ │
│ │ top_match = {                          │ │
│ │   'esco_uri': esco_uris[best_idx],     │ │
│ │   'similarity': float(similarities[0][0])│ │
│ │ }                                      │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Performance Comparison:                     │
│   FAISS IndexFlatIP: ~0.2s per skill       │
│   PostgreSQL pgvector: ~5s per skill       │
│   Speedup: 25x faster ⚡                    │
│                                             │
│ Why IndexFlatIP?                            │
│   - Exact nearest neighbor (no approx)     │
│   - Inner product = cosine sim (normalized)│
│   - No index building needed at runtime    │
└─────────────────────┬───────────────────────┘
                      ↓
Step 4.5: Apply Threshold
┌─────────────────────────────────────────────┐
│ SEMANTIC_THRESHOLD = 0.85                   │
│                                             │
│ IF top_match.similarity >= THRESHOLD:      │
│   skill.esco_uri = top_match.esco_uri      │
│   skill.mapping_method = 'semantic'        │
│   skill.mapping_confidence = similarity    │
│   DONE ✅                                   │
│                                             │
│ ELSE:                                      │
│   Go to Step 4.6 (Emergent Skill)          │
└─────────────────────┬───────────────────────┘
                      ↓
Step 4.6: Handle Unmapped Skills
┌─────────────────────────────────────────────┐
│ Flag as EMERGENT SKILL:                     │
│                                             │
│ INSERT INTO emergent_skills (              │
│   skill_text,                              │
│   extraction_method,  -- 'ner'/'regex'/'llm'│
│   first_seen_job_id,                       │
│   occurrence_count,                        │
│   best_esco_match,    -- nearest match     │
│   best_similarity,    -- even if < 0.85    │
│   flag_reason,                             │
│   review_status       -- 'pending'         │
│ ) VALUES (...)                             │
│ ON CONFLICT (skill_text) DO UPDATE         │
│ SET occurrence_count = occurrence_count + 1│
│                                             │
│ skill.esco_uri = NULL                      │
│ skill.mapping_method = 'unmapped'          │
│ skill.flag = 'emergent_skill'              │
└─────────────────────────────────────────────┘
```

#### **Save Mapped Skills**

```
Step 4.7: Save to Database
┌─────────────────────────────────────────────┐
│ INSERT INTO extracted_skills (              │
│   job_id,                                  │
│   skill_text,                              │
│   extraction_method,  -- 'regex'/'ner'/'llm'│
│   llm_model,          -- if from LLM       │
│   skill_type,         -- 'explicit'/'implicit'│
│   confidence_score,                        │
│   esco_uri,           -- NULL if unmapped  │
│   esco_label,                              │
│   mapping_method,     -- 'exact'/'fuzzy'/  │
│                       -- 'semantic'/'unmapped'│
│   mapping_confidence,                      │
│   evidence_text,      -- LLM reasoning     │
│   extracted_at                             │
│ ) VALUES (...)                             │
│                                             │
│ Output: Fully mapped skill database        │
└─────────────────────────────────────────────┘
```

---

### **MODULE 5: Pipeline Comparison (A vs B)**

```
Step 5.1: Extract Skills by Pipeline
┌─────────────────────────────────────────────┐
│ -- Skills from Pipeline A                   │
│ SELECT * FROM extracted_skills              │
│ WHERE extraction_method IN ('regex', 'ner')│
│                                             │
│ -- Skills from Pipeline B                   │
│ SELECT * FROM extracted_skills              │
│ WHERE extraction_method LIKE 'llm%'        │
└─────────────────────┬───────────────────────┘
                      ↓
Step 5.2: Calculate Comparison Metrics
┌─────────────────────────────────────────────┐
│ 1. COVERAGE ANALYSIS                        │
│    skills_A_only = skills_A - skills_B     │
│    skills_B_only = skills_B - skills_A     │
│    skills_both = skills_A ∩ skills_B       │
│    overlap_ratio = len(both) / len(A ∪ B)  │
│                                             │
│ 2. ESCO MAPPING SUCCESS RATE                │
│    mapped_A = COUNT(esco_uri NOT NULL) / A │
│    mapped_B = COUNT(esco_uri NOT NULL) / B │
│                                             │
│ 3. CONFIDENCE DISTRIBUTION                  │
│    avg_conf_A = AVG(confidence_score)      │
│    avg_conf_B = AVG(confidence_score)      │
│                                             │
│ 4. EXPLICIT VS IMPLICIT (B only)            │
│    explicit_B = COUNT(skill_type='explicit')│
│    implicit_B = COUNT(skill_type='implicit')│
│                                             │
│ 5. EMERGENT SKILLS                          │
│    unmapped_A = COUNT(esco_uri IS NULL)    │
│    unmapped_B = COUNT(esco_uri IS NULL)    │
└─────────────────────┬───────────────────────┘
                      ↓
Step 5.3: Qualitative Analysis
┌─────────────────────────────────────────────┐
│ Export for manual review:                   │
│                                             │
│ 1. Top 50 skills unique to Pipeline A      │
│ 2. Top 50 skills unique to Pipeline B      │
│ 3. Skills with high confidence diff        │
│                                             │
│ Manual questions:                           │
│ - Are unique_B skills truly valuable?      │
│ - Did LLM infer useful implicit skills?    │
│ - Did NER/Regex miss obvious skills?       │
│ - Which pipeline is more comprehensive?    │
└─────────────────────┬───────────────────────┘
                      ↓
Step 5.4: Compare Multiple LLMs (if applicable)
┌─────────────────────────────────────────────┐
│ IF ran multiple LLMs in Pipeline B:        │
│                                             │
│ Compare by llm_model:                       │
│   SELECT llm_model,                        │
│     COUNT(*) as skills_extracted,          │
│     AVG(confidence_score) as avg_conf,     │
│     COUNT(CASE WHEN esco_uri IS NOT NULL)  │
│       as mapped_count                      │
│   FROM extracted_skills                    │
│   WHERE extraction_method LIKE 'llm%'      │
│   GROUP BY llm_model                       │
│                                             │
│ Analyze:                                    │
│ - Which LLM found most skills?             │
│ - Which has best ESCO mapping rate?        │
│ - Which has highest confidence?            │
│ - Cost vs performance trade-off            │
└─────────────────────────────────────────────┘
```

---

### **MODULE 6: Skill Clustering & Temporal Analysis**

**IMPORTANT:** We cluster SKILLS, not jobs. This allows us to:
1. Identify skill profiles/families (e.g., "Frontend stack", "DevOps tools")
2. Track how skill clusters evolve over time
3. Discover emerging skill combinations

```
Step 6.1: Generate Skill Embeddings (Individual Skills)
┌─────────────────────────────────────────────┐
│ ⚠️ NOTE: ESCO embeddings (13,939 skills)   │
│          already generated in Phase 0      │
│                                             │
│ HERE: Generate embeddings for ALL extracted│
│       skills (ESCO + emergent/unmapped)    │
│       for clustering analysis              │
│                                             │
│ FOR EACH unique skill extracted:            │
│                                             │
│   # Load E5 multilingual model             │
│   model = SentenceTransformer(             │
│     'intfloat/multilingual-e5-base'        │
│   )                                        │
│                                             │
│   # Generate 768D embedding                │
│   skill_embedding = model.encode(          │
│     skill_text,                            │
│     convert_to_numpy=True                  │
│   )                                        │
│                                             │
│   # Normalize for cosine similarity        │
│   skill_embedding = (                      │
│     skill_embedding /                      │
│     np.linalg.norm(skill_embedding)        │
│   )                                        │
│                                             │
│   # Save to DB                             │
│   INSERT INTO skill_embeddings (           │
│     skill_text, embedding_vector,          │
│     model_name, created_at                 │
│   ) VALUES (...)                           │
│                                             │
│ Result: N unique skills → N embeddings     │
│         (768 dimensions each)              │
└─────────────────────┬───────────────────────┘
                      ↓
Step 6.2: UMAP Dimensionality Reduction (BEFORE Clustering)
┌─────────────────────────────────────────────┐
│ ⚠️ CRITICAL: Reduce BEFORE clustering      │
│                                             │
│ WHY? HDBSCAN performs poorly in high-dim   │
│      spaces (curse of dimensionality).     │
│      UMAP preserves local + global         │
│      structure better than PCA/t-SNE.      │
│                                             │
│ COMPARISON (from Paper 3):                  │
│ ┌──────────┬─────────┬──────────────────┐ │
│ │ Method   │ Speed   │ Trustworthiness  │ │
│ ├──────────┼─────────┼──────────────────┤ │
│ │ PCA      │ Fast    │ 0.72 (linear)    │ │
│ │ t-SNE    │ Slow    │ 0.85 (local)     │ │
│ │ UMAP     │ Medium  │ 0.91 (BEST)      │ │
│ └──────────┴─────────┴──────────────────┘ │
│                                             │
│ UMAP reduces 768D → 2D/3D while preserving │
│ both local clusters AND global topology.   │
│                                             │
│ Implementation:                             │
│   import umap                              │
│                                             │
│   reducer = umap.UMAP(                     │
│     n_components=2,      # 2D for viz      │
│     n_neighbors=15,      # local structure │
│     min_dist=0.1,        # cluster spacing │
│     metric='cosine'      # for embeddings  │
│   )                                        │
│                                             │
│   skill_embeddings_2d = reducer.fit_transform(│
│     skill_embeddings_768d                  │
│   )                                        │
│                                             │
│ Output: N skills × 2 dimensions            │
└─────────────────────┬───────────────────────┘
                      ↓
Step 6.3: HDBSCAN Clustering (AFTER Reduction)
┌─────────────────────────────────────────────┐
│ ⚠️ CRITICAL: Cluster on 2D UMAP output     │
│                                             │
│ Parameters (tuned for skill clustering):    │
│   import hdbscan                            │
│                                             │
│   clusterer = hdbscan.HDBSCAN(             │
│     min_cluster_size=50,   # Min skills    │
│     min_samples=10,        # Core density  │
│     metric='euclidean',    # On 2D UMAP    │
│     cluster_selection_method='eom'         │
│   )                                        │
│                                             │
│   cluster_labels = clusterer.fit_predict(  │
│     skill_embeddings_2d  # 2D, NOT 768D!  │
│   )                                        │
│                                             │
│ Output: Cluster labels for each skill      │
│   -1 = noise/outliers                      │
│   0, 1, 2, ... = cluster IDs               │
│                                             │
│ Save results:                               │
│   UPDATE extracted_skills                  │
│   SET cluster_id = %s, cluster_prob = %s   │
│   WHERE skill_text = %s                    │
└─────────────────────┬───────────────────────┘
                      ↓
Step 6.4: Temporal Cluster Analysis
┌─────────────────────────────────────────────┐
│ Goal: Track how skill clusters change      │
│       over time (2018-2025)                 │
│                                             │
│ Analysis 1: Cluster growth/decline          │
│   SELECT                                    │
│     cluster_id,                            │
│     DATE_TRUNC('quarter', posted_date),    │
│     COUNT(DISTINCT job_id) as demand       │
│   FROM extracted_skills e                  │
│   JOIN raw_jobs r ON e.job_id = r.job_id  │
│   GROUP BY cluster_id, quarter             │
│   ORDER BY quarter, demand DESC            │
│                                             │
│ Analysis 2: Emerging clusters               │
│   - Identify clusters with demand spike    │
│   - Flag new clusters (appeared in 2024+)  │
│                                             │
│ Analysis 3: Dying clusters                  │
│   - Identify clusters with demand drop     │
│   - Mark as "obsolete skills"              │
│                                             │
│ Visualization:                              │
│   - Animated scatter plot (UMAP 2D)        │
│   - Color = cluster, size = demand         │
│   - Timeline slider (by quarter/year)      │
│   - "Replay" skill demand evolution        │
└─────────────────────────────────────────────┘
```

---

### **MODULE 7: SQL Analysis Queries & Visualizations**

#### **7.1: Top Skills Analysis**

**Query 1: Top 20 Most Demanded Skills Overall**
```sql
SELECT
    e.skill_text,
    es.preferred_label_es as esco_label,
    COUNT(DISTINCT e.job_id) as demand_count,
    COUNT(DISTINCT r.country) as countries_present,
    ROUND(AVG(e.confidence_score), 2) as avg_confidence,
    COUNT(CASE WHEN e.mapping_method = 'exact' THEN 1 END) as exact_matches,
    COUNT(CASE WHEN e.mapping_method = 'fuzzy' THEN 1 END) as fuzzy_matches,
    COUNT(CASE WHEN e.mapping_method = 'semantic' THEN 1 END) as semantic_matches
FROM extracted_skills e
INNER JOIN raw_jobs r ON e.job_id = r.job_id
LEFT JOIN esco_skills es ON e.esco_uri = es.esco_uri
WHERE r.is_usable = TRUE
GROUP BY e.skill_text, es.preferred_label_es
ORDER BY demand_count DESC
LIMIT 20;
```

**Query 2: Top Skills by Country**
```sql
SELECT
    r.country,
    e.skill_text,
    COUNT(*) as demand_count,
    ROUND(AVG(e.confidence_score), 2) as avg_confidence
FROM extracted_skills e
INNER JOIN raw_jobs r ON e.job_id = r.job_id
WHERE r.is_usable = TRUE
GROUP BY r.country, e.skill_text
ORDER BY r.country, demand_count DESC;
```

**Query 3: Temporal Skill Trends (Last 12 Months)**
```sql
SELECT
    DATE_TRUNC('month', r.posted_date) as month,
    e.skill_text,
    COUNT(DISTINCT e.job_id) as demand_count
FROM extracted_skills e
INNER JOIN raw_jobs r ON e.job_id = r.job_id
WHERE r.posted_date >= CURRENT_DATE - INTERVAL '12 months'
  AND r.is_usable = TRUE
GROUP BY month, e.skill_text
ORDER BY month DESC, demand_count DESC;
```

---

#### **7.2: Skill Co-occurrence Analysis**

**Query 4: Frequent Skill Pairs**
```sql
WITH skill_pairs AS (
    SELECT
        e1.skill_text as skill_1,
        e2.skill_text as skill_2,
        e1.job_id
    FROM extracted_skills e1
    INNER JOIN extracted_skills e2
        ON e1.job_id = e2.job_id
        AND e1.skill_text < e2.skill_text  -- Avoid duplicates
)
SELECT
    skill_1,
    skill_2,
    COUNT(*) as co_occurrence_count,
    ROUND(
        COUNT(*)::DECIMAL / (
            SELECT COUNT(DISTINCT job_id) FROM raw_jobs WHERE is_usable = TRUE
        ) * 100,
        2
    ) as percentage_of_jobs
FROM skill_pairs
GROUP BY skill_1, skill_2
ORDER BY co_occurrence_count DESC
LIMIT 50;
```

**Purpose:** Identify common skill combinations (e.g., Python + Django, React + TypeScript)

---

#### **7.3: Geographic Skill Distribution**

**Query 5: Skills Unique to Each Country**
```sql
-- Skills found ONLY in Colombia
SELECT
    e.skill_text,
    COUNT(*) as demand_count
FROM extracted_skills e
INNER JOIN raw_jobs r ON e.job_id = r.job_id
WHERE r.country = 'CO'
  AND r.is_usable = TRUE
  AND e.skill_text NOT IN (
      SELECT DISTINCT skill_text
      FROM extracted_skills e2
      INNER JOIN raw_jobs r2 ON e2.job_id = r2.job_id
      WHERE r2.country IN ('MX', 'AR')
  )
GROUP BY e.skill_text
ORDER BY demand_count DESC
LIMIT 20;

-- Repeat for MX and AR
```

**Query 6: Skill Demand by Portal**
```sql
SELECT
    r.portal,
    e.skill_text,
    COUNT(*) as demand_count
FROM extracted_skills e
INNER JOIN raw_jobs r ON e.job_id = r.job_id
WHERE r.is_usable = TRUE
GROUP BY r.portal, e.skill_text
ORDER BY r.portal, demand_count DESC;
```

---

#### **7.4: Cluster Analysis Queries**

**Query 7: Cluster Statistics**
```sql
SELECT
    cluster_id,
    COUNT(*) as job_count,
    COUNT(DISTINCT country) as countries,
    COUNT(DISTINCT portal) as portals,
    ROUND(AVG(cluster_probability), 2) as avg_probability,
    ARRAY_AGG(DISTINCT country) as country_list
FROM raw_jobs
WHERE cluster_id IS NOT NULL
  AND is_usable = TRUE
GROUP BY cluster_id
ORDER BY job_count DESC;
```

**Query 8: Top Skills per Cluster**
```sql
SELECT
    r.cluster_id,
    e.skill_text,
    COUNT(*) as skill_count,
    ROUND(AVG(e.confidence_score), 2) as avg_confidence
FROM extracted_skills e
INNER JOIN raw_jobs r ON e.job_id = r.job_id
WHERE r.cluster_id IS NOT NULL
  AND r.is_usable = TRUE
GROUP BY r.cluster_id, e.skill_text
ORDER BY r.cluster_id, skill_count DESC;
```

**Query 9: Cluster Temporal Evolution**
```sql
SELECT
    cluster_id,
    DATE_TRUNC('month', posted_date) as month,
    COUNT(*) as job_count
FROM raw_jobs
WHERE cluster_id IS NOT NULL
  AND is_usable = TRUE
  AND posted_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY cluster_id, month
ORDER BY month, cluster_id;
```

---

#### **7.5: Pipeline Comparison Queries**

**Query 10: Pipeline A vs B Coverage**
```sql
-- Pipeline A (Regex + NER)
WITH pipeline_a AS (
    SELECT COUNT(DISTINCT skill_text) as unique_skills_a
    FROM extracted_skills
    WHERE extraction_method IN ('regex', 'ner')
),
-- Pipeline B (LLM)
pipeline_b AS (
    SELECT COUNT(DISTINCT skill_text) as unique_skills_b
    FROM extracted_skills
    WHERE extraction_method LIKE 'llm%'
),
-- Overlap
overlap AS (
    SELECT COUNT(DISTINCT e1.skill_text) as overlap_count
    FROM extracted_skills e1
    WHERE extraction_method IN ('regex', 'ner')
      AND EXISTS (
          SELECT 1 FROM extracted_skills e2
          WHERE e2.skill_text = e1.skill_text
            AND e2.extraction_method LIKE 'llm%'
      )
)
SELECT
    a.unique_skills_a,
    b.unique_skills_b,
    o.overlap_count,
    (a.unique_skills_a - o.overlap_count) as a_only,
    (b.unique_skills_b - o.overlap_count) as b_only,
    ROUND(o.overlap_count::DECIMAL / (a.unique_skills_a + b.unique_skills_b - o.overlap_count) * 100, 2) as jaccard_similarity
FROM pipeline_a a, pipeline_b b, overlap o;
```

---

#### **7.6: Emergent Skills Tracking**

**Query 11: Top Emergent Skills (Unmapped to ESCO)**
```sql
SELECT
    skill_text,
    occurrence_count,
    extraction_methods,
    best_esco_match,
    ROUND(best_similarity, 2) as similarity,
    first_seen_job_id,
    review_status
FROM emergent_skills
WHERE review_status = 'pending'
ORDER BY occurrence_count DESC
LIMIT 50;
```

**Purpose:** Identify new/emerging skills not in ESCO taxonomy that should be reviewed for inclusion

---

#### **7.7: Data Quality Metrics**

**Query 12: Extraction Success Rates**
```sql
SELECT
    portal,
    country,
    COUNT(*) as total_jobs,
    COUNT(CASE WHEN extraction_status = 'completed' THEN 1 END) as extracted,
    COUNT(CASE WHEN extraction_status = 'failed' THEN 1 END) as failed,
    ROUND(
        COUNT(CASE WHEN extraction_status = 'completed' THEN 1 END)::DECIMAL / COUNT(*) * 100,
        2
    ) as success_rate
FROM raw_jobs
WHERE is_usable = TRUE
GROUP BY portal, country
ORDER BY portal, country;
```

**Query 13: ESCO Mapping Success Rate**
```sql
SELECT
    extraction_method,
    COUNT(*) as total_skills,
    COUNT(CASE WHEN esco_uri IS NOT NULL THEN 1 END) as mapped,
    COUNT(CASE WHEN esco_uri IS NULL THEN 1 END) as unmapped,
    ROUND(
        COUNT(CASE WHEN esco_uri IS NOT NULL THEN 1 END)::DECIMAL / COUNT(*) * 100,
        2
    ) as mapping_success_rate
FROM extracted_skills
GROUP BY extraction_method
ORDER BY extraction_method;
```

---

#### **7.8: Visualization Types**

**1. Top Skills Bar Chart**
- X-axis: Skill name
- Y-axis: Demand count
- Color: ESCO category
- Data: Query 1

**2. Temporal Trend Line Chart**
- X-axis: Month
- Y-axis: Demand count
- Lines: Top 10 skills
- Data: Query 3

**3. Geographic Heat Map**
- Map of CO, MX, AR
- Color intensity: Skill demand per country
- Data: Query 2

**4. Skill Co-occurrence Network**
- Nodes: Skills
- Edges: Co-occurrence count
- Layout: Force-directed
- Data: Query 4

**5. Cluster Scatter Plot (UMAP 2D)**
- X, Y: UMAP coordinates
- Color: Cluster ID
- Size: Cluster probability
- Data: job_embeddings_reduced table

**6. Pipeline Comparison Venn Diagram**
- Circle A: Pipeline A skills
- Circle B: Pipeline B skills
- Overlap: Shared skills
- Data: Query 10

**Visualization Tools:**
- Plotly (interactive charts)
- Matplotlib/Seaborn (static charts)
- NetworkX (skill networks)
- Export formats: PNG, SVG, HTML, PDF

**Files:** `src/analyzer/visualizations.py`, `src/analyzer/report_generator.py`
**Status:** ❌ Not implemented

---

## 📋 **Database Schema - ACTUALIZADO**

```sql
-- ============================================================
-- EXTRACTION & MAPPING TABLES
-- ============================================================

extracted_skills (
    extraction_id UUID PRIMARY KEY,
    job_id UUID REFERENCES raw_jobs(job_id),

    -- Extracted skill
    skill_text TEXT NOT NULL,
    extraction_method VARCHAR(50),  -- 'regex', 'ner', 'llm_explicit', 'llm_implicit'

    -- LLM-specific
    llm_model VARCHAR(100),          -- 'gpt-3.5-turbo', 'mistral-7b', 'llama-2-7b'
    skill_type VARCHAR(20),          -- 'explicit', 'implicit' (LLM only)
    evidence_text TEXT,              -- LLM reasoning

    -- Confidence
    confidence_score REAL,           -- 0.0 to 1.0

    -- ESCO Mapping (results from Module 4)
    esco_uri VARCHAR(255),           -- NULL if unmapped
    esco_label TEXT,
    mapping_method VARCHAR(50),      -- 'exact', 'fuzzy', 'semantic', 'unmapped'
    mapping_confidence REAL,         -- 0.0 to 1.0

    -- Metadata
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(job_id, skill_text, extraction_method)
)

-- ============================================================
-- EMERGENT SKILLS (unmapped from Module 4)
-- ============================================================

emergent_skills (
    emergent_id UUID PRIMARY KEY,
    skill_text TEXT UNIQUE,

    -- Tracking
    first_seen_job_id UUID REFERENCES raw_jobs(job_id),
    occurrence_count INTEGER DEFAULT 1,
    extraction_methods TEXT[],       -- ['llm', 'ner', 'regex']

    -- Best attempt at mapping
    best_esco_match VARCHAR(255),    -- Nearest ESCO skill (even if < threshold)
    best_similarity REAL,            -- Similarity score

    -- Manual review
    flag_reason VARCHAR(100),
    review_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'approved', 'rejected', 'mapped'
    reviewed_at TIMESTAMP,
    reviewer_notes TEXT,

    -- If approved, map to custom or ESCO
    custom_category VARCHAR(100),
    mapped_to_esco_uri VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

-- ============================================================
-- ESCO EMBEDDINGS (from Module 4 setup)
-- ============================================================

skill_embeddings (
    embedding_id UUID PRIMARY KEY,
    esco_uri VARCHAR(255) REFERENCES esco_skills(esco_uri),
    skill_text TEXT,

    -- Embedding
    embedding_vector REAL[768],      -- E5 multilingual embeddings
    model_name VARCHAR(100) DEFAULT 'multilingual-e5-base',
    embedding_dimension INTEGER DEFAULT 768,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(esco_uri, model_name)
)

-- ============================================================
-- JOB EMBEDDINGS (for clustering)
-- ============================================================

job_embeddings (
    job_id UUID PRIMARY KEY REFERENCES raw_jobs(job_id),

    -- Full embedding
    embedding_vector REAL[768],
    embedding_method VARCHAR(50),    -- 'skill_aggregation', 'full_text'
    model_name VARCHAR(100),

    -- Reduced for visualization
    umap_x REAL,
    umap_y REAL,
    umap_z REAL,                     -- NULL if 2D
    n_components INTEGER,            -- 2 or 3

    -- Cluster assignment
    cluster_id INTEGER,              -- NULL or -1 = noise
    cluster_probability REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

---
