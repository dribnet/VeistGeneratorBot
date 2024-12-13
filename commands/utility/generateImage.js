const { SlashCommandBuilder, PermissionFlagsBits, ChannelType, MessageFlags } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('generateimage')
        .setDescription('Generate an image using the generative_recsys API endpoint.')
        .setDefaultMemberPermissions(PermissionFlagsBits.Administrator),
    async execute(interaction) {
        interaction.deferReply();

        const { Client } = await import('@gradio/client'); // Dynamic import
                                
        const response_0 = await fetch("https://raw.githubusercontent.com/gradio-app/gradio/main/test/test_files/bus.png");
        const exampleImage = await response_0.blob();
                                
        const client = await Client.connect("rynmurdock/generative_recsys");
        const result = await client.predict("/choose", { 
                        img: exampleImage, 
        });

        console.log(result.data);

        interaction.editReply({
            content: 'Image generated',
            flags: MessageFlags.Ephemeral
        })
    }
}