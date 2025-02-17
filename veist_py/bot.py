import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set up bot
class VeistBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # Sync commands with Discord
        await self.tree.sync()
        
    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')

bot = VeistBot()

# Simple test command
@bot.tree.command(name="ping", description="Test if the bot is responsive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! 🏓")

# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN)