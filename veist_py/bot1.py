import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from generator import VeistGenerator
import asyncio
import random

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = discord.Object(id=os.getenv('GUILD_ID', '0'))
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '0'))  # Add your channel ID to .env

STARTER_PROMPTS = [
    "a mysterious robot in a garden",
    "an abstract digital landscape",
    "a futuristic city at night",
    "a geometric pattern with bright colors",
    "a cyberpunk scene with neon lights"
]

# Define meta reactions
META_REACTIONS = ["👍", "👎", "🏁"]

MAX_RETRIES = 3  # Maximum number of retries for generation
RETRY_DELAY = 10  # Seconds to wait between retries

class VeistBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        
        super().__init__(command_prefix='!', intents=intents)
        self.generator = VeistGenerator()
        self.generation_channel = None
        self.is_generating = False
        self.current_thread = None
        self.variation_count = 0
        self.MAX_VARIATIONS = 20  # Increased to 20 variations
        self.last_thread_message = None
        self.last_prompt = None
        self.current_version_message = None
        self.waiting_message_sent = False
        self.timer_message = None
        self.PROGRESS_SEGMENTS = 4
        self.EMPTY_BLOCK = "⬜"
        self.FILLED_BLOCK = "🟩"
        self.waiting_for_feedback = False

    async def setup_hook(self):
        print("Syncing commands to guild...")
        self.tree.copy_global_to(guild=GUILD_ID)
        synced = await self.tree.sync(guild=GUILD_ID)
        print(f"Synced {len(synced)} command(s)")
        
        # Start the generation loop
        self.generate_loop.start()

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        
        # Set up the generation channel
        self.generation_channel = self.get_channel(CHANNEL_ID)
        if not self.generation_channel:
            print(f"Warning: Could not find channel {CHANNEL_ID}")
            return
            
        # Start the generator
        self.generator.start_prompter()
        
        # Generate first image with random prompt
        initial_prompt = random.choice(STARTER_PROMPTS)
        await self.generate_and_send(initial_prompt, is_initial=True)

    async def collect_reactions(self):
        """Collect reactions from the last thread message"""
        if not self.last_thread_message:
            return [], {}
            
        # Fetch the message again to get updated reactions
        message = await self.current_thread.fetch_message(self.last_thread_message.id)
        
        # Collect regular and meta reactions separately
        regular_reactions = []
        meta_stats = {
            "👍": 0,  # likes
            "👎": 0,  # dislikes
            "🏁": 0   # finish flags
        }
        
        for reaction in message.reactions:
            emoji = str(reaction.emoji)
            if emoji in META_REACTIONS:
                # Subtract 1 from count to exclude bot's own reaction
                meta_stats[emoji] = max(0, reaction.count - 1)
            else:
                regular_reactions.append(emoji)
                
        return regular_reactions, meta_stats

    def build_next_prompt(self, reactions):
        """Build next prompt based on previous prompt and reactions"""
        if not reactions:
            return random.choice(STARTER_PROMPTS)
            
        reaction_text = " and ".join(reactions)
        return f"{self.last_prompt}, but more {reaction_text}"

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

    async def update_progress_bar(self, seconds_left):
        """Update the progress bar message"""
        if not self.timer_message:
            return
            
        filled = self.PROGRESS_SEGMENTS - int((seconds_left / 60) * self.PROGRESS_SEGMENTS)
        bar = self.FILLED_BLOCK * filled + self.EMPTY_BLOCK * (self.PROGRESS_SEGMENTS - filled)
        
        # Add waiting message if needed
        message = f"{bar} "
        if self.waiting_for_feedback:
            message += "⏳ waiting for feedback..."
        else:
            message += f"({seconds_left}s left)"
            
        try:
            await self.timer_message.edit(content=message)
        except (discord.NotFound, discord.HTTPException):
            self.timer_message = None

    async def start_progress_timer(self):
        """Start a new progress timer"""
        try:
            if self.timer_message:
                try:
                    await self.timer_message.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass
                self.timer_message = None
            
            if self.current_thread:
                initial_message = f"{self.EMPTY_BLOCK * 4} (60s left)"
                self.timer_message = await self.current_thread.send(initial_message)
                
                for seconds_left in [45, 30, 15]:
                    await asyncio.sleep(15)
                    if not self.timer_message:
                        return
                    await self.update_progress_bar(seconds_left)
                
                await asyncio.sleep(15)
                if self.timer_message:
                    if self.waiting_for_feedback:
                        # If waiting for feedback, start a new timer
                        self.loop.create_task(self.start_progress_timer())
                    else:
                        try:
                            await self.timer_message.edit(content=f"{self.FILLED_BLOCK * 4} (generating...)")
                        except (discord.NotFound, discord.HTTPException):
                            pass
                        self.timer_message = None
        except Exception as e:
            print(f"Error in progress timer: {e}")
            self.timer_message = None

    async def generate_and_send(self, prompt=None, is_initial=False):
        """Helper method to generate and send images"""
        if self.is_generating:
            return
            
        self.is_generating = True
        try:
            if not self.current_thread:
                prompt = random.choice(STARTER_PROMPTS)
                self.waiting_message_sent = False
                self.timer_message = None
                self.waiting_for_feedback = False
            elif not is_initial:
                regular_reactions, meta_stats = await self.collect_reactions()
                
                # Early completion check
                if (meta_stats['👍'] == 0 and 
                    meta_stats['👎'] == 0 and 
                    meta_stats['🏁'] > 0):
                    self.waiting_for_feedback = False
                    # Clear timer if it exists
                    if self.timer_message:
                        try:
                            await self.timer_message.delete()
                        except (discord.NotFound, discord.HTTPException):
                            pass
                        self.timer_message = None
                    try:
                        # Get the attachment from the last message
                        if self.last_thread_message and self.last_thread_message.attachments:
                            # Download the attachment
                            attachment = self.last_thread_message.attachments[0]
                            # Create a temporary file with the image
                            temp_filename = f"temp_{attachment.filename}"
                            await attachment.save(temp_filename)
                            
                            # Post final result
                            final_file = discord.File(temp_filename)
                            await self.current_version_message.delete()
                            await self.generation_channel.send(
                                f"✨ Final Result (by request)\nPrompt: {self.last_prompt}", 
                                file=final_file
                            )
                            
                            # Clean up temp file
                            os.remove(temp_filename)
                            
                            await self.current_thread.send("🏁 Maximum variations reached! Final result posted in main channel.")
                            await self.current_thread.edit(archived=True, locked=True)
                            
                            # Schedule immediate start of next generation
                            self.loop.create_task(self.start_new_generation())
                            return
                        else:
                            raise ValueError("No attachment found in last message")
                            
                    except Exception as e:
                        await self.current_thread.send(f"Error processing early completion: {str(e)}")
                        return
                
                # Check if we have any reactions to work with
                if not regular_reactions and all(v == 0 for v in meta_stats.values()):
                    self.waiting_for_feedback = True
                    if not self.timer_message:
                        # Start a new timer if none exists
                        self.loop.create_task(self.start_progress_timer())
                    return
                
                # If we have reactions, proceed with generation
                self.waiting_for_feedback = False
                if regular_reactions:
                    prompt = self.build_next_prompt(regular_reactions)
                else:
                    prompt = self.last_prompt
                
                print(f"Previous image stats - Likes: {meta_stats['👍']}, "
                      f"Dislikes: {meta_stats['👎']}, Finish flags: {meta_stats['🏁']}")
            
            # Use new retry method
            result = await self.generate_with_retry(prompt)
            
            if "error" in result:
                error_msg = f"Error generating image: {result['error']}"
                await self.generation_channel.send(error_msg)
                if "too busy" in result["error"].lower():
                    await asyncio.sleep(RETRY_DELAY)  # Wait before next attempt
                return

            if not self.current_thread:
                # Initial post in main channel (text only)
                main_message = await self.generation_channel.send(
                    f"🎨 Starting new generation thread\nPrompt: {result['prompt']}"
                )
                
                # Create new thread with simpler name
                self.current_thread = await main_message.create_thread(
                    name="Variations",
                    auto_archive_duration=60
                )
                self.variation_count = 0
                
                # Post initial image in thread
                thread_file = discord.File(result["path"])
                self.last_thread_message = await self.current_thread.send(
                    f"Initial variation (1/{self.MAX_VARIATIONS})\nPrompt: {result['prompt']}", 
                    file=thread_file
                )
                
                # Post initial "current version" in main channel
                current_file = discord.File(result["path"])
                self.current_version_message = await self.generation_channel.send(
                    f"💫 Current Version (1/{self.MAX_VARIATIONS})\nPrompt: {result['prompt']}", 
                    file=current_file
                )
            else:
                # Post variation in thread
                thread_file = discord.File(result["path"])
                self.last_thread_message = await self.current_thread.send(
                    f"Variation {self.variation_count + 1}/{self.MAX_VARIATIONS}\nPrompt: {result['prompt']}", 
                    file=thread_file
                )
                
                # Update "current version" in main channel (only for non-final variations)
                if self.variation_count < self.MAX_VARIATIONS - 1:
                    await self.current_version_message.delete()
                    current_file = discord.File(result["path"])
                    self.current_version_message = await self.generation_channel.send(
                        f"💫 Current Version ({self.variation_count + 1}/{self.MAX_VARIATIONS})\nPrompt: {result['prompt']}", 
                        file=current_file
                    )

            # Add reactions to thread message
            for reaction in META_REACTIONS:
                await self.last_thread_message.add_reaction(reaction)

            self.last_prompt = result['prompt']
            self.variation_count += 1
            
            # If we've reached max variations, update to final result
            if self.variation_count >= self.MAX_VARIATIONS:
                # Update to final result in main channel
                await self.current_version_message.delete()
                final_file = discord.File(result["path"])
                await self.generation_channel.send(
                    f"✨ Final Result\nPrompt: {result['prompt']}", 
                    file=final_file
                )
                
                await self.current_thread.send("🏁 Maximum variations reached! Final result posted in main channel.")
                await self.current_thread.edit(archived=True, locked=True)
                
                # Schedule immediate start of next generation
                self.loop.create_task(self.start_new_generation())
                
            # Start progress timer after successful generation
            if self.current_thread:  # Only start timer if we have a thread
                self.loop.create_task(self.start_progress_timer())

        except Exception as e:
            await self.generation_channel.send(f"Error during generation: {str(e)}")
            # Clear timer on error
            if self.timer_message:
                try:
                    await self.timer_message.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass
                self.timer_message = None
        finally:
            self.is_generating = False

    @tasks.loop(seconds=60)
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
            
        # Process the reaction here (you can add specific logic later)
        print(f"Reaction in thread: {reaction.emoji}")

