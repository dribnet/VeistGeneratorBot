#!/usr/bin/env python3
"""
Veist Bot V2 - Clean implementation with image evolution
Simple starting point that can be extended
"""

import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import discord
from discord.ext import commands

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('veist_bot')

class VeistBot(commands.Bot):
    """Main bot class with clean structure"""
    
    def __init__(self):
        # Bot configuration
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            description='Veist Image Evolution Bot V2'
        )
        
        # Configuration (will add more as needed)
        self.guild_id = int(os.getenv('GUILD_ID', 0))
        self.channel_id = int(os.getenv('CHANNEL_ID', 0))
        self.generation_channel = None
        
    async def setup_hook(self):
        """Called when bot is starting up"""
        logger.info("Bot setup hook called")
        
        # Add any startup tasks here
        # For now, just sync commands if we add any
        if self.guild_id:
            guild = discord.Object(id=self.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands to guild {self.guild_id}")
    
    async def on_ready(self):
        """Called when bot is fully ready"""
        logger.info(f'Bot connected as {self.user} (ID: {self.user.id})')
        
        # Find our generation channel
        if self.channel_id:
            self.generation_channel = self.get_channel(self.channel_id)
            if self.generation_channel:
                logger.info(f"Found generation channel: {self.generation_channel.name}")
                
                # Say hello!
                await self.generation_channel.send(
                    "🤖 **Veist Bot V2 Online!**\n"
                    "Ready to evolve images based on your reactions. "
                    "Starting fresh with a cleaner architecture!"
                )
            else:
                logger.error(f"Could not find channel with ID {self.channel_id}")
        else:
            logger.warning("No CHANNEL_ID configured")
        
        # Log some stats
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
    async def on_message(self, message):
        """Handle messages"""
        # Ignore our own messages
        if message.author == self.user:
            return
            
        # Process commands if any
        await self.process_commands(message)
        
        # We can add more message handling here later
        
    async def on_reaction_add(self, reaction, user):
        """Handle reactions - will implement image evolution here"""
        # Ignore bot reactions
        if user.bot:
            return
            
        # For now, just log it
        logger.debug(f"Reaction {reaction.emoji} added by {user.name}")
        
        # TODO: Implement image evolution based on reactions
        
    async def on_error(self, event, *args, **kwargs):
        """Error handler"""
        logger.exception(f"Error in {event}")

async def main():
    """Main entry point"""
    # Load environment variables
    load_dotenv()
    
    # Check for required environment variables
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("No DISCORD_TOKEN found in environment!")
        return
    
    # Create and run bot
    bot = VeistBot()
    
    try:
        logger.info("Starting bot...")
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
    finally:
        logger.info("Shutting down bot...")
        await bot.close()

if __name__ == "__main__":
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot shutdown requested")