const { SlashCommandBuilder, MessageFlags } = require('discord.js');

// This command would ideally be deployed as a guild command in a private guild.
// This is not neccessary for a prototype build.

module.exports = {
    data: new SlashCommandBuilder()
        .setName('reload')
        .setDescription('Reloads a command.')
        .addStringOption(option =>
            option.setName('command')
                .setDescription('The command to reload.')
                .setRequired(true)),
    async execute(interaction) {
        const commandName = interaction.options.getString('command', true).toLowerCase();
        const command = interaction.client.commands.get(commandName);

        if (!command) {
            return interaction.reply(`There is not command with the name '${commandName}'.`);
        }

        delete require.cache[require.resolve(`./${command.data.name}.js`)];
        
        try {
            const newCommand = require(`./${command.data.name}.js`);
            interaction.client.commands.set(newCommand.data.name, newCommand);
            await interaction.reply({
                content: `Command '${newCommand.data.name} was reloaded.`,
                flags: MessageFlags.Ephemeral
            })
        } catch (error) {
            console.error(error);
            await interaction.reply({content: `There was an error while reloading command '${newCommand.data.name}.`, flags: MessageFlags.Ephemeral})
        }
    }
}