# SEMANTIC DEDUPLICATION REPORT

**Generated:** 2025-11-04

---

## 📊 SUMMARY STATISTICS

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total jobs in database** | 56,555 | 100% |
| Semantic duplicates detected | 3,875 | 6.85% |
| Junk jobs (< 50 chars) | 22,020 | 38.94% |
| **Usable unique jobs** | **30,660** | **54.21%** |

---

## 📈 DUPLICATES BY PORTAL

| Portal | Duplicates | % of Total Duplicates |
|--------|------------|---------------------|
| **hiring_cafe** | 1,788 | 46.1% |
| **computrabajo** | 1,614 | 41.7% |
| **occmundial** | 395 | 10.2% |
| **elempleo** | 59 | 1.5% |
| **magneto** | 16 | 0.4% |
| **bumeran** | 3 | 0.1% |
| **zonajobs** | 0 | 0.0% |

---

## 🔍 DUPLICATES BY DETECTION METHOD

| Method | Count | Description |
|--------|-------|-------------|
| **fuzzy_title_description** | 3,414 (88.1%) | Similar titles (≥90%) + similar descriptions (≥95%) |
| **exact_match_normalized** | 461 (11.9%) | Exact match after removing HTML, whitespace, special chars |

---

## ✅ DEDUPLICATION ACTIONS TAKEN

1. **Migration 007 applied** - Added columns to `raw_jobs`:
   - `is_duplicate` (boolean)
   - `duplicate_of` (uuid) → points to original job
   - `duplicate_similarity_score` (float 0-1)
   - `duplicate_detection_method` (varchar)

2. **3,875 jobs marked as duplicates:**
   - `is_duplicate = TRUE`
   - `is_usable = FALSE` (excluded from processing)
   - `duplicate_of` points to best quality job in group

3. **Script created:** `scripts/analyze_semantic_duplicates.py`
   - Dry-run mode by default (safe testing)
   - Optimized algorithm: 81x-359x speedup vs naive O(n²)
   - Multi-level detection (exact + fuzzy)

---

## ⚠️  CLEANUP NEEDED

### Issue: Duplicates in cleaned_jobs table

**Problem:** 2,499 jobs in `cleaned_jobs` are now marked as duplicates in `raw_jobs`.

**Cause:** These jobs were cleaned BEFORE semantic deduplication was executed.

**Impact:**
- These duplicate jobs may be processed by extraction pipeline
- Wasting computational resources on duplicate data
- Potential duplicate skills in analysis results

**Solution Required:**
```sql
-- Delete duplicates from cleaned_jobs
DELETE FROM cleaned_jobs c
USING raw_jobs r
WHERE c.job_id = r.job_id
  AND r.is_duplicate = TRUE;
```

This will remove 2,499 duplicate records from `cleaned_jobs`.

---

## 🎯 EXAMPLES OF DETECTED DUPLICATES

### Example 1: OccMundial - Job ID Variations
**Group:** Auxiliar contable (17 duplicates)
- Original: `Trabajo de Auxiliar contable - 20820373 | OCC`
- Duplicates: Same job, different posting IDs (20820997, 20821879, etc.)
- Similarity: 94.1% - 96.1%

### Example 2: ElEmpleo - Location Variations
**Group:** Vendedores puerta a puerta (4 duplicates)
- Original: `Vendedores tat o puerta a puerta cucuta`
- Duplicates:
  - `Vendedores tat o puerta a puerta cali` (96.1% similar)
  - `Vendedores tat o puerta a puerta funza` (95.5% similar)
  - `Vendedores tat o puerta a puerta chía` (96.1% similar)

### Example 3: ElEmpleo - Exact Match (Formatting)
**Group:** Administrador de proyecto (2 duplicates)
- Original: `Administrador de proyecto**` (2 asterisks)
- Duplicate: `Administrador de proyecto*` (1 asterisk)
- Similarity: 100% after normalization
- Method: exact_match_normalized

---

## 📋 RECOMMENDATIONS

### 1. Clean duplicates from cleaned_jobs (IMMEDIATE)
Run the cleanup SQL to remove 2,499 duplicates.

### 2. Update pipeline dependencies (IMPORTANT)
Ensure all downstream processes filter by:
```sql
WHERE is_usable = TRUE AND is_duplicate = FALSE
```

### 3. Periodic re-deduplication
Run semantic deduplication analysis monthly on new scrapings:
```bash
python scripts/analyze_semantic_duplicates.py --execute
```

### 4. Monitor duplicate rates
Track duplicate percentages by portal to identify problematic sources.

### 5. Adjust thresholds if needed
Current thresholds:
- Title similarity: ≥ 90%
- Description similarity: ≥ 95%

If false positives/negatives found, adjust in script.

---

## 📊 FINAL DATABASE STATE

```
Total Raw Jobs: 56,555
├─ Junk (unusable):              22,020  (38.94%)
├─ Semantic Duplicates:           3,875  (6.85%)
└─ Usable Unique Jobs:           30,660  (54.21%)
    ├─ In cleaned_jobs:          33,159
    │   ├─ Duplicates (NEED CLEANUP): 2,499
    │   └─ Valid cleaned:        30,660
    └─ Ready for extraction:     30,660 ✅
```

---

## 🔧 FILES CREATED

1. `src/database/migrations/007_add_semantic_deduplication.sql` - Database schema
2. `scripts/analyze_semantic_duplicates.py` - Deduplication script
3. `data/reports/DEDUPLICATION_REPORT.md` - This report

---

**Report End**
