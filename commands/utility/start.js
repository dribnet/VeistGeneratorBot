const { SlashCommandBuilder, PermissionFlagsBits, ChannelType, MessageFlags } = require('discord.js');
const VGenerator = require('../../models/VGenerator');
const path = require('path');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('start')
        .setDescription('Start running the generator.'),
    async execute(interaction) {
        const generator = await VGenerator.findByPk("default");
        const channelId = generator.channel_id

        const channel = interaction.client.channels.cache.get(channelId)

        if (!channel) {
            interaction.reply({
                content: 'Target channel was not found. Make sure a target channel has been set with \\setChannel.',
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        // Schedule the image posting
        const timerId = setInterval(() => {
            console.log(`Trigger`);
            channel.send({
                files: [path.join(__dirname, '../..', 'test_images', 'test_' + (Math.floor(Math.random() * 36) + 1) + '.png')]
                // content: `Here's your regular image.`
            }).catch(console.error);
        }, generator.gen_interval);

        // Add the timer ID to the default generator
        await VGenerator.update(
            { timer_id: timerId },
            {
                where: { name: "default" }
            }
        );

        interaction.reply(`Starting generation at ${generator.gen_interval / 1000} second intervals.`);
    }
}