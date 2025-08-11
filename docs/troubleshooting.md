# 🚨 Troubleshooting Guide - Labor Market Observatory

> **Common issues and solutions for the Labor Market Observatory system**

## 📋 Table of Contents

- [🔍 Common Issues](#-common-issues)
- [🐛 Error Messages](#-error-messages)
- [🔧 Database Problems](#-database-problems)
- [🕷️ Scraping Issues](#️-scraping-issues)
- [🤖 LLM Problems](#-llm-problems)
- [📊 Analysis Issues](#-analysis-issues)
- [⚙️ Configuration Problems](#️-configuration-problems)
- [🚀 Performance Issues](#-performance-issues)
- [📞 Getting Help](#-getting-help)

## 🔍 Common Issues

### **System Won't Start**

#### **Problem**: Module import errors
```
ModuleNotFoundError: No module named 'config'
```

**Solution**: 
1. Ensure you're in the project root directory
2. Install dependencies: `pip install -r requirements.txt`
3. Check Python path: `export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"`

#### **Problem**: Configuration file not found
```
FileNotFoundError: .env file not found
```

**Solution**:
1. Copy `.env.example` to `.env`
2. Fill in required environment variables
3. Ensure file permissions are correct

### **Database Connection Issues**

#### **Problem**: PostgreSQL connection failed
```
OperationalError: (psycopg2.OperationalError) could not connect to server
```

**Solutions**:
1. **Check PostgreSQL service**:
   ```bash
   # Ubuntu/Debian
   sudo systemctl status postgresql
   
   # macOS
   brew services list | grep postgresql
   
   # Windows
   services.msc  # Look for PostgreSQL service
   ```

2. **Verify connection details**:
   ```bash
   # Test connection
   psql -h localhost -U your_user -d labor_observatory
   ```

3. **Check firewall settings**:
   ```bash
   # Ubuntu/Debian
   sudo ufw status
   
   # macOS
   sudo pfctl -s rules
   ```

#### **Problem**: pgvector extension not found
```
ERROR: extension "pgvector" is not available
```

**Solution**:
1. Install pgvector extension:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql-15-pgvector
   
   # macOS
   brew install pgvector
   ```

2. Enable extension in database:
   ```sql
   CREATE EXTENSION IF NOT EXISTS "pgvector";
   ```

### **Scraping Issues**

#### **Problem**: Spider not starting
```
No spider found with name 'computrabajo'
```

**Solution**:
1. Check spider registration in `src/scraper/spiders/__init__.py`
2. Verify spider class names match expected names
3. Check for syntax errors in spider files

#### **Problem**: Rate limiting/blocking
```
HTTP 429: Too Many Requests
```

**Solutions**:
1. **Increase delays**:
   ```python
   # In src/scraper/settings.py
   DOWNLOAD_DELAY = 2.0
   RANDOMIZE_DOWNLOAD_DELAY = True
   ```

2. **Rotate user agents**:
   ```python
   # In src/scraper/settings.py
   DOWNLOADER_MIDDLEWARES = {
       'scraper.middlewares.RotateUserAgentMiddleware': 400,
   }
   ```

3. **Use proxy rotation** (if available):
   ```python
   # In src/scraper/settings.py
   DOWNLOADER_MIDDLEWARES = {
       'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
   }
   ```

#### **Problem**: Selectors not working
```
No data extracted from job postings
```

**Solutions**:
1. **Check website structure changes**:
   - Visit the job portal manually
   - Inspect HTML elements
   - Update CSS selectors in spider

2. **Use browser developer tools**:
   - Right-click → Inspect Element
   - Check for dynamic content loading
   - Verify selector paths

3. **Add debugging**:
   ```python
   # In spider
   def parse_job(self, response):
       # Debug response
       print(f"Response URL: {response.url}")
       print(f"Response status: {response.status}")
       
       # Test selectors
       title = response.css('h1::text').get()
       print(f"Title selector result: {title}")
   ```

### **LLM Processing Issues**

#### **Problem**: Model not loading
```
FileNotFoundError: Model file not found
```

**Solutions**:
1. **Check model path**:
   ```bash
   # Verify model exists
   ls -la /path/to/your/model.gguf
   ```

2. **Download model**:
   ```bash
   # Download Mistral 7B
   wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf
   ```

3. **Update environment variable**:
   ```bash
   export LLM_MODEL_PATH="/path/to/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
   ```

#### **Problem**: Out of memory errors
```
CUDA out of memory
```

**Solutions**:
1. **Reduce GPU layers**:
   ```bash
   export LLM_N_GPU_LAYERS=20  # Reduce from 35
   ```

2. **Use CPU only**:
   ```bash
   export LLM_N_GPU_LAYERS=0
   ```

3. **Reduce batch size**:
   ```bash
   export LLM_BATCH_SIZE=1
   ```

#### **Problem**: OpenAI API errors
```
openai.error.AuthenticationError: Invalid API key
```

**Solutions**:
1. **Check API key**:
   ```bash
   echo $OPENAI_API_KEY
   ```

2. **Verify key format**:
   - Should start with `sk-`
   - No extra spaces or characters

3. **Check account status**:
   - Visit OpenAI dashboard
   - Verify billing and usage limits

### **Analysis Issues**

#### **Problem**: Clustering not working
```
ValueError: Input contains NaN values
```

**Solutions**:
1. **Clean embeddings**:
   ```python
   import numpy as np
   
   # Remove NaN values
   embeddings = [emb for emb in embeddings if not np.isnan(emb).any()]
   ```

2. **Check embedding generation**:
   - Verify all skills have embeddings
   - Check for empty or invalid text

#### **Problem**: UMAP errors
```
ValueError: Input contains infinite values
```

**Solutions**:
1. **Normalize embeddings**:
   ```python
   from sklearn.preprocessing import StandardScaler
   
   scaler = StandardScaler()
   normalized_embeddings = scaler.fit_transform(embeddings)
   ```

2. **Check for infinite values**:
   ```python
   import numpy as np
   
   # Check for inf values
   has_inf = np.isinf(embeddings).any()
   print(f"Has infinite values: {has_inf}")
   ```

## 🐛 Error Messages

### **Common Python Errors**

| Error | Cause | Solution |
|-------|-------|----------|
| `ImportError` | Missing dependencies | `pip install -r requirements.txt` |
| `AttributeError` | Object has no attribute | Check object type and methods |
| `TypeError` | Wrong data type | Verify input data types |
| `ValueError` | Invalid value | Check input validation |
| `KeyError` | Missing dictionary key | Verify key exists in dict |
| `IndexError` | List index out of range | Check list length before indexing |

### **Database Errors**

| Error | Cause | Solution |
|-------|-------|----------|
| `OperationalError` | Connection failed | Check PostgreSQL service |
| `IntegrityError` | Constraint violation | Check data validation |
| `ProgrammingError` | SQL syntax error | Verify SQL queries |
| `DataError` | Invalid data type | Check column types |

### **Scrapy Errors**

| Error | Cause | Solution |
|-------|-------|----------|
| `SpiderError` | Spider configuration issue | Check spider settings |
| `DropItem` | Item validation failed | Review item pipeline |
| `IgnoreRequest` | Request filtered out | Check downloader middleware |

## 🔧 Database Problems

### **Database Schema Issues**

#### **Problem**: Tables not created
```sql
ERROR: relation "raw_jobs" does not exist
```

**Solution**:
1. Run migration script:
   ```bash
   psql -h localhost -U your_user -d labor_observatory -f src/database/migrations/001_initial_schema.sql
   ```

2. Check table creation:
   ```sql
   \dt labor_observatory.*
   ```

#### **Problem**: Permission denied
```
ERROR: permission denied for table raw_jobs
```

**Solution**:
1. Grant permissions:
   ```sql
   GRANT ALL PRIVILEGES ON TABLE raw_jobs TO your_user;
   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
   ```

2. Check user roles:
   ```sql
   \du your_user
   ```

### **Performance Issues**

#### **Problem**: Slow queries
```
Query taking too long to execute
```

**Solutions**:
1. **Check indexes**:
   ```sql
   -- List indexes
   \d+ raw_jobs
   
   -- Create missing indexes
   CREATE INDEX IF NOT EXISTS idx_job_title ON raw_jobs(title);
   ```

2. **Analyze table statistics**:
   ```sql
   ANALYZE raw_jobs;
   ANALYZE extracted_skills;
   ```

3. **Check query plans**:
   ```sql
   EXPLAIN ANALYZE SELECT * FROM raw_jobs WHERE country = 'CO';
   ```

## 🕷️ Scraping Issues

### **Website Changes**

#### **Problem**: Selectors broken after website update
```
No data extracted from updated website
```

**Solution**:
1. **Inspect new structure**:
   - Use browser developer tools
   - Check for new CSS classes or IDs
   - Look for JavaScript-rendered content

2. **Update selectors**:
   ```python
   # Old selector
   title = response.css('h1.job-title::text').get()
   
   # New selector (example)
   title = response.css('h1[data-testid="job-title"]::text').get()
   ```

3. **Add fallback selectors**:
   ```python
   def extract_text(self, response, selectors):
       for selector in selectors:
           text = response.css(selector).get()
           if text:
               return text.strip()
       return ""
   
   # Usage
   title = self.extract_text(response, [
       'h1.job-title::text',
       'h1[data-testid="job-title"]::text',
       'h1::text'
   ])
   ```

### **Anti-Bot Measures**

#### **Problem**: Getting blocked by websites
```
HTTP 403: Forbidden
```

**Solutions**:
1. **Rotate user agents**:
   ```python
   # In middleware
   user_agents = [
       'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
       'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
       'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
   ]
   ```

2. **Add delays and randomization**:
   ```python
   DOWNLOAD_DELAY = 3.0
   RANDOMIZE_DOWNLOAD_DELAY = True
   DOWNLOAD_DELAY_RANGE = (2, 5)
   ```

3. **Use proxy rotation** (if available):
   ```python
   PROXY_LIST = [
       'http://proxy1:port',
       'http://proxy2:port'
   ]
   ```

## 🤖 LLM Problems

### **Model Loading Issues**

#### **Problem**: CUDA out of memory
```
RuntimeError: CUDA out of memory
```

**Solutions**:
1. **Reduce GPU memory usage**:
   ```bash
   export LLM_N_GPU_LAYERS=20
   export LLM_CONTEXT_LENGTH=2048
   ```

2. **Use CPU only**:
   ```bash
   export LLM_N_GPU_LAYERS=0
   ```

3. **Monitor GPU memory**:
   ```bash
   nvidia-smi
   watch -n 1 nvidia-smi
   ```

#### **Problem**: Model file corrupted
```
Error loading model: Invalid model file
```

**Solution**:
1. **Re-download model**:
   ```bash
   rm /path/to/corrupted/model.gguf
   wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf
   ```

2. **Verify file integrity**:
   ```bash
   # Check file size
   ls -lh /path/to/model.gguf
   
   # Check file type
   file /path/to/model.gguf
   ```

### **Generation Issues**

#### **Problem**: LLM not responding
```
No response from LLM
```

**Solutions**:
1. **Check model status**:
   ```python
   # Test simple generation
   response = llm.generate("Hello")
   print(f"Response: {response}")
   ```

2. **Verify input format**:
   ```python
   # Check prompt format
   print(f"Prompt: {prompt}")
   print(f"Prompt length: {len(prompt)}")
   ```

3. **Check system resources**:
   ```bash
   # Monitor CPU/memory
   top
   htop
   ```

## 📊 Analysis Issues

### **Clustering Problems**

#### **Problem**: All skills in one cluster
```
Only one cluster detected
```

**Solutions**:
1. **Adjust HDBSCAN parameters**:
   ```python
   clusterer = HDBSCAN(
       min_cluster_size=3,      # Reduce from 5
       min_samples=2,           # Reduce from 3
       cluster_selection_epsilon=0.1
   )
   ```

2. **Check embedding quality**:
   ```python
   # Verify embeddings
   print(f"Embedding shape: {embeddings.shape}")
   print(f"Embedding range: {embeddings.min():.3f} to {embeddings.max():.3f}")
   ```

#### **Problem**: Too many small clusters
```
Hundreds of tiny clusters
```

**Solutions**:
1. **Increase minimum cluster size**:
   ```python
   clusterer = HDBSCAN(
       min_cluster_size=10,     # Increase from 5
       min_samples=5            # Increase from 3
   )
   ```

2. **Adjust UMAP parameters**:
   ```python
   reducer = UMAP(
       n_neighbors=30,          # Increase from 15
       min_dist=0.2             # Increase from 0.1
   )
   ```

### **Visualization Issues**

#### **Problem**: Charts not generating
```
No visualization files created
```

**Solutions**:
1. **Check output directory**:
   ```python
   import os
   print(f"Output dir exists: {os.path.exists(output_dir)}")
   print(f"Output dir writable: {os.access(output_dir, os.W_OK)}")
   ```

2. **Verify matplotlib backend**:
   ```python
   import matplotlib
   print(f"Backend: {matplotlib.get_backend()}")
   
   # Set backend if needed
   matplotlib.use('Agg')
   ```

3. **Check for errors in generation**:
   ```python
   try:
       viz.create_skill_frequency_chart(data)
   except Exception as e:
       print(f"Visualization error: {e}")
       import traceback
       traceback.print_exc()
   ```

## ⚙️ Configuration Problems

### **Environment Variables**

#### **Problem**: Variables not loaded
```
Configuration values are None
```

**Solutions**:
1. **Check .env file**:
   ```bash
   # Verify file exists
   ls -la .env
   
   # Check content
   cat .env
   ```

2. **Verify variable names**:
   ```bash
   # Check environment
   env | grep -i labor
   ```

3. **Test configuration loading**:
   ```python
   from config.settings import get_settings
   
   try:
       settings = get_settings()
       print(f"Database URL: {settings.database_url}")
   except Exception as e:
       print(f"Config error: {e}")
   ```

### **File Permissions**

#### **Problem**: Cannot write to output directory
```
PermissionError: [Errno 13] Permission denied
```

**Solutions**:
1. **Check directory permissions**:
   ```bash
   ls -la outputs/
   ```

2. **Fix permissions**:
   ```bash
   chmod 755 outputs/
   chmod 755 logs/
   ```

3. **Check ownership**:
   ```bash
   ls -la outputs/
   sudo chown $USER:$USER outputs/
   ```

## 🚀 Performance Issues

### **Slow Processing**

#### **Problem**: Pipeline taking too long
```
Processing 1000 jobs takes hours
```

**Solutions**:
1. **Increase batch sizes**:
   ```bash
   export EXTRACTION_BATCH_SIZE=200
   export LLM_BATCH_SIZE=100
   ```

2. **Use parallel processing**:
   ```python
   from concurrent.futures import ThreadPoolExecutor
   
   with ThreadPoolExecutor(max_workers=4) as executor:
       futures = [executor.submit(process_job, job) for job in jobs]
   ```

3. **Optimize database queries**:
   ```python
   # Use bulk operations
   session.bulk_save_objects(jobs)
   session.commit()
   ```

### **Memory Issues**

#### **Problem**: Out of memory errors
```
MemoryError: Unable to allocate array
```

**Solutions**:
1. **Process in smaller batches**:
   ```python
   batch_size = 50  # Reduce from 100
   ```

2. **Clear memory periodically**:
   ```python
   import gc
   
   # After processing batch
   gc.collect()
   ```

3. **Use generators for large datasets**:
   ```python
   def job_generator():
       for job in jobs:
           yield job
   ```

## 📞 Getting Help

### **Self-Diagnosis**

1. **Check logs**:
   ```bash
   tail -f logs/labor_observatory.log
   ```

2. **Enable debug logging**:
   ```bash
   export LOG_LEVEL=DEBUG
   ```

3. **Run with verbose output**:
   ```bash
   python src/orchestrator.py scrape CO computrabajo --verbose
   ```

### **Community Resources**

1. **GitHub Issues**: Check existing issues in the repository
2. **Documentation**: Review the complete implementation guide
3. **Stack Overflow**: Search for similar problems
4. **Discord/Slack**: Join developer communities

### **Reporting Issues**

When reporting an issue, include:

1. **Environment details**:
   - OS version
   - Python version
   - Package versions

2. **Error messages**:
   - Full traceback
   - Log output
   - Screenshots if applicable

3. **Steps to reproduce**:
   - Exact commands run
   - Input data
   - Expected vs actual output

4. **System information**:
   - Hardware specs
   - Available memory
   - Database version

---

**This troubleshooting guide covers the most common issues. If your problem isn't listed, check the logs and try the self-diagnosis steps.** 🚀
