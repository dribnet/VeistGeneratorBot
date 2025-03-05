# CLAUDE.md - Project Guidelines

## Project Commands
- Install dependencies: `pip install -r requirements.txt` (or `requirements_flux.txt` for GPU acceleration)
- Run tests: `python -m pytest`
- Run single test: `python -m pytest tests/test_generator.py::TestVeistGenerator::test_stop`
- Run the bot: `python bot.py`
- Interactive generator CLI: `python generator.py`

## Code Style

### Imports
1. Standard library (os, datetime, pathlib)
2. Third-party libraries (PIL, discord, huggingface_hub)
3. Project imports

### Naming & Types
- Classes: PascalCase (VeistGenerator)
- Functions/variables: snake_case (generate_image)
- Constants: UPPERCASE (TOKEN)
- Use type hints (Dict, List) and return type annotations

### Error Handling
- Use try/except with specific exceptions
- Return dictionaries with error information rather than raising exceptions
- Always include error messages and context in returns

### Structure
- Config values in YAML files (default_config.yaml)
- Classes with clear method organization
- Docstrings for methods and modules