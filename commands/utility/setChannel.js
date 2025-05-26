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
            const generator = await VGenerator.findByPk(interaction.guildId);

            if (!generator) {
                interaction.reply({
                    content: 'The generator has not been initialised in this guild.',
                    flags: MessageFlags.Ephemeral
                });
                return;
            }

            generator.properties.target_channel_id = channel.id;
            generator.changed('properties', true);
            generator.save();

            interaction.reply({
                content: `The target channel has been set to '${channel.name}'.`,
                flags: MessageFlags.Ephemeral
            });
        }
}