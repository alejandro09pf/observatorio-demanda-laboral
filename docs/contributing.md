# 🤝 Contributing Guide - Labor Market Observatory

> **How to contribute to the Labor Market Observatory project**

## 📋 Table of Contents

- [🌟 Welcome Contributors](#-welcome-contributors)
- [🎯 Project Goals](#-project-goals)
- [🔧 Development Setup](#-development-setup)
- [📝 Code Style](#-code-style)
- [🧪 Testing](#-testing)
- [📚 Documentation](#-documentation)
- [🚀 Pull Request Process](#-pull-request-process)
- [🐛 Bug Reports](#-bug-reports)
- [💡 Feature Requests](#-feature-requests)
- [📞 Communication](#-communication)
- [🏆 Recognition](#-recognition)

## 🌟 Welcome Contributors

Thank you for your interest in contributing to the **Labor Market Observatory**! This project aims to provide automated insights into labor market trends across Latin America, and we welcome contributions from developers, researchers, and data scientists.

### **Why Contribute?**

- **Impact**: Help bridge information gaps in Latin American labor markets
- **Learning**: Work with cutting-edge AI/ML technologies (LLMs, embeddings, clustering)
- **Community**: Join a community of developers and researchers
- **Recognition**: Get credited for your contributions

### **Who Can Contribute?**

- **Developers**: Python, SQL, web scraping, ML/AI
- **Researchers**: Labor economics, skill analysis, market trends
- **Data Scientists**: Data processing, visualization, analysis
- **Designers**: UI/UX, report layouts, visualizations
- **Documentation**: Technical writing, tutorials, guides

## 🎯 Project Goals

### **Current Priorities**

1. **Core Implementation**: Complete the basic pipeline functionality
2. **Testing**: Build comprehensive test coverage
3. **Documentation**: Improve user and developer guides
4. **Performance**: Optimize processing speed and memory usage
5. **Extensibility**: Make the system easy to extend

### **Long-term Vision**

- **Multi-language Support**: Expand beyond Spanish
- **Real-time Processing**: Stream processing capabilities
- **API Service**: RESTful API for external integrations
- **Advanced Analytics**: Predictive modeling and trend analysis
- **Mobile App**: Native mobile applications

## 🔧 Development Setup

### **Prerequisites**

- Python 3.10+
- PostgreSQL 15+ with pgvector extension
- Git
- Docker (optional)

### **Local Development Setup**

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/observatorio-demanda-laboral.git
   cd observatorio-demanda-laboral
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Set up database**:
   ```bash
   # Create database and run migrations
   psql -h localhost -U your_user -c "CREATE DATABASE labor_observatory;"
   psql -h localhost -U your_user -d labor_observatory -f src/database/migrations/001_initial_schema.sql
   ```

6. **Verify setup**:
   ```bash
   python -m pytest tests/ -v
   ```

### **Docker Development Setup**

1. **Start services**:
   ```bash
   docker-compose up -d postgres redis
   ```

2. **Run migrations**:
   ```bash
   docker-compose exec postgres psql -U labor_user -d labor_observatory -f /docker-entrypoint-initdb.d/001_initial_schema.sql
   ```

3. **Run tests**:
   ```bash
   docker-compose run --rm app python -m pytest tests/ -v
   ```

## 📝 Code Style

### **Python Style Guide**

We follow **PEP 8** and use **Black** for code formatting.

1. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

2. **Format code**:
   ```bash
   black src/ tests/
   isort src/ tests/
   ```

3. **Check code quality**:
   ```bash
   flake8 src/ tests/
   mypy src/
   ```

### **Code Standards**

- **Type Hints**: Use type hints for all function parameters and return values
- **Docstrings**: Follow Google docstring format
- **Error Handling**: Use specific exceptions and provide meaningful error messages
- **Logging**: Use structured logging with appropriate levels
- **Testing**: Aim for 80%+ test coverage

### **Example Code Structure**

```python
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ExampleClass:
    """Example class demonstrating code standards."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize the example class.
        
        Args:
            config: Configuration dictionary
            
        Raises:
            ValueError: If config is empty
        """
        if not config:
            raise ValueError("Config cannot be empty")
        
        self.config = config
        logger.info("ExampleClass initialized with config: %s", config)
    
    def process_data(self, data: List[str]) -> List[Dict[str, Any]]:
        """Process a list of data items.
        
        Args:
            data: List of data strings to process
            
        Returns:
            List of processed data dictionaries
            
        Raises:
            ValueError: If data contains empty strings
        """
        if not data:
            logger.warning("No data provided for processing")
            return []
        
        # Validate input
        if any(not item.strip() for item in data):
            raise ValueError("Data items cannot be empty")
        
        # Process data
        result = []
        for item in data:
            processed = self._process_item(item)
            result.append(processed)
        
        logger.info("Processed %d items", len(result))
        return result
    
    def _process_item(self, item: str) -> Dict[str, Any]:
        """Process a single data item.
        
        Args:
            item: Data string to process
            
        Returns:
            Processed data dictionary
        """
        return {
            'original': item,
            'processed': item.strip().lower(),
            'length': len(item)
        }
```

### **File Naming Conventions**

- **Python files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_private_method`

### **Import Organization**

```python
# Standard library imports
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Third-party imports
import numpy as np
import pandas as pd
from sqlalchemy import create_engine

# Local imports
from config.settings import get_settings
from database.operations import DatabaseOperations
from utils.validators import validate_input
```

## 🧪 Testing

### **Test Structure**

```
tests/
├── conftest.py              # Test configuration and fixtures
├── test_database.py         # Database operation tests
├── test_scraper.py          # Scraping module tests
├── test_extractor.py        # Skill extraction tests
├── test_llm_processor.py    # LLM processing tests
├── test_embedder.py         # Embedding generation tests
├── test_analyzer.py         # Analysis and clustering tests
├── test_orchestrator.py     # Main pipeline tests
└── fixtures/                # Test data and fixtures
    ├── __init__.py
    ├── sample_jobs.json
    └── sample_skills.json
```

### **Writing Tests**

1. **Test naming**: `test_function_name_scenario`
2. **Use fixtures**: Leverage pytest fixtures for common setup
3. **Mock external dependencies**: Use `unittest.mock` for external services
4. **Test edge cases**: Include boundary conditions and error scenarios

### **Example Test**

```python
import pytest
from unittest.mock import Mock, patch
from database.operations import DatabaseOperations

class TestDatabaseOperations:
    """Test database operations."""
    
    @pytest.fixture
    def db_ops(self, test_database_url):
        """Create database operations instance."""
        return DatabaseOperations(test_database_url)
    
    @pytest.fixture
    def sample_job_data(self):
        """Sample job data for testing."""
        return {
            "portal": "computrabajo",
            "country": "CO",
            "url": "https://example.com/job/1",
            "title": "Software Developer",
            "description": "Python developer needed"
        }
    
    def test_insert_job_success(self, db_ops, sample_job_data):
        """Test successful job insertion."""
        # Act
        job_id = db_ops.insert_job(sample_job_data)
        
        # Assert
        assert job_id is not None
        assert isinstance(job_id, str)
        
        # Verify job was actually inserted
        jobs = db_ops.get_unprocessed_jobs(limit=1)
        assert len(jobs) == 1
        assert jobs[0].title == sample_job_data["title"]
    
    def test_insert_job_duplicate(self, db_ops, sample_job_data):
        """Test duplicate job handling."""
        # Arrange
        db_ops.insert_job(sample_job_data)
        
        # Act
        job_id = db_ops.insert_job(sample_job_data)
        
        # Assert
        assert job_id is None  # Should return None for duplicates
    
    @patch('database.operations.create_engine')
    def test_database_connection_error(self, mock_create_engine, test_database_url):
        """Test database connection error handling."""
        # Arrange
        mock_create_engine.side_effect = Exception("Connection failed")
        
        # Act & Assert
        with pytest.raises(Exception, match="Connection failed"):
            DatabaseOperations(test_database_url)
```

### **Running Tests**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_database.py

# Run specific test function
pytest tests/test_database.py::TestDatabaseOperations::test_insert_job_success

# Run with verbose output
pytest -v

# Run with print statements
pytest -s
```

### **Test Coverage Requirements**

- **Minimum coverage**: 80%
- **Critical modules**: 90%+ (database, core logic)
- **New features**: Must include tests
- **Bug fixes**: Must include regression tests

## 📚 Documentation

### **Documentation Standards**

- **README.md**: Project overview and quick start
- **API Reference**: Complete function and class documentation
- **Architecture**: System design and data flow
- **Setup Guide**: Installation and configuration
- **Troubleshooting**: Common issues and solutions

### **Writing Documentation**

1. **Use clear language**: Write for developers of varying skill levels
2. **Include examples**: Provide practical code examples
3. **Keep updated**: Update docs when code changes
4. **Use consistent formatting**: Follow markdown standards

### **Documentation Structure**

```markdown
# Module Name

Brief description of what this module does.

## Functions

### function_name(param1, param2)

Description of what the function does.

**Args:**
- `param1`: Description of first parameter
- `param2`: Description of second parameter

**Returns:**
Description of return value

**Raises:**
- `ValueError`: When invalid input is provided

**Example:**
```python
result = function_name("example", 42)
print(result)  # Output: example_result
```

## Classes

### ClassName

Description of the class and its purpose.

**Methods:**
- `method1()`: Description of method
- `method2(param)`: Description of method with parameter

**Example:**
```python
instance = ClassName()
result = instance.method1()
```
```

## 🚀 Pull Request Process

### **Before Submitting**

1. **Ensure tests pass**: Run the full test suite
2. **Check code quality**: Run linting and type checking
3. **Update documentation**: Add/update relevant documentation
4. **Test functionality**: Verify your changes work as expected

### **Pull Request Template**

```markdown
## Description

Brief description of what this PR accomplishes.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing

- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Checklist

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
- [ ] No breaking changes (unless documented)

## Related Issues

Closes #(issue number)
```

### **Review Process**

1. **Automated checks**: CI/CD pipeline runs tests and quality checks
2. **Code review**: At least one maintainer must approve
3. **Testing**: Changes are tested in staging environment
4. **Merge**: PR is merged after approval and testing

### **Commit Message Format**

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

**Examples:**
```
feat(database): add bulk insert operation

fix(scraper): resolve rate limiting issues

docs(api): update function documentation

test(extractor): add test coverage for edge cases
```

## 🐛 Bug Reports

### **Bug Report Template**

```markdown
## Bug Description

Clear description of what the bug is.

## Steps to Reproduce

1. Step 1
2. Step 2
3. Step 3

## Expected Behavior

What you expected to happen.

## Actual Behavior

What actually happened.

## Environment

- OS: [e.g., Ubuntu 20.04, macOS 12.0]
- Python Version: [e.g., 3.10.0]
- Package Versions: [e.g., requirements.txt contents]
- Database: [e.g., PostgreSQL 15.0]

## Additional Information

- Error messages
- Logs
- Screenshots
- Related issues
```

### **Before Reporting**

1. **Check existing issues**: Search for similar problems
2. **Verify setup**: Ensure your environment is correctly configured
3. **Test minimal case**: Try to isolate the problem
4. **Check documentation**: Verify you're using the system correctly

## 💡 Feature Requests

### **Feature Request Template**

```markdown
## Feature Description

Clear description of the feature you'd like to see.

## Problem Statement

What problem does this feature solve?

## Proposed Solution

How would you like this feature to work?

## Alternatives Considered

What other approaches have you considered?

## Additional Context

Any other information that might be helpful.
```

### **Feature Request Guidelines**

1. **Be specific**: Describe exactly what you want
2. **Explain why**: Help us understand the value
3. **Consider impact**: Think about how it affects the system
4. **Be patient**: Feature development takes time

## 📞 Communication

### **Communication Channels**

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and discussions
- **Pull Requests**: Code reviews and collaboration
- **Email**: Direct contact for sensitive matters

### **Communication Guidelines**

1. **Be respectful**: Treat all contributors with respect
2. **Be constructive**: Provide helpful feedback
3. **Be patient**: Development takes time
4. **Ask questions**: Don't hesitate to ask for clarification

### **Getting Help**

1. **Check documentation**: Start with the existing guides
2. **Search issues**: Look for similar problems
3. **Ask questions**: Use GitHub Discussions
4. **Join community**: Connect with other contributors

## 🏆 Recognition

### **Contributor Recognition**

- **Contributors list**: All contributors are listed in README.md
- **Commit history**: Your contributions are preserved in git
- **Release notes**: Significant contributions are mentioned in releases
- **Documentation**: Contributors are credited in relevant sections

### **Types of Contributions**

- **Code**: Bug fixes, new features, improvements
- **Documentation**: Guides, tutorials, API docs
- **Testing**: Test cases, bug reports, quality improvements
- **Design**: UI/UX improvements, visualizations
- **Research**: Data analysis, methodology improvements

### **Contributor Levels**

- **Contributor**: Any contribution to the project
- **Maintainer**: Regular contributions and code review
- **Core Developer**: Significant contributions and project direction

---

**Thank you for contributing to the Labor Market Observatory! Your contributions help make labor market information more accessible across Latin America.** 🚀 