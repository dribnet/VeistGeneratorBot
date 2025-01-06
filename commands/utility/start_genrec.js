const {
    SlashCommandBuilder,
    MessageFlags,
    ActionRowBuilder,
    ButtonBuilder,
    ButtonStyle
} = require('discord.js');
const VGenerator = require('../../models/VGenerator');
const VPost = require('../../models/VPost');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('start_genrec')
        .setDescription('Start running the generator using the generative_recsys API endpoint.'),
    async execute(interaction) {
        const generator = await VGenerator.findByPk("default");

        // Exit immediately if the generator is already running
        if (generator.timer_active) {
            interaction.reply({
                content: 'The generator is already active. Stop it with /stop before starting a new one.',
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        const channelId = generator.channel_id;
        const genInterval = generator.properties.gen_interval;

        const channel = interaction.client.channels.cache.get(channelId);

        if (!channel) {
            interaction.reply({
                content: 'Target channel was not found. Make sure a target channel has been set with /setChannel.',
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        // Set timer_active to be running
        const gen = await VGenerator.findByPk('default');
        
        gen.timer_active = true;
        
        const prop = gen.properties;
        prop.gen_type = 'genrec';
        gen.properties = prop;
        gen.changed('properties', true);
        
        await gen.save();

        interaction.reply({
            content: `Starting generation at ${genInterval / 1000} second intervals.`,
            flags: MessageFlags.Ephemeral
        });

        // Schedule the image posting
        postImage(channel, genInterval, true); // Post one image immediately, then start timer
        const timerId = setInterval(async () => {
            // Check if timer is still active and clear it if it is not
            const gen = await VGenerator.findByPk("default");
            if (!gen?.timer_active) {
                clearInterval(timerId);
                return;
            }

            postImage(channel, genInterval, false);
        }, genInterval);
    }
}

async function postImage(channel, genInterval, initial) {
    // Generate image
    const { Client } = await import('@gradio/client'); // Dynamic import
    const client = await Client.connect("rynmurdock/generative_recsys");

    let imgData = null;

    if (initial) {
        await client.predict('/start', )
            .then(response => {
                imgData = response.data[response.data.length - 1];
                console.log("Initial Response:", response)
            })
            .catch(err => console.error(err));
        
    } else {
        // We get the votes from the last generated image and get the
        // next image based on that
        const lastEntry = await VPost.findOne({
            order: [['createdAt', 'DESC']]
        });
        console.log("Last Entry:", lastEntry.prediction_response)
        
        if (lastEntry.upvotes >= lastEntry.downvotes) {
            await client.predict('/choose', {
                img: lastEntry.prediction_response.url
            })
            .then(response => {
                imgData = response.data[response.data.length - 1];
                console.log("Response:", response)
            })
            .catch(err => {
                console.error("Error Details:", err)
                if (err.response) {
                    console.error("Response Status:", err.response.status)
                    console.error("Response Data:", err.response.data)
                }
            });
        }
        else {

        }
    }

    // Create buttons
    const upvoteButton = new ButtonBuilder()
        .setCustomId('upvote')
        .setLabel('👍 (0)')
        .setStyle(ButtonStyle.Success);

    const downvoteButton = new ButtonBuilder()
        .setCustomId('downvote')
        .setLabel('👎 (0)')
        .setStyle(ButtonStyle.Danger);

    const buttons = new ActionRowBuilder().addComponents(upvoteButton, downvoteButton);

    var imgPost = null;
    channel.send({
        files: [imgData.url],
        components: [buttons]
    })
    .then(data => {
        imgPost = data;
        VPost.findOrCreate({
            where: {
                message_id: imgPost.id
            },
            defaults: {
                prediction_response: imgData
            }
        });
    })
    .catch(console.error);

    // Create a collector for button interactions
    const filter = (i) => ['upvote', 'downvote'].includes(i.customId);
    const collector = channel.createMessageComponentCollector({
        filter,
        time: genInterval
    });

    collector.on('collect', async (interaction) => {
        if (!interaction.isButton()) return;

        const message = await VPost.findByPk(interaction.message.id);

        if (message.users.list.includes(interaction.user.id)) {
            interaction.reply({
                content: `You have already voted on this image.`,
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        // Increment vote
        if (interaction.customId == 'upvote') {
            message.upvotes++;
        } else if (interaction.customId == 'downvote') {
            message.downvotes++;
        }

        // Add user to list
        message.users.list.push(interaction.user.id);
        message.changed('users', true);

        await message.save();

        // Update button text
        const updatedUpvoteButton = ButtonBuilder
            .from(upvoteButton)
            .setLabel(`👍 (${message.upvotes})`);
        const updatedDownvoteButton = ButtonBuilder
            .from(downvoteButton)
            .setLabel(`👎 (${message.downvotes})`);

        const updatedRow = new ActionRowBuilder().addComponents(
            updatedUpvoteButton,
            updatedDownvoteButton
        );

        await interaction.update({
            components: [updatedRow]
        });
    });

    collector.on('end', async () => {
        const message = await VPost.findOne({
            order: [['createdAt', 'DESC']]
        });

        // Update button text
        const updatedUpvoteButton = ButtonBuilder
            .from(upvoteButton)
            .setLabel(`👍 (${message.upvotes})`)
            .setStyle(ButtonStyle.Secondary)
            .setDisabled(true)
        const updatedDownvoteButton = ButtonBuilder
            .from(downvoteButton)
            .setLabel(`👎 (${message.downvotes})`)
            .setStyle(ButtonStyle.Secondary)
            .setDisabled(true)

        const updatedRow = new ActionRowBuilder().addComponents(
            updatedUpvoteButton,
            updatedDownvoteButton
        );

        await imgPost.edit({
            components: [updatedRow]
        });

        message.upvotes = 0;
        message.downvotes = 0;
        message.users.list.length = 0;
        message.changed('users', true);
        await message.save()
    });
}