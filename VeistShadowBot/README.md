# Veist Shadow Bot

### Process

- The bot remembers the last reaction emoji that eash user added to a Veist Generator Bot post [**This won't be necessary with the reinforcement learning**].
- On subsequent posts, the bot waits a set time to allow the users to add reactions as soon as the post is made. At the end of that time, for each user that hasn't reacted, the Shadow Bot creates a custom emoji representing the user and the the last reaction emoji that they used [**This can be replaced with the prediction output from the reinforcement learning**]. The Shadow Bot then sends a DM to those users to notify them of the reaction, linking to the relevant post (*A command could be added to allow users to silence these notifications, if desired*).
- After the bot has added a custom reaction, one of two things could happen:
    - The user selects the custom reaction, or adds the same reaction that is referenced. This means that the user agrees with the Shadow Bot's reaction [**and can be viewed as positive feedback for the reinforcement learning**].
    - The user adds a different reaction. This means that the user disagrees with the Shadow Bot's reaction [**and can be viewed as a negative feedback for the reinforcement learning**].