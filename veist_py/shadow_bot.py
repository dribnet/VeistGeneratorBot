import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
from typing import Dict

load_dotenv()
TOKEN = os.getenv('DISCORD_SHADOWBOT_TOKEN')
VEIST_BOT_ID = int(os.getenv('VEIST_BOT_ID', '0'))

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
        
        self.shadows: Dict[int, ShadowData] = {}

    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        print(f'{self.user} is ready to create shadows!')
        for guild in self.guilds:
            for member in guild.members:
                if not member.bot:
                    self.create_shadow(member)

    def create_shadow(self, member: discord.Member) -> ShadowData:
        shadow = ShadowData(member)
        self.shadows[member.id] = shadow
        return shadow

    async def on_message(self, message):
        if message.author.id == VEIST_BOT_ID:
            try:
                await message.add_reaction("👻")
            except Exception:
                pass

        await self.process_commands(message)

bot = ShadowBot()

if __name__ == "__main__":
    bot.run(TOKEN) 