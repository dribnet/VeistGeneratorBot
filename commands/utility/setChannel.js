const { SlashCommandBuilder, PermissionFlagsBits, ChannelType } = require('discord.js');
const VChannel = require('../../models/VChannel');
const { where } = require('../../sql-database');

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
            await VChannel.upsert({
                name: "Target_Channel",
                id: channel.id
            });
            await interaction.reply(`The target channel has been set to '${channel.name}'.`);
        }
}