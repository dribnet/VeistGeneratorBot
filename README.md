# VeistGeneratorBot
The generator and UI bot for the Veist project

Goal:
- Using a homemade generator.

Prototype:
- Use any process that accepts an input and generates an image.
	- First step is to get a generator operational using JS. This should be hosted on my machine and will eventually run alongside the bot.
	- Next, it should be integrated into the Discord API to generate images and post them at regular intervals (every couple of minutes).
	- Then, use commands to allow the user to append inputs to the prompt, and use parsed arguments (eg. time::15m) to add context.
		- Eg. /prompt green things time::15m
		- The "time" argument, for example, will allow users to add a line to the prompt that will last for a period of time, being removed from the prompt at the end of the timer. If an appended input does not have this argument, it will only be removed if the entire prompt changes.
