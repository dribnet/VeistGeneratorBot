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
        
        # Add progress bar related attributes
        self.waiting_message_sent = False
        self.timer_message = None
        self.PROGRESS_SEGMENTS = 4  # Number of segments in the progress bar
        self.EMPTY_BLOCK = "⬜"     # Empty block for progress bar
        self.FILLED_BLOCK = "🟩"    # Filled block for progress bar
        self.waiting_for_feedback = False

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

    async def update_thread_message_status(self, status_text):
        """Update the status text on the last thread message"""
        if self.last_thread_message:
            try:
                content = self.last_thread_message.content
                # Replace the last line (status line)
                lines = content.split('\n')
                if len(lines) > 1:
                    lines[-1] = status_text
                    new_content = '\n'.join(lines)
                else:
                    new_content = f"{content}\n{status_text}"
                    
                await self.last_thread_message.edit(content=new_content)
            except Exception as e:
                print(f"Error updating thread message: {e}")

    async def generate_and_send(self, prompt=None, is_initial=False):
        """Helper method to generate and send images"""
        if self.is_generating:
            return
            
        self.is_generating = True
        self.waiting_for_feedback = False
        
        try:
            # Immediately show generating message in both thread and main channel
            if self.current_thread and self.last_thread_message:
                await self.update_thread_message_status("🔄 Generating new image...")
            
            # Create or update timer message in main channel immediately
            if self.timer_message:
                try:
                    await self.timer_message.edit(content="🔄 Generating new image...")
                except:
                    self.timer_message = await self.generation_channel.send("🔄 Generating new image...")
            else:
                self.timer_message = await self.generation_channel.send("🔄 Generating new image...")
            
            if not self.current_thread:
                prompt = random.choice(STARTER_PROMPTS)
            elif not is_initial:
                regular_reactions, meta_stats = await self.collect_reactions()
                
                if CONFIG['display']['debug_output']:
                    print(f"Early completion check:")
                    print(f"Meta stats: {meta_stats}")
                    print(f"Regular reactions: {regular_reactions}")
                
                # Early completion check - only require heart and no regular reactions
                if (meta_stats['❤️'] > 0 and 
                    sum(regular_reactions.values()) == 0):
                    if CONFIG['display']['debug_output']:
                        print("Early completion conditions met!")
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
                            
                            # Clean up timer message
                            if self.timer_message:
                                await self.timer_message.delete()
                                self.timer_message = None
                                
                            self.loop.create_task(self.start_new_generation())
                            return
                    except Exception as e:
                        await self.current_thread.send(f"Error processing early completion: {str(e)}")
                        return
                
                # Check if we have any non-meta reactions
                if not any(count > 0 for count in regular_reactions.values()):
                    await self.update_thread_message_status("⏳ Waiting for reactions...")
                    self.waiting_for_feedback = True
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
                message_content = f"Initial variation"
                if CONFIG['display']['prompt_visibility'] == "Full":
                    message_content += f"\nPrompt: {result['prompt']}"
                message_content += "\n\n🔄 Collecting feedback..."
                
                thread_file = discord.File(result["path"])
                self.last_thread_message = await self.current_thread.send(
                    message_content, 
                    file=thread_file
                )
                
                # Post current version
                current_version_content = f"💫 Current Version"
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
                message_content = f"Variation {self.variation_count + 1}"
                if CONFIG['display']['prompt_visibility'] == "Full":
                    message_content += f"\nPrompt: {result['prompt']}"
                message_content += "\n\n🔄 Collecting feedback..."
                
                thread_file = discord.File(result["path"])
                self.last_thread_message = await self.current_thread.send(
                    message_content,
                    file=thread_file
                )
                
                # Update current version
                await self.current_version_message.delete()
                current_version_content = f"💫 Current Version"
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
            
            # No more check for max variations - removed

            # Clean up timer message when generating a new image
            if self.timer_message:
                await self.timer_message.delete()
                self.timer_message = None

        except Exception as e:
            await self.generation_channel.send(f"Error during generation: {str(e)}")
        finally:
            self.is_generating = False

    @tasks.loop(seconds=60)  # Default interval, will be changed in setup_hook
    async def generate_loop(self):
        """Main generation loop"""
        if not self.generation_channel:
            return
            
        if not self.current_thread:
            await self.start_new_generation()
        else:
            await self.generate_and_send()
            
    @generate_loop.before_loop
    async def before_generate_loop(self):
        await self.wait_until_ready()
        
        # Find the generation channel
        channel_id = CONFIG['discord']['channel_id']
        channel_name = CONFIG['discord']['channel_name']
        
        if channel_id:
            self.generation_channel = self.get_channel(channel_id)
        else:
            # Find channel by name
            for guild in self.guilds:
                channel = discord.utils.get(guild.text_channels, name=channel_name)
                if channel:
                    self.generation_channel = channel
                    break
                    
        if not self.generation_channel:
            print(f"Could not find generation channel (ID: {channel_id}, Name: {channel_name})")
            self.generate_loop.cancel()
            return
            
        print(f"Found generation channel: {self.generation_channel.name}")
        
        # Start the progress bar update loop
        self.update_progress_bar.start()

    @tasks.loop(seconds=5)
    async def update_progress_bar(self):
        """Update the progress bar to show time until next generation"""
        if not self.generation_channel or not self.current_thread:
            return
            
        # If we're currently generating, show a generating message instead of countdown
        if self.is_generating:
            status = "🔄 Generating new image..."
            
            # Update the thread message
            await self.update_thread_message_status(status)
            
            # Update or create timer message in main channel
            if not self.timer_message:
                self.timer_message = await self.generation_channel.send("🔄 Generating new image...")
            else:
                try:
                    await self.timer_message.edit(content="🔄 Generating new image...")
                except:
                    # If message was deleted, create a new one
                    self.timer_message = await self.generation_channel.send("🔄 Generating new image...")
            return
            
        # Calculate time until next generation
        time_left = self.generate_loop.next_iteration - discord.utils.utcnow()
        if time_left.total_seconds() <= 0:
            return
            
        # Calculate progress (0.0 to 1.0)
        interval = CONFIG['generation']['seconds_per_variation']
        progress = 1.0 - (time_left.total_seconds() / interval)
        
        # Create progress bar
        filled_segments = int(progress * self.PROGRESS_SEGMENTS)
        empty_segments = self.PROGRESS_SEGMENTS - filled_segments
        progress_bar = self.FILLED_BLOCK * filled_segments + self.EMPTY_BLOCK * empty_segments
        
        # Format time left
        minutes = int(time_left.total_seconds() // 60)
        seconds = int(time_left.total_seconds() % 60)
        time_str = f"{minutes:01d}:{seconds:02d}"
        
        # Create status message
        if self.waiting_for_feedback:
            status = f"⏳ Waiting for reactions... ({time_str} until next check) {progress_bar}"
        else:
            status = f"⏱️ Next variation in {time_str} {progress_bar}"
        
        # Update the message
        await self.update_thread_message_status(status)
        
        # Create or update timer message in main channel
        if not self.timer_message:
            self.timer_message = await self.generation_channel.send(f"⏱️ Next generation in {time_str} {progress_bar}")
        else:
            try:
                await self.timer_message.edit(content=f"⏱️ Next generation in {time_str} {progress_bar}")
            except:
                # If message was deleted, create a new one
                self.timer_message = await self.generation_channel.send(f"⏱️ Next generation in {time_str} {progress_bar}")

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
