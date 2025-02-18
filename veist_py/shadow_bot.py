import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
from typing import Dict
import random

load_dotenv()
TOKEN = os.getenv('DISCORD_SHADOWBOT_TOKEN')  # Updated token name
VEIST_BOT_ID = int(os.getenv('VEIST_BOT_ID', '0'))

print(f"Initializing shadow bot. Will watch for Veist bot ID: {VEIST_BOT_ID}")

class ShadowData:
    def __init__(self, member: discord.Member):
        self.member = member
        self.name = f"👻shadow_{member.name}"
        self.message_count = 0

class ShadowBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.reactions = True
        super().__init__(command_prefix='!', intents=intents)
        
        self.webhooks: Dict[int, discord.Webhook] = {}
        self.shadows: Dict[int, ShadowData] = {}

    async def setup_hook(self):
        print("Setting up shadow bot...")

    async def on_ready(self):
        print(f'{self.user} is ready to create shadows!')
        # Create shadows for all current members
        for guild in self.guilds:
            print(f"Creating shadows for guild: {guild.name}")
            for member in guild.members:
                if not member.bot:
                    shadow = self.create_shadow(member)
                    print(f"Created shadow for {member.name}: {shadow.name}")

    def create_shadow(self, member: discord.Member) -> ShadowData:
        """Create a new shadow for a member"""
        shadow = ShadowData(member)
        self.shadows[member.id] = shadow
        print(f"Created new shadow: {shadow.name}")
        return shadow

    async def on_message(self, message):
        print(f"Received message from: {message.author.name} (ID: {message.author.id})")
        
        # Check if message is from the Veist bot
        if message.author.id == VEIST_BOT_ID:
            print("Message is from Veist bot!")
            
            # Add ghost reaction
            try:
                await message.add_reaction("👻")
                print("Added ghost reaction")
            except discord.errors.Forbidden as e:
                print(f"Error adding reaction: {e}")
            except Exception as e:
                print(f"Unexpected error adding reaction: {e}")
            
            # Get all shadows to respond
            for shadow in self.shadows.values():
                try:
                    await message.channel.send(f"*{shadow.name} observes silently...*")
                    print(f"Posted shadow response for {shadow.name}")
                except Exception as e:
                    print(f"Error posting shadow response: {e}")

        await self.process_commands(message)

    async def on_reaction_add(self, reaction, user):
        print(f"Reaction added: {reaction.emoji} by {user.name}")

bot = ShadowBot()

if __name__ == "__main__":
    print("Starting shadow bot...")
    bot.run(TOKEN) 