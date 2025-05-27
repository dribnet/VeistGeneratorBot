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

## NFT Publishing Integration

### akaSwap API Details
- **Base URL**: https://testnets.akaswap.com/api/v2
- **Documentation**: https://hackmd.io/@red30603/SJmiQLE5ke
- **Blockchain**: Tezos Ghostnet (testnet)
- **View NFTs**: https://testnets.akaswap.com/proxymint/{token_id}
- **View Wallet**: https://testnets.akaswap.com/tz/{wallet_address}

### API Endpoints
1. **IPFS Upload**: POST `/ipfs/tokens`
   - Uploads three image versions (artifact, display, thumbnail)
   - Returns IPFS URIs for all versions
   
2. **NFT Minting**: POST `/fa2tokens/{contract}`
   - Creates and mints NFT tokens
   - Requires proper authentication and contract permissions

### Current Implementation Status
- ✅ IPFS upload working perfectly
- ✅ Image resizing for three quality levels (2048x2048, 1024x1024, 256x256)
- ✅ Correct mint request format validated
- ✅ NFT minting working on Ghostnet testnet!
- ✅ Contract address: `KT1DeWkBGLKiXoYqxnMT4w3c8chApAqkFhqJ` (confirmed working)

### NFT Publishing Utility
Located at `apps/publish.py`, provides:
- Command-line interface for publishing images as NFTs
- Automatic image resizing and IPFS upload
- Full minting flow with metadata

### Usage
```bash
# Set credentials
export AKASWAP_PARTNER_ID="your-partner-id"
export AKASWAP_PARTNER_SECRET="your-secret"

# Publish an image
python apps/publish.py image.jpg \
  --name "Veist Consensus #1" \
  --description "Community-approved artwork" \
  --receiver "tz1YourWalletAddress"
```

### Testing
```bash
# Test IPFS upload only
python apps/test_publish.py --skip-mint

# Test full flow (requires valid credentials)
python apps/test_publish.py
```

### Integration Notes for Meeting
1. ✅ **Contract address confirmed** - KT1DeWkBGLKiXoYqxnMT4w3c8chApAqkFhqJ works!
2. ✅ **Test credentials working** - Can mint NFTs on Ghostnet
3. **Production setup** - Discuss mainnet contract and credentials
4. **Wallet address** - Confirm production Tezos wallet for receiving NFTs
5. **Token ID strategy** - Currently using timestamp % Int32.MaxValue

### Bot Integration Plan
When ready, the bot will:
1. Detect special "publish" reaction (e.g., 🎨 or custom emoji)
2. Check if image achieved consensus (AllDone reactions)
3. Automatically publish to NFT with metadata:
   - Name: "Veist Consensus #{number}"
   - Description: Include prompt and reaction data
   - Attributes: Generator version, consensus score, timestamp

## Next Steps - Image Generation Backend

### GPT-Image-1 Integration (In Progress)
- **Model**: gpt-image-1 (OpenAI's latest multimodal image model, released April 2025)
- **Key Feature**: Can understand input images AND generate new ones based on feedback
- **Pricing**: $0.02 (low), $0.07 (medium), $0.19 (high) per image
- **Advantage**: Single API call for both understanding and generation

### Why This Is Better
- Old approach: Blind prompt manipulation ("A neon city but more 🌈")
- New approach: AI actually sees the image and understands visual feedback
- Can interpret emoji reactions as visual instructions (🔥 = more intensity, 💙 = blue tones, etc.)

### Implementation Plan
1. Start with simple API test utility (like we did for NFT publishing)
2. Test image-to-image evolution with emoji feedback
3. Once working, integrate into new bot architecture
4. Build incrementally rather than big refactor

### API Details
- Endpoint: https://api.openai.com/v1/images/generations
- Model: "gpt-image-1"
- Supports: image input + prompt, quality levels, moderation settings
- Returns: Generated image URL

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