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

class VeistBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True  # Make sure we can see reactions
        
        super().__init__(command_prefix='!', intents=intents)
        self.generator = VeistGenerator()
        self.generation_channel = None
        self.is_generating = False
        self.last_message = None
        self.last_prompt = None

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
        self.last_prompt = initial_prompt
        await self.generate_and_send(initial_prompt, is_initial=True)

    async def collect_reactions(self):
        """Collect reactions from the last message"""
        if not self.last_message:
            return []
            
        # Fetch the message again to get updated reactions
        message = await self.generation_channel.fetch_message(self.last_message.id)
        
        # Collect all reactions
        reactions = []
        for reaction in message.reactions:
            # Convert emoji to text description
            if isinstance(reaction.emoji, str):
                reactions.append(reaction.emoji)
            else:
                reactions.append(reaction.emoji.name)
                
        print(f"Collected reactions: {reactions}")  # Debug print
        return reactions

    def build_next_prompt(self, reactions):
        """Build next prompt based on previous prompt and reactions"""
        if not reactions:
            return random.choice(STARTER_PROMPTS)
            
        # Convert reactions to prompt modifications
        reaction_text = " and ".join(reactions)
        return f"{self.last_prompt}, but more {reaction_text}"

    async def generate_and_send(self, prompt=None, is_initial=False):
        """Helper method to generate and send images"""
        if self.is_generating:
            return
            
        self.is_generating = True
        try:
            # If no prompt provided and not initial, build from reactions
            if prompt is None and not is_initial:
                reactions = await self.collect_reactions()
                prompt = self.build_next_prompt(reactions)
            
            # Run the generation in a thread pool
            result = await self.loop.run_in_executor(
                None, 
                self.generator.generate_image,
                prompt
            )
            
            if "error" in result:
                await self.generation_channel.send(f"Error generating image: {result['error']}")
                return
                
            file = discord.File(result["path"])
            prefix = "🎨 Starting up with" if is_initial else "🎮 New generation\n"
            
            # Send the message and store it
            self.last_message = await self.generation_channel.send(
                f"{prefix}Prompt: {result['prompt']}\nStatus: {result['status']}", 
                file=file
            )
            self.last_prompt = result['prompt']
            
            # Add some starter reactions for guidance
            if is_initial:
                starter_reactions = ["🔥", "❄️", "🌟", "🎨", "🌈"]
                for reaction in starter_reactions:
                    await self.last_message.add_reaction(reaction)
                
        except Exception as e:
            await self.generation_channel.send(f"Error during generation: {str(e)}")
        finally:
            self.is_generating = False

    @tasks.loop(seconds=60)
    async def generate_loop(self):
        if not self.generation_channel or not self.is_ready():
            return
            
        await self.generate_and_send()

    @generate_loop.before_loop
    async def before_generate_loop(self):
        await self.wait_until_ready()

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