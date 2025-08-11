# 🚀 Setup Guide - Labor Market Observatory

> **Complete installation and configuration guide for the Labor Market Observatory system**

## 📋 Table of Contents

- [🎯 Prerequisites](#-prerequisites)
- [🔧 System Installation](#-system-installation)
- [🗄️ Database Setup](#️-database-setup)
- [🐍 Python Environment](#-python-environment)
- [⚙️ Configuration](#-configuration)
- [🧪 Testing Installation](#-testing-installation)
- [🚀 First Run](#-first-run)
- [❌ Troubleshooting](#-troubleshooting)

## 🎯 Prerequisites

### **System Requirements**

- **Operating System**: Windows 10+, macOS 10.15+, Ubuntu 18.04+
- **RAM**: Minimum 8GB, Recommended 16GB+
- **Storage**: Minimum 20GB free space
- **Python**: 3.10 or higher
- **PostgreSQL**: 15 or higher

### **Hardware Recommendations**

- **CPU**: Multi-core processor (4+ cores recommended)
- **GPU**: NVIDIA GPU with 6GB+ VRAM (for LLM processing)
- **Network**: Stable internet connection for web scraping

## 🔧 System Installation

### **1. Install System Dependencies**

#### **Ubuntu/Debian**
```bash
# Update package list
sudo apt-get update

# Install system dependencies
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    postgresql \
    postgresql-contrib \
    postgresql-15 \
    build-essential \
    libpq-dev \
    curl \
    wget \
    git

# Install additional tools
sudo apt-get install -y \
    nginx \
    supervisor \
    redis-server
```

#### **macOS**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.10 postgresql@15 redis nginx

# Install additional tools
brew install --cask docker
```

#### **Windows**
```bash
# Install Chocolatey if not already installed
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install dependencies
choco install python postgresql redis nginx
```

### **2. Install PostgreSQL Extensions**

```bash
# Connect to PostgreSQL as superuser
sudo -u postgres psql

# Create pgvector extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

# Exit PostgreSQL
\q
```

## 🗄️ Database Setup

### **1. Create Database and User**

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database
CREATE DATABASE labor_observatory
  WITH ENCODING 'UTF8'
  LC_COLLATE = 'en_US.UTF-8'
  LC_CTYPE = 'en_US.UTF-8';

# Create user
CREATE USER labor_user WITH PASSWORD 'your_secure_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE labor_observatory TO labor_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO labor_user;

# Exit PostgreSQL
\q
```

### **2. Run Database Migrations**

```bash
# Navigate to project directory
cd observatorio-demanda-laboral

# Run initial schema
psql -U labor_user -d labor_observatory -f src/database/migrations/001_initial_schema.sql
```

### **3. Verify Database Connection**

```bash
# Test connection
psql -U labor_user -d labor_observatory -c "SELECT version();"

# Check extensions
psql -U labor_user -d labor_observatory -c "SELECT * FROM pg_extension;"
```

## 🐍 Python Environment

### **1. Create Virtual Environment**

```bash
# Navigate to project directory
cd observatorio-demanda-laboral

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### **2. Install Python Dependencies**

```bash
# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install additional development dependencies
pip install -r requirements-dev.txt
```

### **3. Install spaCy Spanish Model**

```bash
# Download Spanish language model
python -m spacy download es_core_news_lg

# Verify installation
python -c "import spacy; nlp = spacy.load('es_core_news_lg'); print('Spanish model loaded successfully')"
```

### **4. Download LLM Models**

```bash
# Create models directory
mkdir -p data/models

# Download Mistral 7B model (example)
cd data/models
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf

# Rename for convenience
mv mistral-7b-instruct-v0.2.Q4_K_M.gguf mistral-7b-instruct.Q4_K_M.gguf

# Return to project directory
cd ../..
```

## ⚙️ Configuration

### **1. Environment Variables**

```bash
# Copy environment template
cp .env.example .env

# Edit environment file
nano .env  # or use your preferred editor
```

#### **Required Environment Variables**

```bash
# Database
DATABASE_URL=postgresql://labor_user:your_password@localhost:5432/labor_observatory

# LLM Model
LLM_MODEL_PATH=./data/models/mistral-7b-instruct.Q4_K_M.gguf

# Scraping
SCRAPER_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Academic Research Bot v1.0"

# Output directories
OUTPUT_DIR=./outputs
LOG_DIR=./logs
```

### **2. Create Configuration Files**

```bash
# Create configuration directories
mkdir -p config
mkdir -p src/config

# Create ESCO configuration
cat > config/esco_config.yaml << 'EOF'
esco:
  version: "1.1.0"
  base_url: "https://ec.europa.eu/esco/api"
  language:
    primary: "es"
    fallback: "en"
  skill_types:
    - "skill/competence"
    - "knowledge"
EOF
```

### **3. Create Required Directories**

```bash
# Create output and cache directories
mkdir -p outputs
mkdir -p logs
mkdir -p data/cache
mkdir -p data/models
mkdir -p data/esco
```

## 🧪 Testing Installation

### **1. Test Database Connection**

```python
# Create test script
cat > test_db.py << 'EOF'
#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

# Test database connection
try:
    engine = create_engine(os.getenv('DATABASE_URL'))
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        print("✅ Database connection successful!")
        print(f"PostgreSQL version: {result.fetchone()[0]}")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
EOF

# Run test
python test_db.py
```

### **2. Test spaCy Installation**

```python
# Create test script
cat > test_spacy.py << 'EOF'
#!/usr/bin/env python3
import spacy

try:
    # Load Spanish model
    nlp = spacy.load("es_core_news_lg")
    print("✅ spaCy Spanish model loaded successfully!")
    
    # Test basic functionality
    doc = nlp("Desarrollador Python con experiencia en Django")
    print(f"✅ NLP processing successful! Found {len(doc.ents)} entities")
    
except Exception as e:
    print(f"❌ spaCy test failed: {e}")
EOF

# Run test
python test_spacy.py
```

### **3. Test LLM Model**

```python
# Create test script
cat > test_llm.py << 'EOF'
#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

model_path = os.getenv('LLM_MODEL_PATH')

if os.path.exists(model_path):
    print(f"✅ LLM model found at: {model_path}")
    print(f"File size: {os.path.getsize(model_path) / (1024**3):.2f} GB")
else:
    print(f"❌ LLM model not found at: {model_path}")
EOF

# Run test
python test_llm.py
```

## 🚀 First Run

### **1. Initialize System**

```bash
# Check system status
python src/orchestrator.py status

# Run initial setup
python src/orchestrator.py setup
```

### **2. Test Scraping**

```bash
# Test scraping with limited pages
python src/orchestrator.py scrape CO computrabajo --pages 2

# Check results
python src/orchestrator.py status
```

### **3. Test Complete Pipeline**

```bash
# Run mini pipeline
python src/orchestrator.py pipeline CO computrabajo --full --pages 3

# Check outputs
ls -la outputs/
```

## ❌ Troubleshooting

### **Common Issues and Solutions**

#### **1. Database Connection Errors**

```bash
# Check PostgreSQL service status
sudo systemctl status postgresql

# Restart PostgreSQL if needed
sudo systemctl restart postgresql

# Check connection parameters
psql -U labor_user -d labor_observatory -h localhost
```

#### **2. Python Package Issues**

```bash
# Reinstall virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### **3. spaCy Model Issues**

```bash
# Reinstall Spanish model
python -m spacy uninstall es_core_news_lg
python -m spacy download es_core_news_lg

# Verify installation
python -m spacy validate
```

#### **4. LLM Model Issues**

```bash
# Check model file integrity
ls -la data/models/

# Re-download if corrupted
rm data/models/mistral-7b-instruct.Q4_K_M.gguf
# Download again from Hugging Face
```

#### **5. Permission Issues**

```bash
# Fix directory permissions
sudo chown -R $USER:$USER observatorio-demanda-laboral/
chmod -R 755 observatorio-demanda-laboral/

# Fix PostgreSQL permissions
sudo chown -R postgres:postgres /var/lib/postgresql/
sudo chmod -R 700 /var/lib/postgresql/
```

### **Getting Help**

- **Check logs**: `tail -f logs/labor_observatory.log`
- **System status**: `python src/orchestrator.py status`
- **Database logs**: `sudo tail -f /var/log/postgresql/postgresql-*.log`
- **Create issue**: Use the GitHub issue tracker

---

## 🎉 Next Steps

After successful installation:

1. **Read the [Master Technical Specification](documentation/master-tech-spec.md)**
2. **Explore the [Complete Implementation Guide](documentation/complete-implementation-guide.md)**
3. **Review [Data Flow Reference](documentation/data-flow-reference.md)**
4. **Start with small datasets and gradually scale up**
5. **Join the community and contribute!**

---

**Happy analyzing! 🚀**
