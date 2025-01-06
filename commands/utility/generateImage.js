const { SlashCommandBuilder, PermissionFlagsBits, ChannelType, MessageFlags } = require('discord.js');
const VGenerator = require('../../models/VGenerator');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('generateimage')
        .setDescription('Generate an image using the generative_recsys API endpoint.')
        .setDefaultMemberPermissions(PermissionFlagsBits.Administrator),
    async execute(interaction) {
        
        const gen = await VGenerator.findByPk('default');
        
        interaction.reply({
            content: "Generator Type: " + gen.properties.gen_type,
            flags: MessageFlags.Ephemeral
        })
    }
}