const { SlashCommandBuilder, MessageFlags } = require("discord.js");
const VGenerator = require("../../models/VGenerator");

module.exports = {
    data: new SlashCommandBuilder()
        .setName('init')
        .setDescription('Initialise the database for this guild.'),
    async execute(interaction) {
        const [generator, created] = await VGenerator.findOrCreate(
            { where: { guild_id: interaction.guildId } }
        );

        if (created) {
            interaction.reply({
                content: '⚙️ Guild has been initialised in the database.',
                flags: MessageFlags.Ephemeral
            });
        }
        else {
            interaction.reply({
                content: '⚙️ Guild already initialised in the database.',
                flags: MessageFlags.Ephemeral
            });
        }

    }
}