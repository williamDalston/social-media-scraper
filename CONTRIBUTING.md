# Contributing Guide

Thank you for your interest in contributing to the HHS Social Media Scraper project!

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)

---

## 🤝 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the project
- Show empathy towards others

---

## 🚀 Getting Started

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/your-username/social-media-scraper.git
   cd social-media-scraper
   ```
3. **Set up development environment** (see below)
4. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

---

## 🔧 Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git
- Your favorite code editor

### Setup Steps

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install development dependencies (if exists)
pip install -r requirements-dev.txt

# 4. Copy environment template
cp .env.example .env

# 5. Configure environment
# Edit .env with your settings

# 6. Initialize database
python -c "from scraper.schema import init_db; init_db('social_media.db')"

# 7. Run tests
pytest

# 8. Start development server
export FLASK_ENV=development
export FLASK_DEBUG=True
python app.py
```

### Docker Development

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f app

# Run commands in container
docker-compose exec app bash
```

---

## 🔄 Development Workflow

### Branch Naming

- `feature/feature-name` - New features
- `bugfix/issue-description` - Bug fixes
- `docs/documentation-update` - Documentation
- `refactor/code-improvement` - Code refactoring
- `test/test-coverage` - Test additions

### Commit Messages

Follow conventional commits format:

```
type(scope): subject

body

footer
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions
- `chore`: Maintenance tasks

**Examples:**
```
feat(api): Add pagination to accounts endpoint

fix(scraper): Handle Instagram rate limits properly

docs(readme): Update installation instructions
```

---

## 📝 Coding Standards

### Python Style

- Follow PEP 8 style guide
- Use type hints where possible
- Maximum line length: 100 characters
- Use meaningful variable and function names

### Code Formatting

```bash
# Install formatter (if not already)
pip install black isort flake8

# Format code
black .
isort .

# Check linting
flake8 .
```

### Import Organization

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# Standard library
import os
import sys
from datetime import datetime

# Third-party
from flask import Flask, jsonify
from sqlalchemy import Column, Integer

# Local
from scraper.schema import DimAccount
from api.errors import NotFoundError
```

### Documentation

- Add docstrings to all functions and classes
- Use Google-style docstrings
- Document complex logic with comments

**Example:**
```python
def get_account(platform: str, handle: str) -> DimAccount:
    """
    Get account by platform and handle.
    
    Args:
        platform: Social media platform (X, Instagram, etc.)
        handle: Account handle/username
        
    Returns:
        DimAccount instance
        
    Raises:
        NotFoundError: If account not found
    """
    # Implementation
```

---

## 🧪 Testing Guidelines

### Writing Tests

- Write tests for all new features
- Test both success and failure cases
- Use descriptive test names
- Keep tests independent and isolated

**Example:**
```python
def test_get_account_success(db_session, sample_account):
    """Test successful account retrieval."""
    account = db_session.query(DimAccount).first()
    assert account is not None
    assert account.platform == 'X'
    assert account.handle == '@test'

def test_get_account_not_found(db_session):
    """Test account not found error."""
    with pytest.raises(NotFoundError):
        get_account('X', '@nonexistent')
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=scraper --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_scrapers.py

# Run specific test
pytest tests/unit/test_scrapers.py::TestSimulatedScraper::test_scrape

# Run with verbose output
pytest -v

# Run only failed tests
pytest --lf
```

### Test Coverage

- Maintain 80%+ code coverage
- Focus on critical paths
- Test edge cases and error conditions

---

## 📚 Documentation

### Code Documentation

- Add docstrings to all public functions/classes
- Document complex algorithms
- Include usage examples in docstrings

### API Documentation

- Document all API endpoints
- Include request/response examples
- Document authentication requirements
- Update OpenAPI/Swagger documentation

### User Documentation

- Update relevant user-facing docs
- Add examples where helpful
- Keep documentation up to date

---

## 🎯 Submitting Changes

### Pull Request Process

1. **Update your fork**
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Create feature branch**
   ```bash
   git checkout -b feature/your-feature
   ```

3. **Make changes**
   - Write code
   - Add tests
   - Update documentation

4. **Run tests**
   ```bash
   pytest
   black .
   isort .
   flake8 .
   ```

5. **Commit changes**
   ```bash
   git add .
   git commit -m "feat(scope): description"
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature
   ```

7. **Create Pull Request**
   - Provide clear description
   - Link related issues
   - Include screenshots if UI changes
   - Ensure CI tests pass

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Testing
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No breaking changes (or documented)
```

---

## 🎨 Code Review Guidelines

### For Authors

- Keep PRs focused and small
- Respond to feedback promptly
- Make requested changes
- Ask questions if unclear

### For Reviewers

- Be constructive and respectful
- Provide specific feedback
- Suggest improvements
- Approve when satisfied

---

## 🐛 Reporting Bugs

### Bug Report Template

```markdown
**Describe the bug**
Clear description of the issue

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen

**Actual behavior**
What actually happened

**Environment:**
- OS: [e.g., macOS 12.0]
- Python: [e.g., 3.11.0]
- Version: [e.g., 1.0.0]

**Logs**
Relevant log output

**Additional context**
Any other relevant information
```

---

## 💡 Feature Requests

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
Clear description of the problem

**Describe the solution you'd like**
Clear description of desired solution

**Describe alternatives considered**
Alternative solutions considered

**Additional context**
Any other relevant information
```

---

## 📋 Checklist for Contributors

Before submitting:

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] No linting errors
- [ ] Commit messages follow conventions
- [ ] Branch is up to date with main
- [ ] PR description is clear and complete

---

## 🔗 Resources

- **[Python Style Guide (PEP 8)](https://www.python.org/dev/peps/pep-0008/)**
- **[Conventional Commits](https://www.conventionalcommits.org/)**
- **[pytest Documentation](https://docs.pytest.org/)**
- **[Flask Documentation](https://flask.palletsprojects.com/)**

---

## ❓ Questions?

- Check existing documentation
- Search existing issues
- Ask in discussions (if available)
- Create an issue with question tag

---

**Thank you for contributing! 🎉**

