# Scraper Module

This module provides a comprehensive web scraping solution for job portals with advanced features like user agent rotation, proxy support, retry mechanisms, and deduplication.

## Features

- **Multiple Spiders**: Support for infojobs, elempleo, bumeran, computrabajo, and lego
- **User Agent Rotation**: Automatic rotation of user agents to avoid detection
- **Proxy Support**: Configurable proxy rotation with authentication
- **Retry Mechanism**: Exponential backoff retry for failed requests
- **Deduplication**: Content-based deduplication using SHA256 hashing
- **Scheduling**: Support for both APScheduler and stateless execution
- **Multi-country Support**: CO, MX, AR

## Quick Start

### 1. Setup Environment

Copy the environment example and configure it:

```bash
cp env.example .env
# Edit .env with your database credentials and settings
```

### 2. Start Database

```bash
docker compose up -d postgres
```

### 3. Run Database Migration

```bash
docker exec -i labor_pg psql -U labor_user -d labor_observatory < src/database/migrations/001_initial_schema.sql
```

### 4. Run a Single Spider

```bash
python -m src.orchestrator run-once infojobs --country CO --limit 100
```

### 5. Run Multiple Spiders

```bash
python -m src.orchestrator run infojobs,elempleo,bumeran --country CO --limit 500
```

## Available Spiders

| Spider | Countries | Description |
|--------|-----------|-------------|
| infojobs | CO, MX, AR | InfoJobs job portal |
| elempleo | CO, MX, AR | El Empleo job portal |
| bumeran | CO, MX, AR | Bumeran job portal |
| computrabajo | CO, MX, AR | Computrabajo job portal |
| lego | CO, MX, AR | LEGO careers (example) |

## Configuration

### Environment Variables

Key environment variables for the scraper:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=labor_observatory
DB_USER=labor_user
DB_PASSWORD=your_password

# Scrapy Settings
SCRAPY_DOWNLOAD_DELAY=1.0
SCRAPY_CONCURRENT_REQUESTS=16
SCRAPY_DOWNLOAD_TIMEOUT=20
SCRAPY_RETRY_TIMES=3

# Proxies
PROXY_POOL=http://user:pass@proxy1:port,http://user:pass@proxy2:port
PROXY_ROTATION_STRATEGY=round_robin

# User Agents
USER_AGENT_LIST_PATH=./config/user_agents.txt
USER_AGENT_ROTATION_STRATEGY=round_robin
```

### User Agents

The system uses a pool of modern user agents located in `config/user_agents.txt`. You can customize this file with your own user agents.

## Scheduling

### Option 1: APScheduler (Recommended)

Use the built-in scheduler for continuous operation:

```bash
# Start scheduler
python -m src.orchestrator schedule start

# Stop scheduler
python -m src.orchestrator schedule stop
```

The scheduler reads configuration from `config/schedule.yaml`:

```yaml
jobs:
  - spider: infojobs
    country: CO
    trigger: cron
    cron: "0 */4 * * *"  # Every 4 hours
    max_pages: 10
    limit: 200
```

### Option 2: Cron/Windows Task Scheduler

For stateless execution suitable for cron or Windows Task Scheduler:

```bash
# Run once with specific spiders
python scripts/run_once.py --spiders infojobs,elempleo --country CO --limit 100

# Save results to file
python scripts/run_once.py --spiders infojobs --country CO --output results.json
```

## Command Line Interface

The orchestrator provides a comprehensive CLI:

```bash
# List available spiders
python -m src.orchestrator list-spiders

# Check system status
python -m src.orchestrator status

# Run multiple spiders
python -m src.orchestrator run infojobs,elempleo --country CO --limit 500

# Run single spider
python -m src.orchestrator run-once infojobs --country CO --limit 100

