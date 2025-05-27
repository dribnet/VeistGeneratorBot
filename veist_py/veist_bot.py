#!/usr/bin/env python3
"""
Veist Bot V2 - Clean implementation with image evolution
Simple starting point that can be extended
"""

import os
import logging
import asyncio
import base64
import io
from datetime import datetime
from dotenv import load_dotenv
import discord
from discord.ext import commands
from openai import OpenAI

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
        
        # Robot evolution state
        self.robot_channel_name = "robot-evolution"  # Dedicated channel name
        self.robot_channel = None
        self.current_response_id = None
        self.evolution_count = 0
        
        # Initialize OpenAI client
        try:
            self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            logger.info("OpenAI client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.openai_client = None
        
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
        
        # Find the robot evolution channel in Development category
        for guild in self.guilds:
            # Look for Development category
            dev_category = None
            for category in guild.categories:
                if category.name.lower() == "development":
                    dev_category = category
                    logger.info(f"Found Development category")
                    break
            
            if dev_category:
                # Look for robot-evolution channel in this category
                for channel in dev_category.text_channels:
                    if channel.name == self.robot_channel_name:
                        self.robot_channel = channel
                        logger.info(f"Found robot evolution channel in Development: {channel.name}")
                        break
            
            # If not found in Development, check all channels as fallback
            if not self.robot_channel:
                for channel in guild.text_channels:
                    if channel.name == self.robot_channel_name:
                        self.robot_channel = channel
                        logger.info(f"Found robot evolution channel: {channel.name} (not in Development)")
                        break
        
        if self.robot_channel and self.openai_client:
            # Generate and post initial robot
            await self.robot_channel.send(
                "🤖 **Robot Evolution Starting!**\n"
                "I'll generate an initial robot, then evolve it based on your messages.\n"
                "Just type what changes you'd like to see!"
            )
            
            await self.generate_initial_robot()
        elif not self.robot_channel:
            logger.error(f"Could not find channel named '{self.robot_channel_name}'")
            logger.info("Please create a channel called 'robot-evolution'")
        
        # Log some stats
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
    async def on_message(self, message):
        """Handle messages"""
        # Ignore our own messages
        if message.author == self.user:
            return
            
        # Check if message is in robot channel
        if message.channel == self.robot_channel and self.current_response_id:
            # Any message in robot channel is treated as evolution request
            await self.evolve_robot(message.content)
            
        # Process commands if any
        await self.process_commands(message)
        
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
    
    async def generate_initial_robot(self):
        """Generate the first robot image"""
        if not self.openai_client or not self.robot_channel:
            return
            
        prompt = """Create a friendly, colorful robot character in a simple environment. 
        The robot should have clear, distinct features that can be easily modified.
        Digital art style, bright colors, clear details. Make it cute and appealing!"""
        
        try:
            # Show typing indicator
            async with self.robot_channel.typing():
                response = self.openai_client.responses.create(
                    model="gpt-4o-mini",
                    input=prompt,
                    tools=[{"type": "image_generation", "quality": "low"}],
                )
                
                # Extract image
                for output in response.output:
                    if output.type == "image_generation_call":
                        # Save response ID for future evolutions
                        self.current_response_id = response.id
                        self.evolution_count = 0
                        
                        # Convert to discord file
                        image_bytes = base64.b64decode(output.result)
                        file = discord.File(
                            io.BytesIO(image_bytes), 
                            filename=f"robot_initial.png"
                        )
                        
                        await self.robot_channel.send(
                            "🎨 **Initial Robot Generated!**\n"
                            "Type any message to evolve it!",
                            file=file
                        )
                        logger.info("Initial robot posted")
                        return
                        
            logger.error("No image in response")
            
        except Exception as e:
            logger.error(f"Failed to generate initial robot: {e}")
            await self.robot_channel.send(f"❌ Failed to generate robot: {str(e)}")
    
    async def evolve_robot(self, modification: str):
        """Evolve the robot based on user input"""
        if not self.openai_client or not self.robot_channel or not self.current_response_id:
            return
            
        try:
            # Show typing indicator
            async with self.robot_channel.typing():
                response = self.openai_client.responses.create(
                    model="gpt-4o-mini",
                    previous_response_id=self.current_response_id,
                    input=f"Modify the robot: {modification}",
                    tools=[{"type": "image_generation", "quality": "low"}],
                )
                
                # Extract evolved image
                for output in response.output:
                    if output.type == "image_generation_call":
                        # Update state
                        self.current_response_id = response.id
                        self.evolution_count += 1
                        
                        # Convert to discord file
                        image_bytes = base64.b64decode(output.result)
                        file = discord.File(
                            io.BytesIO(image_bytes), 
                            filename=f"robot_evolution_{self.evolution_count}.png"
                        )
                        
                        await self.robot_channel.send(
                            f"🔄 **Evolution #{self.evolution_count}**\n"
                            f"Applied: *{modification}*",
                            file=file
                        )
                        logger.info(f"Evolution {self.evolution_count} posted")
                        return
                        
            logger.error("No image in evolution response")
            
        except Exception as e:
            logger.error(f"Failed to evolve robot: {e}")
            await self.robot_channel.send(f"❌ Evolution failed: {str(e)}")

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