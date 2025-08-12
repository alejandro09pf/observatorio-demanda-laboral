# 🚀 **QUICK START - Labor Market Observatory**

> **Get up and running in 5 minutes**

## ⚡ **IMMEDIATE ACTIONS**

### **1. Read These Files (in order)**
- **[ONBOARDING GUIDE](docs/ONBOARDING_GUIDE.md)** ← **START HERE**
- **[DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)** ← Development roadmap
- **[README.md](README.md)** ← Project overview

### **2. Current Status**
- ✅ **Phases 1 & 2 Complete** - Foundation & Database working
- 🚧 **Phase 3 Next** - Web Scraping implementation
- 🗄️ **Database Ready** - PostgreSQL running, all models working

### **3. Quick Commands**
```bash
# Check system status
python src/orchestrator.py status

# Verify database
python -c "from src.database.operations import DatabaseOperations; db = DatabaseOperations(); print('✅ Database working!')"

# Run tests
python -m pytest tests/ -v
```

## 🎯 **WHAT TO DO NEXT**

**Focus on Phase 3: Web Scraping**
- Implement real scraping logic in `src/scraper/spiders/`
- Test with `python src/orchestrator.py scrape CO computrabajo --pages 1`
- Verify data flows to database

## 📚 **ESSENTIAL DOCUMENTATION**

- **🏗️ Architecture**: `docs/architecture.md`
- **🔧 Technical Spec**: `docs/technical-specification.md`
- **📊 Data Flow**: `docs/data-flow-reference.md`
- **🚀 Implementation**: `docs/implementation-guide.md`

---

**Need more details? Read the [ONBOARDING GUIDE](docs/ONBOARDING_GUIDE.md)!** 🚀 