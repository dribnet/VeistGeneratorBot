const { SlashCommandBuilder, PermissionFlagsBits, ChannelType } = require('discord.js');

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
            await interaction.reply(`${channel.name} set as default channel.`);
        }
}