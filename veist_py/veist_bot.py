#!/usr/bin/env python3
"""
Veist Bot V2 - Modular architecture for multiple evolution modes
"""

import os
import logging
import asyncio
import base64
import io
import yaml
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import discord
from discord.ext import commands
from openai import OpenAI
from apps.publish import AkaSwapPublisher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('veist_bot')


class VeistModule(ABC):
    """Base class for bot modules"""
    
    def __init__(self, bot: 'VeistBot'):
        self.bot = bot
        self.enabled = True
        
    @abstractmethod
    async def on_ready(self):
        """Called when bot is ready"""
        pass
        
    @abstractmethod
    async def on_message(self, message: discord.Message):
        """Handle messages"""
        pass
        
    @abstractmethod
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Handle reactions"""
        pass


class TextEvolutionModule(VeistModule):
    """Handles text-based robot evolution in robot-text-evolution channel"""
    
    def __init__(self, bot: 'VeistBot'):
        super().__init__(bot)
        self.channel_name = "robot-text-evolution"
        self.channel = None
        self.current_response_id = None
        self.evolution_count = 0
        self.last_message = None
        self.last_image_path = None
        self.pending_publish = False
        self.pending_quality_bump = False
        self.current_quality = "low"
        self.quality_levels = ["low", "medium", "high"]
        
    async def on_ready(self):
        """Find channel and start initial robot"""
        # Find the robot evolution channel in Development category
        for guild in self.bot.guilds:
            # Look for Development category
            dev_category = None
            for category in guild.categories:
                if category.name.lower() == "development":
                    dev_category = category
                    logger.info(f"Found Development category")
                    break
            
            if dev_category:
                # Look for robot-text-evolution channel in this category
                for channel in dev_category.text_channels:
                    if channel.name == self.channel_name:
                        self.channel = channel
                        logger.info(f"Found {self.channel_name} channel in Development")
                        break
            
            # If not found in Development, check all channels as fallback
            if not self.channel:
                for channel in guild.text_channels:
                    if channel.name == self.channel_name:
                        self.channel = channel
                        logger.info(f"Found {self.channel_name} channel (not in Development)")
                        break
        
        if self.channel and self.bot.openai_client:
            # Generate and post initial robot
            await self.channel.send(
                "🤖 **Robot Evolution Starting!**\n"
                "I'll generate an initial robot, then evolve it based on your messages.\n"
                "Just type what changes you'd like to see!"
            )
            
            await self.generate_initial_robot()
        elif not self.channel:
            logger.error(f"Could not find channel named '{self.channel_name}'")
            
    async def on_message(self, message: discord.Message):
        """Handle text messages for evolution"""
        # Ignore our own messages
        if message.author == self.bot.user:
            return
            
        # Check if message is in our channel
        if message.channel == self.channel and self.current_response_id:
            # React to show we're processing
            await message.add_reaction("⏳")  # Hourglass to show processing
            
            try:
                # Evolve the robot
                await self.evolve_robot(message.content)
                
                # Remove processing reaction and add success
                await message.remove_reaction("⏳", self.bot.user)
                await message.add_reaction("✅")  # Checkmark to show complete
            except Exception as e:
                # Remove processing reaction and add error
                await message.remove_reaction("⏳", self.bot.user)
                await message.add_reaction("❌")  # X to show error
                logger.error(f"Evolution failed: {e}")
                
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Handle meta reactions"""
        # Ignore bot reactions
        if user.bot:
            return
            
        # Only process reactions in our channel
        if reaction.message.channel != self.channel:
            return
            
        # Check if this is a reaction to our last message
        if reaction.message.id != self.last_message.id if self.last_message else None:
            return
            
        emoji_str = str(reaction.emoji)
        
        # Check for publish confirmation (thumbs up to confirm)
        if self.pending_publish and emoji_str == "👍":
            await self.publish_as_nft()
            self.pending_publish = False
            return
            
        # Check for quality bump confirmation
        if self.pending_quality_bump and emoji_str == "👍":
            await self.bump_quality()
            self.pending_quality_bump = False
            return
            
        # Check for all_done meta reaction
        if emoji_str == self.bot.config['meta_reactions']['all_done']:
            self.pending_publish = True
            confirm_msg = await self.channel.send(
                "🎨 **Ready to publish as NFT?**\n"
                "React with 👍 to confirm publishing this robot to the Tezos testnet!"
            )
            await confirm_msg.add_reaction("👍")
            self.last_message = confirm_msg
            
        # Check for keep_going meta reaction (quality bump)
        elif emoji_str == self.bot.config['meta_reactions']['keep_going']:
            current_idx = self.quality_levels.index(self.current_quality)
            if current_idx < len(self.quality_levels) - 1:
                next_quality = self.quality_levels[current_idx + 1]
                self.pending_quality_bump = True
                confirm_msg = await self.channel.send(
                    f"📈 **Upgrade image quality?**\n"
                    f"Current: {self.current_quality} → Next: {next_quality}\n"
                    f"React with 👍 to regenerate at higher quality!"
                )
                await confirm_msg.add_reaction("👍")
                self.last_message = confirm_msg
            else:
                await self.channel.send("Already at highest quality! 🌟")
                
        # Check for go_back meta reaction (reboot with new robot)
        elif emoji_str == self.bot.config['meta_reactions']['go_back']:
            await self.channel.send(
                "🔄 **Rebooting with a new robot!**\n"
                "Starting fresh..."
            )
            # Reset quality and generate new robot
            self.current_quality = "low"
            await self.generate_initial_robot()
            
    async def generate_initial_robot(self):
        """Generate the first robot image"""
        if not self.bot.openai_client or not self.channel:
            return
            
        prompt = """Create a friendly, colorful robot character in a simple environment. 
        The robot should have clear, distinct features that can be easily modified.
        Digital art style, bright colors, clear details. Make it cute and appealing!"""
        
        try:
            # Show typing indicator
            async with self.channel.typing():
                response = self.bot.openai_client.responses.create(
                    model="gpt-4o-mini",
                    input=prompt,
                    tools=[{"type": "image_generation", "quality": self.current_quality}],
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
                        
                        # Save image for potential NFT
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        self.last_image_path = f"outputs/robot_{timestamp}.png"
                        os.makedirs("outputs", exist_ok=True)
                        with open(self.last_image_path, 'wb') as f:
                            f.write(image_bytes)
                        
                        # Send message
                        self.last_message = await self.channel.send(
                            "🎨 **Initial Robot Generated!**\n"
                            "Type any message to evolve it!",
                            file=file
                        )
                        
                        # Add meta reactions
                        for reaction in self.bot.meta_reactions:
                            await self.last_message.add_reaction(reaction)
                        
                        logger.info("Initial robot posted with reactions")
                        return
                        
            logger.error("No image in response")
            
        except Exception as e:
            logger.error(f"Failed to generate initial robot: {e}")
            await self.channel.send(f"❌ Failed to generate robot: {str(e)}")
            
    async def evolve_robot(self, modification: str):
        """Evolve the robot based on user input"""
        if not self.bot.openai_client or not self.channel or not self.current_response_id:
            return
            
        try:
            # Show typing indicator
            async with self.channel.typing():
                response = self.bot.openai_client.responses.create(
                    model="gpt-4o-mini",
                    previous_response_id=self.current_response_id,
                    input=f"Modify the robot: {modification}",
                    tools=[{"type": "image_generation", "quality": self.current_quality}],
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
                        
                        # Save image for potential NFT
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        self.last_image_path = f"outputs/robot_{timestamp}.png"
                        with open(self.last_image_path, 'wb') as f:
                            f.write(image_bytes)
                        
                        # Send message
                        self.last_message = await self.channel.send(
                            f"🔄 **Evolution #{self.evolution_count}**\n"
                            f"Applied: *{modification}*",
                            file=file
                        )
                        
                        # Add meta reactions
                        for reaction in self.bot.meta_reactions:
                            await self.last_message.add_reaction(reaction)
                        
                        logger.info(f"Evolution {self.evolution_count} posted with reactions")
                        return
                        
            logger.error("No image in evolution response")
            
        except Exception as e:
            logger.error(f"Failed to evolve robot: {e}")
            raise  # Re-raise to trigger error reaction
            
    async def publish_as_nft(self):
        """Publish the current robot as an NFT"""
        if not self.bot.nft_publisher or not self.last_image_path:
            await self.channel.send("❌ Unable to publish: No image or publisher available")
            return
            
        try:
            async with self.channel.typing():
                # Publish to NFT
                result = self.bot.nft_publisher.publish_image(
                    image_path=self.last_image_path,
                    name=f"Veist Robot Evolution #{self.evolution_count}",
                    description=f"Community-evolved robot from VeistBot. Evolution count: {self.evolution_count}",
                    receiver_address="tz2J3uKDJ9s68RtX1XSsqQB6ENRS3wiL1HR5"  # Test wallet
                )
                
                if result.get('success'):
                    nft_url = result['mint'].get('viewUrl', 'https://testnets.akaswap.com')
                    await self.channel.send(
                        f"✅ **NFT Published!**\n"
                        f"🎨 View on akaSwap: {nft_url}\n"
                        f"📦 Token ID: {result['mint'].get('tokenId', 'Unknown')}\n"
                        f"🔗 Contract: {result['mint'].get('contract', 'Unknown')}"
                    )
                    logger.info(f"NFT published: {result}")
                else:
                    await self.channel.send("❌ NFT publishing failed")
                    
        except Exception as e:
            logger.error(f"NFT publishing error: {e}")
            await self.channel.send(f"❌ NFT publishing error: {str(e)}")
            
    async def bump_quality(self):
        """Regenerate the current robot at higher quality"""
        if not self.bot.openai_client or not self.current_response_id:
            await self.channel.send("❌ No robot to upgrade!")
            return
            
        # Bump quality level
        current_idx = self.quality_levels.index(self.current_quality)
        self.current_quality = self.quality_levels[current_idx + 1]
        
        try:
            async with self.channel.typing():
                # Regenerate at higher quality
                response = self.bot.openai_client.responses.create(
                    model="gpt-4o-mini",
                    previous_response_id=self.current_response_id,
                    input="Regenerate this exact same image at higher quality",
                    tools=[{"type": "image_generation", "quality": self.current_quality}],
                )
                
                # Extract image
                for output in response.output:
                    if output.type == "image_generation_call":
                        # Update state
                        self.current_response_id = response.id
                        
                        # Convert to discord file
                        image_bytes = base64.b64decode(output.result)
                        file = discord.File(
                            io.BytesIO(image_bytes), 
                            filename=f"robot_hq_{self.evolution_count}.png"
                        )
                        
                        # Save image
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        self.last_image_path = f"outputs/robot_{timestamp}.png"
                        with open(self.last_image_path, 'wb') as f:
                            f.write(image_bytes)
                        
                        # Send message
                        self.last_message = await self.channel.send(
                            f"✨ **Quality Upgraded!**\n"
                            f"Now at: **{self.current_quality}** quality\n"
                            f"(Evolution #{self.evolution_count})",
                            file=file
                        )
                        
                        # Add meta reactions
                        for reaction in self.bot.meta_reactions:
                            await self.last_message.add_reaction(reaction)
                        
                        logger.info(f"Quality bumped to {self.current_quality}")
                        return
                        
        except Exception as e:
            logger.error(f"Quality bump failed: {e}")
            await self.channel.send(f"❌ Quality upgrade failed: {str(e)}")


class VeistBot(commands.Bot):
    """Main bot class with modular architecture"""
    
    def __init__(self, enabled_modules: Optional[List[str]] = None):
        # Bot configuration
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            description='Veist Image Evolution Bot V2'
        )
        
        # Configuration
        self.guild_id = int(os.getenv('GUILD_ID', 0))
        
        # Load config for meta reactions
        config_path = Path(__file__).parent / "default_config.yaml"
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.meta_reactions = [
            self.config['meta_reactions']['all_done'],
            self.config['meta_reactions']['keep_going'],
            self.config['meta_reactions']['go_back']
        ]
        
        # Initialize OpenAI client
        try:
            self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            logger.info("OpenAI client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.openai_client = None
            
        # Initialize NFT publisher
        try:
            partner_id = os.getenv('AKASWAP_PARTNER_ID', 'aka-gptqgzidcn')
            partner_secret = os.getenv('AKASWAP_PARTNER_SECRET', 'd3b2e436a2dcb4571385aacf779d9858b9ad5a643e8dc10c9255c1a3a2014b12')
            self.nft_publisher = AkaSwapPublisher(partner_id, partner_secret)
            logger.info("NFT publisher initialized")
        except Exception as e:
            logger.error(f"Failed to initialize NFT publisher: {e}")
            self.nft_publisher = None
            
        # Initialize modules
        self.modules: List[VeistModule] = []
        if enabled_modules is None:
            enabled_modules = ['text_evolution']  # Default modules
            
        if 'text_evolution' in enabled_modules:
            self.modules.append(TextEvolutionModule(self))
            logger.info("TextEvolutionModule enabled")
            
        # Add more modules as we create them
        # if 'reaction_testbed' in enabled_modules:
        #     self.modules.append(ReactionTestbedModule(self))
        
    async def setup_hook(self):
        """Called when bot is starting up"""
        logger.info("Bot setup hook called")
        
        # Sync commands if we add any
        if self.guild_id:
            guild = discord.Object(id=self.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands to guild {self.guild_id}")
    
    async def on_ready(self):
        """Called when bot is fully ready"""
        logger.info(f'Bot connected as {self.user} (ID: {self.user.id})')
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Initialize all modules
        for module in self.modules:
            await module.on_ready()
        
    async def on_message(self, message):
        """Handle messages - delegate to modules"""
        # Let modules handle messages
        for module in self.modules:
            await module.on_message(message)
            
        # Process commands if any
        await self.process_commands(message)
        
    async def on_reaction_add(self, reaction, user):
        """Handle reactions - delegate to modules"""
        # Let modules handle reactions
        for module in self.modules:
            await module.on_reaction_add(reaction, user)
    
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
    
    # Parse enabled modules from environment or use defaults
    enabled_modules = os.getenv('VEIST_MODULES', 'text_evolution').split(',')
    
    # Create and run bot
    bot = VeistBot(enabled_modules=enabled_modules)
    
    try:
        logger.info(f"Starting bot with modules: {enabled_modules}")
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