# VeistGeneratorBot
The generator and UI bot for the Veist project

# Veist Shadow

### Shadow Bot
The shadow bot represents an individual user in the guild. For the purpose of this first version, it simply repeats the last "reaction" that person made.

	Issues:
	1. Discord does not allow for the dynamic addition of bots. For each new member, a new bot would have to be created in the Developer Portal and then manually added to the server. While this may work for a single server with very few users, it does not scale well. In addition, there is a cap of how many bots a user can create, thereby further limiting the number of bots that could be made.

	Resuloutions:
	1. There can be a single bot/instance per server that can dynamically add a "shadow reaction" for each user. 