import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from generator import VeistGenerator
import asyncio
import random
import argparse
import yaml
from pathlib import Path
from reaction_merging import create_merger

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = discord.Object(id=os.getenv('GUILD_ID', '0'))

def load_config(config_path=None):
    # Load default configuration
    default_config_path = Path(__file__).parent / "default_config.yaml"
    with open(default_config_path, 'r') as f:
        default_config = yaml.safe_load(f)

    # Determine user config path
    if config_path:
        user_config_path = Path(config_path)
    else:
        user_config_path = Path(__file__).parent / "config.yaml"
            
    # If user config doesn't exist, create it from default
    if not user_config_path.exists():
        print(f"Config file not found at {user_config_path}, creating from default config...")
        with open(user_config_path, 'w') as f:
            yaml.safe_dump(default_config, f)
        return default_config
    
    # Load user config and merge with defaults
    print(f"Loading config from {user_config_path}")
    with open(user_config_path, 'r') as f:
        user_config = yaml.safe_load(f)

    # Recursively merge user config with defaults
    def merge_configs(default, user):
        merged = default.copy()
        for key, value in user.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = merge_configs(merged[key], value)
            else:
                merged[key] = value
        return merged

    # Merge user config with defaults
    final_config = merge_configs(default_config, user_config)
    
    # Optionally save the merged config if it's different from the user's config
    if final_config != user_config:
        print("Updating config file with new default values...")
        with open(user_config_path, 'w') as f:
            yaml.safe_dump(final_config, f)

    return final_config

# Load configuration with optional path
CONFIG = load_config()

# Update constants from config
MAX_RETRIES = CONFIG['retry']['max_attempts']
RETRY_DELAY = CONFIG['retry']['delay_seconds']

STARTER_PROMPTS = [
    "a mysterious robot in a garden",
    "an abstract digital landscape",
    "a futuristic city at night",
    "a geometric pattern with bright colors",
    "a cyberpunk scene with neon lights"
]

# Define meta reactions
META_REACTIONS = ["❤️"]  # Just the red heart

class VeistBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        
        super().__init__(command_prefix='!', intents=intents)
        self.generator = VeistGenerator(
            backend=CONFIG['generation']['backend'],
            debug=CONFIG['display']['debug_output']
        )
        self.reaction_merger = create_merger(CONFIG['generation']['reaction_merging'])
        self.generation_channel = None
        self.is_generating = False
        self.current_thread = None
        self.variation_count = 0
        self.MAX_VARIATIONS = CONFIG['generation']['max_variations']
        self.last_thread_message = None
        self.last_prompt = None
        self.current_version_message = None

    async def setup_hook(self):
        print("Syncing commands to guild...")
        self.tree.copy_global_to(guild=GUILD_ID)
        synced = await self.tree.sync(guild=GUILD_ID)
        print(f"Synced {len(synced)} command(s)")
        
        # Set the loop interval from config
        self.generate_loop.change_interval(
            seconds=CONFIG['generation']['seconds_per_variation']
        )
        # Start the generation loop
        self.generate_loop.start()

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        
        # Set up the generation channel using config
        channel_id = CONFIG['discord']['channel_id']
        if channel_id:
            self.generation_channel = self.get_channel(int(channel_id))
        else:
            # Find channel by name
            channel_name = CONFIG['discord']['channel_name']
            for channel in self.get_all_channels():
                if channel.name == channel_name:
                    self.generation_channel = channel
                    break
        
        if not self.generation_channel:
            channel_id_or_name = channel_id or CONFIG['discord']['channel_name']
            print(f"Warning: Could not find channel {channel_id_or_name}")
            return
            
        # Start the generator
        self.generator.start_prompter()
        
        # Generate first image with random prompt
        initial_prompt = random.choice(STARTER_PROMPTS)
        await self.generate_and_send(initial_prompt, is_initial=True)

    async def collect_reactions(self):
        """Collect reactions from the last thread message"""
        if not self.last_thread_message:
            return {}, {}
            
        # Fetch the message again to get updated reactions
        message = await self.current_thread.fetch_message(self.last_thread_message.id)
        
        # Collect regular and meta reactions separately
        regular_reactions = {}
        meta_stats = {
            "❤️": 0  # hearts
        }
        
        for reaction in message.reactions:
            emoji = str(reaction.emoji)
            count = reaction.count
            
            if emoji in META_REACTIONS:
                # Subtract 1 from meta reactions to account for bot's own reaction
                meta_stats[emoji] = max(0, count - 1)
            else:
                regular_reactions[emoji] = count
                
        # if CONFIG['display']['debug_output']:
            # print(f"Reaction check:")
            # print(f"Heart count: {meta_stats['❤️']}")
            # print(f"Regular reactions: {regular_reactions}")
            
        return regular_reactions, meta_stats

    def build_next_prompt(self, reactions):
        """Build next prompt based on previous prompt and reactions"""
        if not reactions:
            return random.choice(STARTER_PROMPTS)
        
        return self.reaction_merger.merge(self.last_prompt, reactions)

    async def start_new_generation(self):
        """Start a fresh generation cycle"""
        self.current_thread = None
        self.variation_count = 0
        self.last_prompt = None
        await self.generate_and_send()

    async def generate_with_retry(self, prompt):
        """Attempt to generate image with retries"""
        for attempt in range(MAX_RETRIES):
            try:
                result = await self.loop.run_in_executor(
                    None, 
                    self.generator.generate_image,
                    prompt
                )
                
                if "error" in result and "too busy" in result["error"].lower():
                    if attempt < MAX_RETRIES - 1:  # Don't message if it's the last attempt
                        await self.generation_channel.send(f"⏳ Server busy, retrying in {RETRY_DELAY} seconds... (Attempt {attempt + 1}/{MAX_RETRIES})")
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                return result
                
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    await self.generation_channel.send(f"⚠️ Generation error, retrying in {RETRY_DELAY} seconds... (Attempt {attempt + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    return {"error": str(e)}
        
        return {"error": "Maximum retry attempts reached"}

    async def update_thread_message_status(self, status: str):
        """Update the status in the last thread message"""
        if self.last_thread_message:
            try:
                current_content = self.last_thread_message.content
                base_content = current_content.split('\n')[0]  # Keep the first line (variation info)
                await self.last_thread_message.edit(content=f"{base_content}\nPrompt: {self.last_prompt}\n\n{status}")
            except discord.NotFound:
                pass

    async def generate_and_send(self, prompt=None, is_initial=False):
        """Helper method to generate and send images"""
        if self.is_generating:
            return
            
        self.is_generating = True
        try:
            if not self.current_thread:
                prompt = random.choice(STARTER_PROMPTS)
            elif not is_initial:
                regular_reactions, meta_stats = await self.collect_reactions()
                
                # Calculate total regular reactions
                total_regular = sum(regular_reactions.values())
                heart_count = meta_stats['❤️']
                
                # Early completion check - hearts outnumber other reactions
                if heart_count > total_regular:
                    if CONFIG['display']['debug_output']:
                        print(f"Early completion: {heart_count} hearts > {total_regular} regular reactions")
                    try:
                        if self.last_thread_message and self.last_thread_message.attachments:
                            attachment = self.last_thread_message.attachments[0]
                            temp_filename = f"temp_{attachment.filename}"
                            await attachment.save(temp_filename)
                            
                            final_file = discord.File(temp_filename)
                            await self.current_version_message.delete()
                            await self.generation_channel.send(
                                f"✨ Final Result (chosen with ❤️)\nPrompt: {self.last_prompt}", 
                                file=final_file
                            )
                            os.remove(temp_filename)
                            
                            await self.current_thread.send("❤️ Final result posted in main channel.")
                            await self.current_thread.edit(archived=True, locked=True)
                            
                            self.loop.create_task(self.start_new_generation())
                            return
                    except Exception as e:
                        await self.current_thread.send(f"Error processing early completion: {str(e)}")
                        return
                
                # Check if we have any non-meta reactions
                if not any(count > 0 for count in regular_reactions.values()):
                    await self.update_thread_message_status("⏳ Waiting for reactions...")
                    return
                
                # Only proceed if we have actual reactions
                prompt = self.build_next_prompt(regular_reactions)
            
            # Generate image
            result = await self.generate_with_retry(prompt)
            
            if "error" in result:
                await self.generation_channel.send(f"Error generating image: {result['error']}")
                return

            if not self.current_thread:
                # Initial post and thread creation
                main_message_content = "🎨 Starting new generation thread"
                if CONFIG['display']['prompt_visibility'] == "Full":
                    main_message_content += f"\nPrompt: {result['prompt']}"
                    
                main_message = await self.generation_channel.send(main_message_content)
                
                self.current_thread = await main_message.create_thread(
                    name="Variations",
                    auto_archive_duration=60
                )
                self.variation_count = 0
                
                # Post initial image with status below
                message_content = f"Initial variation (1/{self.MAX_VARIATIONS})"
                if CONFIG['display']['prompt_visibility'] == "Full":
                    message_content += f"\nPrompt: {result['prompt']}"
                message_content += "\n\n🔄 Collecting feedback..."
                
                thread_file = discord.File(result["path"])
                self.last_thread_message = await self.current_thread.send(
                    message_content, 
                    file=thread_file
                )
                
                # Post current version
                current_version_content = f"💫 Current Version (1/{self.MAX_VARIATIONS})"
                if CONFIG['display']['prompt_visibility'] == "Full":
                    current_version_content += f"\nPrompt: {result['prompt']}"
                
                current_file = discord.File(result["path"])
                self.current_version_message = await self.generation_channel.send(
                    current_version_content,
                    file=current_file
                )
            else:
                # Clear status from previous message
                if self.last_thread_message:
                    try:
                        current_content = self.last_thread_message.content
                        base_content = current_content.split('\n')[0]  # Keep the first line (variation info)
                        if CONFIG['display']['prompt_visibility'] == "Full":
                            prompt_line = current_content.split('\n')[1]  # Keep the prompt line
                            await self.last_thread_message.edit(content=f"{base_content}\n{prompt_line}")
                        else:
                            await self.last_thread_message.edit(content=base_content)
                    except (discord.NotFound, IndexError):
                        pass
                
                # Post variation with status below
                message_content = f"Variation {self.variation_count + 1}/{self.MAX_VARIATIONS}"
                if CONFIG['display']['prompt_visibility'] == "Full":
                    message_content += f"\nPrompt: {result['prompt']}"
                message_content += "\n\n🔄 Collecting feedback..."
                
                thread_file = discord.File(result["path"])
                self.last_thread_message = await self.current_thread.send(
                    message_content,
                    file=thread_file
                )
                
                # Update current version
                if self.variation_count < self.MAX_VARIATIONS - 1:
                    await self.current_version_message.delete()
                    current_version_content = f"💫 Current Version ({self.variation_count + 1}/{self.MAX_VARIATIONS})"
                    if CONFIG['display']['prompt_visibility'] == "Full":
                        current_version_content += f"\nPrompt: {result['prompt']}"
                    
                    current_file = discord.File(result["path"])
                    self.current_version_message = await self.generation_channel.send(
                        current_version_content,
                        file=current_file
                    )

            # Add reactions
            for reaction in META_REACTIONS:
                await self.last_thread_message.add_reaction(reaction)

            self.last_prompt = result['prompt']
            self.variation_count += 1
            
            # Check if we're done
            if self.variation_count >= self.MAX_VARIATIONS:
                await self.current_version_message.delete()
                final_file = discord.File(result["path"])
                await self.generation_channel.send(
                    f"✨ Final Result\nPrompt: {result['prompt']}", 
                    file=final_file
                )
                
                await self.current_thread.send("🏁 Final result posted in main channel.")
                await self.current_thread.edit(archived=True, locked=True)
                
                self.loop.create_task(self.start_new_generation())

        except Exception as e:
            await self.generation_channel.send(f"Error during generation: {str(e)}")
        finally:
            self.is_generating = False

    @tasks.loop(seconds=None)  # We'll set the seconds in setup_hook
    async def generate_loop(self):
        if not self.generation_channel or not self.is_ready():
            return
            
        if self.current_thread and self.variation_count < self.MAX_VARIATIONS:
            await self.generate_and_send()
        elif not self.current_thread and not self.is_generating:
            await self.start_new_generation()

    async def on_reaction_add(self, reaction, user):
        """Handle reactions"""
        if user.bot:
            return
            
        message = reaction.message
        
        # Only process reactions in threads
        if not isinstance(message.channel, discord.Thread):
            return
            
        # Only process reactions to our own messages
        if message.author != self.user:
            return
            
        if CONFIG['display']['debug_output']:
            print(f"Reaction in thread: {reaction.emoji}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run the Veist Discord bot')
    parser.add_argument('config', nargs='?', help='Path to config file')
    parser.add_argument('--config', dest='config_flag', help='Path to config file (alternative syntax)')
    args = parser.parse_args()

    # Use either positional or --config argument
    config_path = args.config or args.config_flag
    
    # Load configuration with optional path
    CONFIG = load_config(config_path)
    bot = VeistBot()
    bot.run(TOKEN)
