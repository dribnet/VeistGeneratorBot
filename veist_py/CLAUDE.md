# CLAUDE.md - VeistGeneratorBot Project Guidelines

## Project Vision

VeistGeneratorBot is a prototype for a new kind of collective intelligence system that learns to predict and fulfill group desires through minimal feedback. Currently manifested as an AI art generator, it interprets Discord reactions as a sparse communication language to understand what a community wants.

### Core Concept
- The bot generates images and learns from emoji reactions
- It tries to predict the collective will of the group
- Goal: Maximize "AllDone" reactions (group consensus achieved)
- Each community develops its own "reaction language" that the bot must learn

### Meta Reactions
- **VeistAllDone**: Mission accomplished, good stopping point
- **VeistKeepGoing**: Right direction, continue evolving
- **VeistGoBack**: Wrong direction, try something different

All other reactions are open to interpretation - the bot must learn their meaning through trial and error.

### Future Vision
- Adaptable to different group cultures and preferences
- Shadow users: Predict absent users' reactions
- NPC testing environments for systematic improvement
- NFT publishing for notable consensus achievements
- Multi-backend support for different generation models

## Project Commands
- Install dependencies: `pip install -r requirements.txt` (or `requirements_flux.txt` for GPU acceleration)
- Run tests: `python -m pytest`
- Run single test: `python -m pytest tests/test_generator.py::TestVeistGenerator::test_stop`
- Run the bot: `python bot.py`
- Run with custom config: `python bot.py config.yaml`
- Interactive generator CLI: `python generator.py`

## Architecture Overview

### Core Components
- **bot.py**: Discord bot implementation, reaction handling, generation loop
- **generator.py**: Image generation interface (supports multiple backends)
- **reaction_merging.py**: Interprets reactions to evolve prompts
- **merging/**: Different strategies for interpreting reactions
  - append_merger.py: Simple reaction-to-text mapping
  - deepseek_merger.py: LLM-based interpretation
  - reaction_merger.py: Base interface

### Configuration
- **default_config.yaml**: Base configuration with all options
- **config.yaml**: User overrides (auto-created from default)
- **debug.yaml**, **debug_flux.yaml**: Development configs

## Code Style

### Type Hints
Always use type hints for function parameters and return values:
```python
from typing import Dict, List, Optional, Tuple

def process_reactions(reactions: Dict[str, int], meta_stats: Dict[str, int]) -> Optional[str]:
    pass
```

### Imports
1. Standard library (os, datetime, pathlib, asyncio)
2. Type hints (typing imports)
3. Third-party libraries (PIL, discord, huggingface_hub)
4. Project imports

### Naming & Types
- Classes: PascalCase (VeistGenerator, ReactionMerger)
- Functions/variables: snake_case (generate_image, collect_reactions)
- Constants: UPPERCASE (TOKEN, MAX_RETRIES)
- Private methods: _leading_underscore

### Error Handling
- Use try/except with specific exceptions
- Return dictionaries with error information rather than raising exceptions
- Always include error messages and context in returns
- Log errors appropriately for debugging

### Async Best Practices
- Use `async`/`await` consistently
- Prefer `asyncio.create_task()` for fire-and-forget operations
- Handle discord.py exceptions (NotFound, Forbidden, HTTPException)

### Structure
- Config values in YAML files (default_config.yaml)
- Classes with clear method organization
- Docstrings for public methods and modules
- Keep Discord bot logic separate from generation logic