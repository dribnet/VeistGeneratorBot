const { SlashCommandBuilder, MessageFlags, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');
const VGenerator = require('../../models/VGenerator');
const path = require('path');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('start')
        .setDescription('Start running the generator.'),
    async execute(interaction) {
        const generator = await VGenerator.findByPk("default");
        const channelId = generator.channel_id;
        const genInterval = generator.gen_interval;

        const channel = interaction.client.channels.cache.get(channelId);

        if (!channel) {
            interaction.reply({
                content: 'Target channel was not found. Make sure a target channel has been set with /setChannel.',
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        // Set timer_active to be running
        await VGenerator.update(
            { timer_active: true },
            {
                where: { name: "default" }
            }
        );
        
        interaction.reply({
            content: `Starting generation at ${genInterval / 1000} second intervals.`,
            flags: MessageFlags.Ephemeral
        });

        // Schedule the image posting
        postImage(channel, genInterval); // Post one image immediately, then start timer
        const timerId = setInterval(async () => { 
            // Check if timer is still active and clear it if it is not
            const gen = await VGenerator.findByPk("default");
            if (!gen?.timer_active) {
                clearInterval(timerId);
                return;
            }

            postImage(channel, genInterval);
        }, genInterval);
    }
}

function postImage(channel, genInterval) {
    // Create buttons
    const upvoteButton = new ButtonBuilder()
        .setCustomId('upvote')
        .setLabel('👍 (0)')
        .setStyle(ButtonStyle.Success);

    const downvoteButton = new ButtonBuilder()
        .setCustomId('downvote')
        .setLabel('👎 (0)')
        .setStyle(ButtonStyle.Danger);

    const row = new ActionRowBuilder().addComponents(upvoteButton, downvoteButton);

    var imgPost = null;
    channel.send({
        files: [path.join(__dirname, '../..', 'test_images', 'test_' + (Math.floor(Math.random() * 36) + 1) + '.png')],
        components: [row]
    })
    .then(data => imgPost = data)
    .catch(console.error);
    
    // Create a collector for button interactions
    const filter = (i) => ['upvote', 'downvote'].includes(i.customId);
    const collector = channel.createMessageComponentCollector({ filter, time: genInterval });

    collector.on('collect', async (interaction) => {
        if (!interaction.isButton()) return;

        const gen = await VGenerator.findByPk("default");

        if (gen.users.list.includes(interaction.user.id)) {
            interaction.reply({
                content: `You have already voted on this image.`,
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        // Increment vote
        if (interaction.customId == 'upvote') {
            gen.current_upvotes++;
        }
        else if (interaction.customId == 'downvote') {
            gen.current_downvotes++;
        }

        // Add user to list
        gen.users.list.push(interaction.user.id);
        gen.changed('users', true);

        await gen.save();

        // Update button text
        const updatedUpvoteButton = ButtonBuilder
            .from(upvoteButton)
            .setLabel(`👍 (${gen.current_upvotes})`);
        const updatedDownvoteButton = ButtonBuilder
            .from(downvoteButton)
            .setLabel(`👎 (${gen.current_downvotes})`);

        const updatedRow = new ActionRowBuilder().addComponents(
            updatedUpvoteButton, 
            updatedDownvoteButton
        );

        await interaction.update({
            components: [updatedRow]
        });
    });

    collector.on('end', async () => {
        const gen = await VGenerator.findByPk("default");

        await imgPost.edit({
            components: []
        });
        await imgPost.reply({
            content: `Image received: 👍 ${gen.current_upvotes} | 👎 ${gen.current_downvotes}`,
        });

        gen.current_upvotes = 0;
        gen.current_downvotes = 0;
        gen.users.list.length = 0;
        gen.changed('users', true);
        await gen.save()
    });
}