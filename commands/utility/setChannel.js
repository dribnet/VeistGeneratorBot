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
            const [vchan, created] = await VChannel.findOrCreate({
                where: { id: channel.id },
                defaults: { name: channel.name }
            });
            if (created) {
                await interaction.reply(`'${channel.name}' has been set as the target channel.`);
            }
            else {
                await interaction.reply(`'${channel.name}' has already been set as the target channel.`);
            }
        }
}