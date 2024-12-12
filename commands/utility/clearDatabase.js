const { SlashCommandBuilder, MessageFlags, PermissionFlagsBits } = require('discord.js');
const VGenerator = require('../../models/VGenerator');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('cleardatabase')
        .setDescription('Clear the database. [DEVELOPMENT ONLY]')
        .setDefaultMemberPermissions(PermissionFlagsBits.Administrator),
    async execute(interaction) {
        await VGenerator.truncate();

        interaction.reply({
            content: 'Database has been cleared.',
            flags: MessageFlags.Ephemeral
        })
    }

}