const { SlashCommandBuilder, MessageFlags, PermissionFlagsBits } = require('discord.js');
const VGenerator = require('../../models/VGenerator');
const VPost = require('../../models/VPost');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('cleardatabase')
        .setDescription('Clear the database. [DEVELOPMENT ONLY]')
        .setDefaultMemberPermissions(PermissionFlagsBits.Administrator),
    async execute(interaction) {
        await VGenerator.truncate();
        await VPost.truncate();

        interaction.reply({
            content: 'Database has been cleared.',
            flags: MessageFlags.Ephemeral
        })
    }

}