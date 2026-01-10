# Contributing to Spatelier

Thank you for your interest in contributing to Spatelier! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/galenspikes/spatelier/issues)
2. If not, create a new issue with:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)

### Suggesting Features

1. Check existing [Issues](https://github.com/galenspikes/spatelier/issues) for similar suggestions
2. Create a new issue describing:
   - The feature and its use case
   - Why it would be valuable
   - Potential implementation approach (if you have ideas)

### Submitting Changes

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set up development environment**
   ```bash
   source venv/bin/activate
   pip install -e ".[dev]"
   pre-commit install
   ```

4. **Make your changes**
   - Follow the code style (black, isort)
   - Add tests for new functionality
   - Update documentation as needed

5. **Run tests and checks**
   ```bash
   make test
   make lint
   make format-check
   ```

6. **Commit your changes**
   ```bash
   git commit -m "Add: description of your changes"
   ```

7. **Push and create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Development Guidelines

### Code Style

- Follow PEP 8
- Use `black` for formatting (line length 88)
- Use `isort` for import sorting
- Type hints are required for all functions

### Testing

- Write tests for all new features
- Maintain or improve test coverage
- Run `make test` before submitting

### Documentation

- Update README.md for user-facing changes
- Add docstrings to all public functions/classes
- Update CHANGELOG.md for significant changes

## Project Structure

```
spatelier/
├── cli/          # CLI commands
├── core/         # Core functionality
├── modules/      # Feature modules
├── database/     # Database models
├── tests/        # Test suite
└── docs/         # Documentation
```

## Questions?

Feel free to open an issue for any questions about contributing!