# Start/stop scheduler
python -m src.orchestrator schedule start
python -m src.orchestrator schedule stop
```

## Database Schema

Jobs are stored in the `raw_jobs` table with the following structure:

```sql
CREATE TABLE raw_jobs (
    job_id UUID PRIMARY KEY,
    portal VARCHAR(50) NOT NULL,
    country CHAR(2) NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    description TEXT NOT NULL,
    requirements TEXT,
    salary_raw TEXT,
    contract_type VARCHAR(50),
    remote_type VARCHAR(50),
    posted_date DATE,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_hash VARCHAR(64) UNIQUE,  -- For deduplication
    raw_html TEXT,
    is_processed BOOLEAN DEFAULT FALSE
);
```

## Deduplication

The system uses content-based deduplication:

1. **Content Hash**: SHA256 hash of title + description + requirements
2. **Database Constraint**: UNIQUE constraint on content_hash
3. **Pipeline Logic**: ON CONFLICT DO NOTHING to skip duplicates
4. **Logging**: Duplicates are logged for monitoring

## Middlewares

### UserAgentRotationMiddleware

- Loads user agents from file or uses defaults
- Supports round-robin and random rotation strategies
- Configurable via `USER_AGENT_ROTATION_STRATEGY`

### ProxyRotationMiddleware

- Supports HTTP proxies with authentication
- Configurable rotation strategy
- Loads from `PROXY_POOL` environment variable

### RetryWithBackoffMiddleware

- Exponential backoff for failed requests
- Retries on HTTP 429, 502-504, and timeouts
- Configurable retry count and backoff

## Error Handling

The system includes comprehensive error handling:

- **Database Errors**: Connection failures, constraint violations
- **Network Errors**: Timeouts, connection refused
- **Parsing Errors**: Invalid HTML, missing selectors
- **Rate Limiting**: Automatic retry with backoff

## Monitoring

### Logs

Logs are written to:
- `logs/scrapy.log` - Scrapy-specific logs
- `logs/labor_observatory.log` - Application logs

### Status Command

Check system health and statistics:

```bash
python -m src.orchestrator status
```

This shows:
- Database connection status
- Job counts by portal
- Last scraping times

## Adding New Spiders

To add a new spider:

1. Create a new spider class inheriting from `BaseSpider`
2. Implement `parse_search_results()` and `parse_job()` methods
3. Add to `AVAILABLE_SPIDERS` in orchestrator
4. Update configuration files

Example:

```python
class NewSpider(BaseSpider):
    name = "newspider"
    allowed_domains = ["example.com"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "newspider"
        self.start_urls = ['https://example.com/jobs']
    
    def parse_search_results(self, response):
        # Parse job listings
        pass
    
    def parse_job(self, response):
        # Parse individual job
        pass
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check database credentials in `.env`
   - Ensure PostgreSQL is running
   - Verify database exists

2. **Spider Not Found**
   - Check spider name spelling
   - Ensure spider is in `AVAILABLE_SPIDERS`
   - Verify spider class exists

3. **No Jobs Scraped**
   - Check website structure hasn't changed
   - Verify CSS selectors in spider
   - Check for rate limiting

4. **Duplicate Jobs**
   - This is normal behavior
   - Check logs for "Duplicate job skipped" messages
   - Verify content_hash is working correctly

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python -m src.orchestrator run-once infojobs --country CO
```

## Performance Tuning

### Concurrent Requests

Adjust based on target website capacity:

```bash
export SCRAPY_CONCURRENT_REQUESTS=8  # Conservative
export SCRAPY_CONCURRENT_REQUESTS=32 # Aggressive
```

### Download Delays

Balance between speed and politeness:

```bash
export SCRAPY_DOWNLOAD_DELAY=0.5  # Fast
export SCRAPY_DOWNLOAD_DELAY=2.0  # Polite
```

### Timeouts

Adjust for slow websites:

```bash
export SCRAPY_DOWNLOAD_TIMEOUT=30  # Longer timeout
```

## Security Considerations

1. **Proxy Usage**: Use proxies for production scraping
2. **Rate Limiting**: Respect website rate limits
3. **User Agents**: Rotate user agents to avoid detection
4. **Credentials**: Store sensitive data in environment variables
5. **Logging**: Avoid logging sensitive information

## Support

For issues and questions:

1. Check the logs for error messages
2. Verify configuration is correct
3. Test with a single spider first
4. Check database connectivity
5. Review the troubleshooting section above
