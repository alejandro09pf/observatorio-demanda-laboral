# LLM Model Comparison - 10 Jobs Test
**Generated:** 2025-11-06 00:54:03
**Jobs Tested:** 10 randomly selected from gold standard
**Models:** Gemma 3 4B, Llama 3.2 3B, Qwen2.5 3B, Phi-3 Mini

---

## Performance Summary

| Model | Jobs Processed | Errors | Avg Time/Job | Total Time | Load Time |
|-------|----------------|--------|--------------|------------|----------|
| llama-3.2-3b-instruct | 0/10 | 1 | 0.00s | 0.00s | 2.78s |
| qwen2.5-3b-instruct | 0/10 | 1 | 0.00s | 0.00s | 2.59s |
| phi-3.5-mini | 0/10 | 1 | 0.00s | 0.00s | 3.44s |

---

## Next Steps

Run evaluation script to compare vs gold standard:

```bash
python scripts/evaluate_pipelines.py --mode subset \
  --job-ids-file /tmp/selected_10_jobs.csv \
  --pipelines llama-3.2-3b-instruct qwen2.5-3b-instruct phi-3.5-mini \
  --skill-type hard
```
