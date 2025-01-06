const { SlashCommandBuilder, MessageFlags } = require('discord.js');
const VGenerator = require('../../models/VGenerator');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('stop')
        .setDescription('Stop the generator.'),
    async execute(interaction) {
        const generator = await VGenerator.findByPk("default");

        if (!generator?.timer_active) {
            interaction.reply({
                content: 'Timer has not been started. Use /start to begin generations.',
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        const gen = await VGenerator.findByPk('default');

        gen.timer_active = false;
        
        const prop = gen.properties;
        prop.gen_type = 'none';
        gen.properties = prop;
        gen.changed('properties', true);
        
        await gen.save();

        interaction.reply({
            content: 'Timer has been stopped.',
            flags: MessageFlags.Ephemeral
        });
    }
};