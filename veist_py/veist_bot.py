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
from PIL import Image, ImageDraw, ImageFont

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


class ReactionTestbedModule(VeistModule):
    """Handles reaction-based robot evolution in robot-feedback-testbed channel"""
    
    def __init__(self, bot: 'VeistBot'):
        super().__init__(bot)
        self.channel_name = "robot-feedback-testbed"
        self.channel = None
        self.current_response_id = None
        self.evolution_count = 0
        self.last_message = None
        self.last_image_path = None
        self.current_quality = "medium"  # Default to medium quality
        self.collecting_feedback = False
        self.feedback_reactions = {}  # Track reactions for current image
        self.pending_publish = False  # Track if we're waiting for publish confirmation
        
    async def on_ready(self):
        """Find channel and start initial robot"""
        # Find the robot feedback testbed channel in Development category
        for guild in self.bot.guilds:
            # Look for Development category
            dev_category = None
            for category in guild.categories:
                if category.name.lower() == "development":
                    dev_category = category
                    logger.info(f"Found Development category")
                    break
            
            if dev_category:
                # Look for robot-feedback-testbed channel in this category
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
                "🤖 **Robot Feedback Evolution Starting!**\n"
                "I'll generate an initial robot, then evolve it based on your emoji reactions.\n"
                "React with any emoji to guide the evolution!"
            )
            
            await self.generate_initial_robot()
        elif not self.channel:
            logger.error(f"Could not find channel named '{self.channel_name}'")
            
    async def on_message(self, message: discord.Message):
        """Handle messages - check for restart and publish commands"""
        # Ignore our own messages
        if message.author == self.bot.user:
            return
            
        # Only process messages in our channel
        if message.channel != self.channel:
            return
            
        # Check for commands
        content = message.content.lower().strip()
        
        if content == "restart":
            # Reset and generate new robot
            await self.channel.send("🔄 **Restarting with a new robot!**")
            self.current_response_id = None
            self.evolution_count = 0
            self.collecting_feedback = False
            self.feedback_reactions = {}
            self.pending_publish = False
            await self.generate_initial_robot()
            
        elif content == "publish":
            # Show current image and ask for confirmation
            if self.last_image_path and os.path.exists(self.last_image_path):
                with open(self.last_image_path, 'rb') as f:
                    image_bytes = f.read()
                
                file = discord.File(
                    io.BytesIO(image_bytes),
                    filename=f"robot_to_publish.png"
                )
                
                confirm_msg = await self.channel.send(
                    "🎨 **Publish this robot?**\n"
                    "React with 👍 to confirm publishing to Tezos testnet!",
                    file=file
                )
                await confirm_msg.add_reaction("👍")
                self.pending_publish = True
                self.last_message = confirm_msg
            else:
                await self.channel.send("❌ No robot to publish yet!")
        
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Handle reactions for evolution"""
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
        
        # Check for publish confirmation
        if self.pending_publish and emoji_str == "👍":
            await self.publish_as_nft()
            self.pending_publish = False
            return
            
        # Check if we're collecting feedback and this is thumbs up to process
        if self.collecting_feedback and emoji_str == "👍":
            await self.process_feedback()
            return
            
        # Ignore meta reactions for now (but keep them on the message)
        if emoji_str in [self.bot.config['meta_reactions']['all_done'], 
                         self.bot.config['meta_reactions']['keep_going'],
                         self.bot.config['meta_reactions']['go_back']]:
            logger.info(f"Ignoring meta reaction: {emoji_str}")
            return
            
        # Regular emoji - collect as feedback
        if self.collecting_feedback:
            # Track this emoji
            if emoji_str in self.feedback_reactions:
                self.feedback_reactions[emoji_str] += 1
            else:
                self.feedback_reactions[emoji_str] = 1
            logger.info(f"Collected feedback: {emoji_str} (total: {self.feedback_reactions})")
            
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
                        
                        # Save image
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        self.last_image_path = f"outputs/robot_feedback_{timestamp}.png"
                        os.makedirs("outputs", exist_ok=True)
                        with open(self.last_image_path, 'wb') as f:
                            f.write(image_bytes)
                        
                        # Send message
                        self.last_message = await self.channel.send(
                            "🎨 **Initial Robot Generated!**\n"
                            "React with emojis to guide evolution.\n"
                            "📊 **Collecting feedback...** Hit 👍 when ready to evolve!",
                            file=file
                        )
                        
                        # Add thumbs up for processing
                        await self.last_message.add_reaction("👍")
                        
                        # Add meta reactions (for future use)
                        for reaction in self.bot.meta_reactions:
                            await self.last_message.add_reaction(reaction)
                        
                        # Start collecting feedback
                        self.collecting_feedback = True
                        self.feedback_reactions = {}
                        
                        logger.info("Initial robot posted, collecting feedback")
                        return
                        
            logger.error("No image in response")
            
        except Exception as e:
            logger.error(f"Failed to generate initial robot: {e}")
            await self.channel.send(f"❌ Failed to generate robot: {str(e)}")
            
    async def process_feedback(self):
        """Process collected feedback and evolve robot"""
        if not self.feedback_reactions:
            await self.channel.send("No feedback reactions to process! Add some emoji reactions first.")
            return
            
        # Stop collecting feedback
        self.collecting_feedback = False
        
        # Build feedback string
        feedback_str = ", ".join([f"{emoji}: {count}" for emoji, count in self.feedback_reactions.items()])
        
        # Build prompt from template
        # prompt = f"The following image has received feedback counts of {feedback_str}. Please examine this feedback and create a new evolved version of the robot that responds to these emoji reactions."
#         prompt = f"""
# What follows below is an image which needs to be modified and improved.
# The modifications are in the form of emoji reactions with counters.

