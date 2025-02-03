const { SlashCommandBuilder, MessageFlags } = require("discord.js");
const VGenerator = require("../../models/VGenerator");
const VPost = require("../../models/VPost");
const { hf_token } = require('../../config.json');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('start_reaction')
        .setDescription('Start running the generator using the flux API endpoint. Reactions gathered and used an input.'),
    async execute(interaction) {
        const gen = await VGenerator.findByPk('default');

        // Exit immediately if the generator is already running
        if (gen.timer_active) {
            interaction.reply({
                content: 'The generator is already active. Stop it with /stop before starting a new one.',
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        const channelId = gen.channel_id;
        const genInterval = gen.properties.gen_interval;

        const channel = interaction.client.channels.cache.get(channelId);

        if (!channel) {
            interaction.reply({
                content: 'Target channel was not found. Make sure a target channel has been set with /setChannel.',
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        // Set timer_active to be running
        gen.timer_active = true;

        const prop = gen.properties;
        prop.gen_type = 'reaction';
        gen.properties = prop;
        gen.changed('properties', true);
        
        await gen.save();

        interaction.reply({
            content: `Starting generation at ${genInterval / 1000} second intervals.`,
            flags: MessageFlags.Ephemeral
        });

        // Post initial image
        postImage(channel, genInterval);
    }
}

async function postImage(channel, genInterval) {
    let post = null;
    let imgPath = `test_${Math.floor(Math.random() * 36)+1}.png`;
    channel.send({
        files: [`./test_images/${imgPath}`]
    })
    .then(data => {
        post = data;
        VPost.findOrCreate({
            where: {
                message_id: post.id
            },
            defaults: {
                prompt: imgPath
            }
        });

        // post.react('👍');
    })
    .catch(console.error);

    // Start timer
    setTimeout(async () => {
        const vpost = await VPost.findOne({
            order: [['createdAt', 'DESC']]
        })
        try {
            const message = await channel.messages.fetch(vpost.message_id);
    
            const reactions = message.reactions.cache.map(reaction => ({
                emoji: reaction.emoji.name,
                users: reaction.users.cache.map(user => user.id)
            }));

            vpost.reactions.list = reactions;
            vpost.changed('reactions', true);

            vpost.users.list = [...new Set(reactions.flatMap(item => item.users))];
            vpost.changed('users', true);

            await vpost.save();

            message.reply({
                content: `Reactions recieved: ` + data.map(item => `${item.emoji} x${item.users.length}`).join(', ')
            });
            await message.reactions.removeAll();

            // Recursively call postImage(). We do this here to guaruntee that the reactions
            // have been stored in the database before trying to construct the next prompt
            postImage(channel, genInterval);
            
        } catch (error) {
            console.error(error);
        }
    }, genInterval);
}