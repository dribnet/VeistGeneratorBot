const { SlashCommandBuilder, MessageFlags } = require('discord.js');
const VGenerator = require('../../models/VGenerator');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('stop')
        .setDescription('Stop the generator.'),
    async execute(interaction) {
        const generator = await VGenerator.findByPk(interaction.guildId);

        if (!generator?.is_active) {
            interaction.reply({
                content: 'Timer has not been started. Use /start to begin generations.',
                flags: MessageFlags.Ephemeral
            });
            return;
        }


        generator.is_active = false;
        
        await generator.save();

        interaction.reply({
            content: 'Timer has been stopped.',
            flags: MessageFlags.Ephemeral
        });
    }
};