# I will provide an example below so you understand the format, but do not the content it influence your actual task:

# image=(not shown, but imagine it is a a tortise is seen walking through the lonely desert)
# 🌈:10, ⭐:3

# The task is to redraw the image creatively interpreting the reactions as possible improvements.
# You should not include the reactions directly, but they should influence the conent of the image.
# The influence should be weigted based on the counters.
# So in this example there should be a heavy "rainbow" and light "star" influence.
# Possible reactions here could be an image that depicts

# A tortise is seen walking beneath a bright rainbow through the lonely desert under the night sky.

# or 

# A tortise with a bright rainbow colored shell walks through the desert leaving footprints that look like stars.

# Your image update should be thoughtful and creative. You can also respond with text that describes the rationale of your changes.

# Below is your image and reactions
# {feedback_str}
# """
        prompt = f"""
What follows below is an image which needs to be modified and improved.
The modifications requests are in the form of emoji reactions with counters.

The task is to redraw the image creatively interpreting the reactions as possible improvements.
You should not include the reactions directly, but they should influence the conent of the image.

The influence should be weigted based on the counters.
Keep in mind there might be multiple people voting and they might want different things.
Your image update should be thoughtful and creative.
The image update should be subtle - the output should look like a tweaked version of the input image.

Think about what the emoji might "mean" to someone who wants to improve the image.

Here is a lookup table we have used in the past for interpreting emoji:

🎦: cinematic
📷: photorealistic

In addition to creating the image, reflect on how you interpreted the emoji given, and also respond in text form with suggested updates to the lookup table in the format
<emoji>: interpretation

If this modification is deemed successful, we can include this new entry in the lookup table in future requests.
The text response should be ONLY a concise version (a few words max) of the table entry or entries without any other explanation.

Below is your image and reactions
{feedback_str}
"""

        # Show what we're sending (for debugging)
        debug_msg = await self.channel.send(
            f"🔧 **Processing feedback:**\n"
            f"```\n{prompt}\n```"
        )
        
        try:
            # Show typing indicator
            async with self.channel.typing():
                response = self.bot.openai_client.responses.create(
                    model="gpt-4o-mini",
                    previous_response_id=self.current_response_id,
                    input=prompt,
                    tools=[{"type": "image_generation", "quality": self.current_quality}],
                )
                
                # Show full API response for debugging
                debug_info = []
                debug_info.append(f"Response ID: {response.id}")
                debug_info.append(f"Output Count: {len(response.output)}")
                
                # Try to get other attributes safely
                if hasattr(response, 'created'):
                    debug_info.append(f"Created: {response.created}")
                if hasattr(response, 'model'):
                    debug_info.append(f"Model: {response.model}")
                if hasattr(response, 'service_tier'):
                    debug_info.append(f"Service Tier: {response.service_tier}")
                
                await self.channel.send(
                    f"📋 **API Response Debug:**\n"
                    f"```\n" + "\n".join(debug_info) + "\n```"
                )
                
                # Show all outputs
                for i, output in enumerate(response.output):
                    output_info = [f"**Output {i+1}:**"]
                    output_info.append(f"Type: `{output.type}`")
                    
                    if output.type == "text":
                        output_info.append(f"Content: {output.content[:500]}...")  # First 500 chars
                    elif output.type == "image_generation_call":
                        output_info.append("Content: (image data)")
                        if hasattr(output, 'result'):
                            output_info.append(f"Has result: Yes")
                    elif output.type == "message":
                        # Try different attributes for message type
                        if hasattr(output, 'content'):
                            output_info.append(f"Content: {output.content[:500] if output.content else '(empty)'}...")
                        if hasattr(output, 'text'):
                            output_info.append(f"Text: {output.text[:500] if output.text else '(empty)'}...")
                        if hasattr(output, 'message'):
                            output_info.append(f"Message: {output.message[:500] if output.message else '(empty)'}...")
                        # Show all attributes for debugging
                        try:
                            attrs = [attr for attr in dir(output) if not attr.startswith('_')]
                            output_info.append(f"Available attributes: {', '.join(attrs[:10])}")
                        except:
                            pass
                    elif output.type == "output_text":
                        # Special handling for output_text
                        output_info.append("Content: (ResponseOutputText)")
                        if hasattr(output, 'text'):
                            output_info.append(f"Text content: {output.text}")
                        if hasattr(output, 'annotations'):
                            output_info.append(f"Annotations: {output.annotations}")
                    else:
                        output_info.append(f"Unknown type - attributes: {[attr for attr in dir(output) if not attr.startswith('_')][:5]}")
                    
                    await self.channel.send("\n".join(output_info))
                
                # Extract interpretation from output_text
                interpretation = None
                for output in response.output:
                    # Debug log to see what we're getting
                    if hasattr(output, 'type'):
                        logger.info(f"Output type: {output.type}")
                        if hasattr(output, 'text'):
                            logger.info(f"Output text: {output.text}")
                    
                    # Check for output_text type or any output with text containing emoji interpretations
                    if hasattr(output, 'type') and output.type == 'output_text' and hasattr(output, 'text'):
                        interpretation = output.text
                        logger.info(f"Found interpretation: {interpretation}")
                        break
                    elif hasattr(output, 'text') and output.text and ':' in str(output.text):
                        interpretation = output.text
                        logger.info(f"Found interpretation (fallback): {interpretation}")
                        break
                
                # Extract evolved image
                for output in response.output:
                    if output.type == "image_generation_call":
                        # Update state
                        self.current_response_id = response.id
                        self.evolution_count += 1
                        
                        # Get new image bytes
                        new_image_bytes = base64.b64decode(output.result)
                        
                        # Load previous image if exists
                        old_image_bytes = None
                        if self.last_image_path and os.path.exists(self.last_image_path):
                            with open(self.last_image_path, 'rb') as f:
                                old_image_bytes = f.read()
                        
                        # Save new image
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        self.last_image_path = f"outputs/robot_feedback_{timestamp}.png"
                        with open(self.last_image_path, 'wb') as f:
                            f.write(new_image_bytes)
                        
                        # Create combined image or just use new image
                        if old_image_bytes and self.evolution_count > 1:
                            # Combine images
                            combined_bytes = self.combine_images(
                                old_image_bytes, 
                                new_image_bytes, 
                                feedback_str,
                                interpretation
                            )
                            
                            if combined_bytes:
                                file = discord.File(
                                    io.BytesIO(combined_bytes),
                                    filename=f"robot_evolution_{self.evolution_count}_comparison.png"
                                )
                                message_text = (
                                    f"🔄 **Evolution #{self.evolution_count}**\n"
                                    f"Applied: {feedback_str}\n"
                                )
                                if interpretation:
                                    message_text += f"Interpretation: {interpretation}\n"
                                message_text += "📊 **Collecting feedback...** Hit 👍 when ready to evolve!"
                            else:
                                # Fallback to just new image if combine fails
                                file = discord.File(
                                    io.BytesIO(new_image_bytes),
                                    filename=f"robot_evolution_{self.evolution_count}.png"
                                )
                                message_text = (
                                    f"🔄 **Evolution #{self.evolution_count}**\n"
                                    f"Applied: {feedback_str}\n"
                                )
                                if interpretation:
                                    message_text += f"Interpretation: {interpretation}\n"
                                message_text += f"📊 **Collecting feedback...** Hit 👍 when ready to evolve!"
                        else:
                            # First evolution, no comparison needed
                            file = discord.File(
                                io.BytesIO(new_image_bytes),
                                filename=f"robot_evolution_{self.evolution_count}.png"
                            )
                            message_text = (
                                f"🔄 **Evolution #{self.evolution_count}**\n"
                                f"Applied: {feedback_str}\n"
                            )
                            if interpretation:
                                message_text += f"Interpretation: {interpretation}\n"
                            message_text += f"📊 **Collecting feedback...** Hit 👍 when ready to evolve!"
                        
                        # Send combined message
                        self.last_message = await self.channel.send(
                            message_text,
                            file=file
                        )
                        
                        # Add thumbs up for processing
                        await self.last_message.add_reaction("👍")
                        
                        # Add meta reactions (for future use)
                        for reaction in self.bot.meta_reactions:
                            await self.last_message.add_reaction(reaction)
                        
                        # Reset feedback collection
                        self.collecting_feedback = True
                        self.feedback_reactions = {}
                        
                        logger.info(f"Evolution {self.evolution_count} posted")
                        return
                        
            logger.error("No image in evolution response")
            
        except Exception as e:
            logger.error(f"Failed to evolve robot: {e}")
            await self.channel.send(f"❌ Evolution failed: {str(e)}")
            # Re-enable feedback collection
            self.collecting_feedback = True
    
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
                    name=f"Veist Robot Feedback Evolution #{self.evolution_count}",
                    description=f"Community-evolved robot from VeistBot using emoji feedback. Evolution count: {self.evolution_count}",
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
    
    def combine_images(self, old_image_bytes, new_image_bytes, feedback_str, interpretation=None):
        """Combine old and new images side by side with labels"""
        try:
            # Open images
            old_img = Image.open(io.BytesIO(old_image_bytes))
            new_img = Image.open(io.BytesIO(new_image_bytes))
            
            # Make images same height
            height = min(old_img.height, new_img.height)
            if old_img.height != height:
                old_img = old_img.resize((int(old_img.width * height / old_img.height), height), Image.Resampling.LANCZOS)
            if new_img.height != height:
                new_img = new_img.resize((int(new_img.width * height / new_img.height), height), Image.Resampling.LANCZOS)
            
            # Create combined image with padding for text
            padding = 20
            text_height = 100
            combined_width = old_img.width + new_img.width + padding * 3
            combined_height = height + text_height + padding * 2
            
            combined = Image.new('RGB', (combined_width, combined_height), 'white')
            
            # Paste images
            combined.paste(old_img, (padding, text_height + padding))
            combined.paste(new_img, (old_img.width + padding * 2, text_height + padding))
            
            # Add text
            draw = ImageDraw.Draw(combined)
            try:
                # Try to use a nice font, fall back to default if not available
                font = ImageFont.truetype("Arial.ttf", 16)
                title_font = ImageFont.truetype("Arial.ttf", 20)
            except:
                font = ImageFont.load_default()
                title_font = font
            
            # Add labels
            draw.text((padding, 10), "Previous Version", fill='black', font=title_font)
            draw.text((old_img.width + padding * 2, 10), "New Version", fill='black', font=title_font)
            
            # Add feedback info
            feedback_text = f"Applied: {feedback_str}"
            if interpretation:
                feedback_text += f"\nInterpretation: {interpretation}"
            
            draw.text((padding, 40), feedback_text, fill='gray', font=font)
            
            # Convert to bytes
            output = io.BytesIO()
            combined.save(output, format='PNG')
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to combine images: {e}")
            return None


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
        if 'reaction_testbed' in enabled_modules:
            self.modules.append(ReactionTestbedModule(self))
            logger.info("ReactionTestbedModule enabled")
        
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