bot = VeistBot()

# Admin command to force sync
@bot.command()
@commands.is_owner()
async def sync(ctx):
    print("Syncing commands...")
    synced = await bot.tree.sync()
    await ctx.send(f"Synced {len(synced)} command(s)")

# Simple test command
@bot.tree.command(name="ping", description="Test if the bot is responsive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! 🏓")

@bot.tree.command(name="test", description="Another test command")
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("Test command works!")

@bot.tree.command(name="generate", description="Generate an image from a prompt")
async def generate(interaction: discord.Interaction, prompt: str):
    # Acknowledge the command immediately
    await interaction.response.defer()
    
    # Start the generator if it's not active
    if not bot.generator.active:
        bot.generator.start_prompter()
    
    # Generate the image
    result = bot.generator.generate_image(prompt)
    
    if "error" in result:
        await interaction.followup.send(f"Error generating image: {result['error']}")
        return
        
    # Create discord file from the image
    file = discord.File(result["path"])
    
    # Send the image with the prompt as a message
    await interaction.followup.send(
        f"Prompt: {result['prompt']}\nStatus: {result['status']}", 
        file=file
    )

@bot.tree.command(name="start", description="Start the generator")
async def start(interaction: discord.Interaction):
    bot.generator.start_prompter()
    await interaction.response.send_message("Generator started in prompter mode! 🎨")

@bot.tree.command(name="stop", description="Stop the generator")
async def stop(interaction: discord.Interaction):
    bot.generator.stop()
    await interaction.response.send_message("Generator stopped! ⏹️")

# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN)