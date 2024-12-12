const { SlashCommandBuilder, PermissionFlagsBits, ChannelType, MessageFlags } = require('discord.js');
const VGenerator = require('../../models/VGenerator');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('setchannel')
        .setDescription('Sets the specified channel to be the target of the Veist Generator.')
        .addChannelOption(option => 
            option
                .setName('channel')
                .setDescription('The channel to target')
                .addChannelTypes(ChannelType.GuildText)
                .setRequired(true)
        )
        .setDefaultMemberPermissions(PermissionFlagsBits.ManageChannels),
        async execute(interaction) {
            const channel = interaction.options.getChannel('channel');
            await VGenerator.upsert({
                name: "default",
                channel_id: channel.id
            });
            await interaction.reply({
                content: `The target channel has been set to '${channel.name}'.`,
                flags: MessageFlags.Ephemeral
            });
        }
}